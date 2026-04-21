"""GlobTool - File pattern matching.

Ported from TypeScript GlobTool.ts patterns:
- Input schema with pattern, path
- Output schema with durationMs, numFiles, filenames, truncated
- Path validation
- Permission checking
- Truncation handling (limit 100 files)
- Relative path output
"""

from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext, ValidationResult
from ..types.permission import PermissionResult, PermissionDecision
from ..types.message import ToolResultBlock


DEFAULT_GLOB_LIMIT = 100


class GlobInput(ToolInput):
    """Input for GlobTool."""

    pattern: str = Field(description="The glob pattern to match files against")
    path: Optional[str] = Field(
        default=None,
        description="The directory to search in. Defaults to current working directory."
    )


class GlobOutput(BaseModel):
    """Output schema for GlobTool."""

    duration_ms: int = Field(description="Time taken to execute search in milliseconds")
    num_files: int = Field(description="Total number of files found")
    filenames: List[str] = Field(description="Array of file paths that match the pattern")
    truncated: bool = Field(description="Whether results were truncated (limited)")


def expand_path(file_path: str) -> str:
    """Expand path."""
    if file_path.startswith("~"):
        file_path = os.path.expanduser(file_path)
    return os.path.abspath(file_path)


def to_relative_path(file_path: str, cwd: str) -> str:
    """Convert to relative path if under cwd."""
    try:
        return str(Path(file_path).relative_to(cwd))
    except ValueError:
        return file_path


def get_glob_prompt() -> str:
    """Generate Glob tool prompt."""
    return """- Fast file pattern matching tool that works with any codebase size
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this tool when you need to find files by name patterns, not content

Usage notes:
- Use Glob for finding files, NOT Bash commands like find or ls
- ALWAYS use this tool for file searches
- Returns up to 100 files by default (may be truncated)
- Use more specific patterns if you get too many results"""


class GlobTool(Tool):
    """Glob tool implementation matching TypeScript GlobTool.ts."""

    name: str = "Glob"
    input_schema: type = GlobInput
    max_result_size_chars: float = 100_000
    strict: bool = True
    aliases: Optional[List[str]] = None
    search_hint: str = "find files by name pattern or wildcard"

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Execute glob search."""
        input_data = GlobInput.model_validate(args)

        start_time = time.time()
        limit = context.glob_limits.get("maxResults", DEFAULT_GLOB_LIMIT) if context.glob_limits else DEFAULT_GLOB_LIMIT

        # Determine search path
        search_path = expand_path(input_data.path) if input_data.path else context.cwd
        base_path = Path(search_path)

        if not base_path.exists():
            return ToolResult(
                data=GlobOutput(
                    duration_ms=int((time.time() - start_time) * 1000),
                    num_files=0,
                    filenames=[],
                    truncated=False,
                ),
                is_error=True,
                error_message=f"Directory does not exist: {search_path}",
            )

        if not base_path.is_dir():
            return ToolResult(
                data=GlobOutput(
                    duration_ms=int((time.time() - start_time) * 1000),
                    num_files=0,
                    filenames=[],
                    truncated=False,
                ),
                is_error=True,
                error_message=f"Path is not a directory: {search_path}",
            )

        # Find matching files
        try:
            matches = list(base_path.glob(input_data.pattern))
            # Sort by modification time (most recent first)
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Apply limit
            truncated = len(matches) > limit
            matches = matches[:limit]

            # Convert to relative paths
            filenames = [to_relative_path(str(m), context.cwd) for m in matches]

            duration_ms = int((time.time() - start_time) * 1000)

            return ToolResult(
                data=GlobOutput(
                    duration_ms=duration_ms,
                    num_files=len(filenames),
                    filenames=filenames,
                    truncated=truncated,
                ),
            )

        except Exception as e:
            return ToolResult(
                data=GlobOutput(
                    duration_ms=int((time.time() - start_time) * 1000),
                    num_files=0,
                    filenames=[],
                    truncated=False,
                ),
                is_error=True,
                error_message=f"Error in glob search: {e}",
            )

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description."""
        pattern = input.get("pattern", "")
        if pattern:
            return f"Find files matching {pattern}"
        return "Find files"

    async def prompt(
        self,
        options: Dict[str, Any],
    ) -> str:
        """Generate tool prompt."""
        return get_glob_prompt()

    def is_concurrency_safe(self, input: Dict[str, Any]) -> bool:
        """Check if tool is safe for concurrent execution."""
        return True

    def is_read_only(self, input: Dict[str, Any]) -> bool:
        """Check if tool is read-only."""
        return True

    def to_auto_classifier_input(self, input: Dict[str, Any]) -> str:
        """Convert input for auto-mode classifier."""
        return input.get("pattern", "")

    def is_search_or_read_command(self, input: Dict[str, Any]) -> Dict[str, bool]:
        """Check if this is a search/read operation."""
        return {"is_search": True, "is_read": False, "is_list": False}

    def get_path(self, input: Dict[str, Any]) -> Optional[str]:
        """Get search path from input."""
        return expand_path(input.get("path", "")) if input.get("path") else None

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary for compact view."""
        if not input or not input.get("pattern"):
            return None
        return f"Find {input['pattern']}"

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description for spinner."""
        if not input or not input.get("pattern"):
            return "Finding files"
        return f"Finding {input['pattern']}"

    def user_facing_name(self, input: Optional[Dict[str, Any]]) -> str:
        """Get user-facing name."""
        return "Glob"

    def validate_input(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate tool input."""
        if input.get("path"):
            full_path = expand_path(input["path"])
            path = Path(full_path)

            if not path.exists():
                return ValidationResult(
                    result=False,
                    message=f"Directory does not exist: {input['path']}",
                    error_code=1,
                )

            if not path.is_dir():
                return ValidationResult(
                    result=False,
                    message=f"Path is not a directory: {input['path']}",
                    error_code=2,
                )

        return ValidationResult(result=True)

    async def check_permissions(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> PermissionResult:
        """Check tool permissions."""
        return PermissionResult(
            decision=PermissionDecision.ALLOW,
            updated_input=input,
        )

    def map_tool_result_to_tool_result_block_param(
        self,
        data: Any,
        tool_use_id: str,
    ) -> ToolResultBlock:
        """Map result to API block."""
        if isinstance(data, GlobOutput):
            if data.num_files == 0:
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content="No files found",
                )

            content = "\n".join(data.filenames)
            if data.truncated:
                content += "\n(Results are truncated. Consider using a more specific path or pattern.)"

            return ToolResultBlock(
                tool_use_id=tool_use_id,
                content=content,
            )

        return ToolResultBlock(
            tool_use_id=tool_use_id,
            content=str(data),
        )


def build_glob_tool() -> GlobTool:
    """Build GlobTool instance."""
    return GlobTool()


# Add execute method to GlobTool
def _add_execute_method():
    async def execute(self, input: GlobInput, ctx: ToolUseContext) -> ToolResult:
        """Execute method for simpler interface."""
        args = input.model_dump() if hasattr(input, 'model_dump') else dict(input)
        return await self.call(args, ctx, lambda *args: True, None)
    GlobTool.execute = execute

_add_execute_method()


__all__ = [
    "GlobTool",
    "GlobInput",
    "GlobOutput",
    "build_glob_tool",
    "get_glob_prompt",
    "DEFAULT_GLOB_LIMIT",
]