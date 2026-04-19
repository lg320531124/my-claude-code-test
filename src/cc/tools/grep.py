"""GrepTool - Content search using ripgrep.

Ported from TypeScript GrepTool.ts patterns:
- Input schema with pattern, path, glob, output_mode, -B/-A/-C context, head_limit
- Output schema with mode, numFiles, filenames, content, numMatches
- Path validation
- Permission checking
- VCS directory exclusion
- Default head_limit of 250
- Context lines support
- Case insensitive option
- Type filter support
"""

from __future__ import annotations
import os
import subprocess
import time
from pathlib import Path
from typing import ClassVar, Dict, Any, Optional, List, Callable, Set

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext, ValidationResult
from ..types.permission import PermissionResult, PermissionDecision
from ..types.message import ToolResultBlock


# VCS directories to exclude
VCS_DIRECTORIES: Set[str] = {".git", ".svn", ".hg", ".bzr", ".jj", ".sl"}

# Default head limit
DEFAULT_HEAD_LIMIT = 250


class GrepInput(ToolInput):
    """Input for GrepTool."""

    pattern: str = Field(description="The regular expression pattern to search for")
    path: Optional[str] = Field(
        default=None,
        description="File or directory to search in. Defaults to cwd."
    )
    glob: Optional[str] = Field(
        default=None,
        description="Glob pattern to filter files (e.g., '*.js', '*.ts')"
    )
    output_mode: str = Field(
        default="files_with_matches",
        description="Output mode: content, files_with_matches, count"
    )
    head_limit: Optional[int] = Field(
        default=None,
        description="Limit output to first N lines/entries. Default 250. Pass 0 for unlimited."
    )
    offset: Optional[int] = Field(
        default=None,
        description="Skip first N entries before applying head_limit"
    )
    context_before: Optional[int] = Field(
        default=None,
        alias="-B",
        description="Number of lines before match"
    )
    context_after: Optional[int] = Field(
        default=None,
        alias="-A",
        description="Number of lines after match"
    )
    context: Optional[int] = Field(
        default=None,
        description="Number of lines before and after match"
    )
    case_insensitive: bool = Field(
        default=False,
        alias="-i",
        description="Case insensitive search"
    )
    line_numbers: bool = Field(
        default=True,
        alias="-n",
        description="Show line numbers"
    )
    multiline: bool = Field(
        default=False,
        description="Enable multiline mode"
    )
    type: Optional[str] = Field(
        default=None,
        description="File type to search (js, py, rust, go, java)"
    )


class GrepOutput(BaseModel):
    """Output schema for GrepTool."""

    mode: str = Field(description="Output mode used")
    num_files: int = Field(description="Number of files with matches")
    filenames: List[str] = Field(description="Files with matches")
    content: Optional[str] = Field(default=None, description="Matching content")
    num_lines: Optional[int] = Field(default=None, description="Lines of content")
    num_matches: Optional[int] = Field(default=None, description="Match count")
    applied_limit: Optional[int] = Field(default=None, description="Limit applied")
    applied_offset: Optional[int] = Field(default=None, description="Offset applied")


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


def apply_head_limit(
    items: List[Any],
    limit: Optional[int],
    offset: int = 0,
) -> tuple[List[Any], Optional[int]]:
    """Apply head_limit and offset to items."""
    if limit == 0:
        return items[offset:], None

    effective_limit = limit or DEFAULT_HEAD_LIMIT
    sliced = items[offset:offset + effective_limit]
    was_truncated = len(items) - offset > effective_limit
    return sliced, effective_limit if was_truncated else None


def get_grep_prompt() -> str:
    """Generate Grep tool prompt."""
    return """- Fast content search tool that works with any codebase size
- Supports regular expression patterns
- Uses ripgrep (rg) for speed
- Use this tool when you need to search file contents, NOT file names

Usage notes:
- Use Grep for content search, NOT Bash commands like grep or rg
- Supports glob patterns (--glob) to filter files
- Use --type for common file types (js, py, rust, etc.)
- Defaults to showing files_with_matches mode
- Use output_mode: 'content' to see matching lines
- Supports -B/-A/-C for context lines
- Use -i for case insensitive search
- Use head_limit to limit results (default 250)
- Use offset with head_limit for pagination


Output modes:
- content: Shows matching lines with line numbers
- files_with_matches: Shows file paths with matches (default)
- count: Shows match counts per file"""


class GrepTool(Tool):
    """Grep tool implementation matching TypeScript GrepTool.ts."""

    name: str = "Grep"
    input_schema: type = GrepInput
    max_result_size_chars: float = 20_000
    strict: bool = True
    aliases: Optional[List[str]] = None
    search_hint: str = "search file contents with regex (ripgrep)"

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Execute grep search."""
        input_data = GrepInput.model_validate(args)

        # Build ripgrep command
        cmd = ["rg", "--no-heading", "--color=never"]

        # VCS exclusions
        for vcs_dir in VCS_DIRECTORIES:
            cmd.extend(["--glob", f"!{vcs_dir}/**"])

        # Output mode
        mode = input_data.output_mode
        if mode == "files_with_matches":
            cmd.append("--files-with-matches")
        elif mode == "count":
            cmd.append("--count")

        # Content mode options
        if mode == "content":
            if input_data.line_numbers:
                cmd.append("--line-number")
            # Context lines
            context = input_data.context
            if context:
                cmd.extend(["-C", str(context)])
            elif input_data.context_before:
                cmd.extend(["-B", str(input_data.context_before)])
            elif input_data.context_after:
                cmd.extend(["-A", str(input_data.context_after)])

        # Case insensitive
        if input_data.case_insensitive:
            cmd.append("-i")

        # Multiline
        if input_data.multiline:
            cmd.extend(["-U", "--multiline-dotall"])

        # Glob filter
        if input_data.glob:
            cmd.extend(["--glob", input_data.glob])

        # Type filter
        if input_data.type:
            cmd.extend(["--type", input_data.type])

        # Pattern
        cmd.append(input_data.pattern)

        # Path
        search_path = expand_path(input_data.path) if input_data.path else context.cwd
        cmd.append(search_path)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=context.cwd,
            )

            # Handle no matches (rg returns exit code 1 when no matches)
            if proc.returncode != 0 and not proc.stdout:
                return ToolResult(
                    data=GrepOutput(
                        mode=mode,
                        num_files=0,
                        filenames=[],
                    ),
                )

            # Process output
            output_text = proc.stdout.strip()
            if not output_text:
                return ToolResult(
                    data=GrepOutput(
                        mode=mode,
                        num_files=0,
                        filenames=[],
                    ),
                )

            # Split and apply limits
            lines = output_text.split("\n")
            offset = input_data.offset or 0
            limited_lines, applied_limit = apply_head_limit(lines, input_data.head_limit, offset)

            # Parse results based on mode
            if mode == "files_with_matches":
                filenames = [to_relative_path(line.strip(), context.cwd) for line in limited_lines if line.strip()]
                return ToolResult(
                    data=GrepOutput(
                        mode=mode,
                        num_files=len(filenames),
                        filenames=filenames,
                        applied_limit=applied_limit,
                        applied_offset=offset if offset > 0 else None,
                    ),
                )

            elif mode == "count":
                # Parse count output
                filenames = []
                num_matches = 0
                for line in limited_lines:
                    if line.strip():
                        parts = line.split(":")
                        if len(parts) >= 2:
                            filenames.append(to_relative_path(parts[0].strip(), context.cwd))
                            try:
                                num_matches += int(parts[-1].strip())
                            except ValueError:
                                pass

                return ToolResult(
                    data=GrepOutput(
                        mode=mode,
                        num_files=len(filenames),
                        filenames=filenames,
                        num_matches=num_matches,
                        applied_limit=applied_limit,
                        applied_offset=offset if offset > 0 else None,
                    ),
                )

            else:  # content mode
                return ToolResult(
                    data=GrepOutput(
                        mode=mode,
                        num_files=0,
                        filenames=[],
                        content="\n".join(limited_lines),
                        num_lines=len(limited_lines),
                        applied_limit=applied_limit,
                        applied_offset=offset if offset > 0 else None,
                    ),
                )

        except FileNotFoundError:
            return ToolResult(
                data=GrepOutput(
                    mode=input_data.output_mode,
                    num_files=0,
                    filenames=[],
                ),
                is_error=True,
                error_message="ripgrep (rg) not installed. Install with: brew install ripgrep",
            )
        except Exception as e:
            return ToolResult(
                data=GrepOutput(
                    mode=input_data.output_mode,
                    num_files=0,
                    filenames=[],
                ),
                is_error=True,
                error_message=f"Error in grep search: {e}",
            )

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description."""
        pattern = input.get("pattern", "")
        if pattern:
            return f"Search for '{pattern}'"
        return "Search content"

    async def prompt(
        self,
        options: Dict[str, Any],
    ) -> str:
        """Generate tool prompt."""
        return get_grep_prompt()

    def is_concurrency_safe(self, input: Dict[str, Any]) -> bool:
        """Check if tool is safe for concurrent execution."""
        return True

    def is_read_only(self, input: Dict[str, Any]) -> bool:
        """Check if tool is read-only."""
        return True

    def to_auto_classifier_input(self, input: Dict[str, Any]) -> str:
        """Convert input for auto-mode classifier."""
        pattern = input.get("pattern", "")
        path = input.get("path", "")
        return f"{pattern} in {path}" if path else pattern

    def is_search_or_read_command(self, input: Dict[str, Any]) -> Dict[str, bool]:
        """Check if this is a search/read operation."""
        return {"is_search": True, "is_read": False, "is_list": False}

    def get_path(self, input: Dict[str, Any]) -> Optional[str]:
        """Get search path from input."""
        return input.get("path") or ""

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary for compact view."""
        if not input or not input.get("pattern"):
            return None
        return f"Search '{input['pattern']}'"

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description for spinner."""
        if not input or not input.get("pattern"):
            return "Searching"
        return f"Searching for '{input['pattern']}'"

    def user_facing_name(self, input: Optional[Dict[str, Any]]) -> str:
        """Get user-facing name."""
        return "Grep"

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
                    message=f"Path does not exist: {input['path']}",
                    error_code=1,
                )

        # Validate pattern is not empty
        if not input.get("pattern"):
            return ValidationResult(
                result=False,
                message="Pattern is required",
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
        if isinstance(data, GrepOutput):
            if data.num_files == 0 and not data.content:
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content="No matches found",
                )

            if data.mode == "content":
                content = data.content or ""
                if data.applied_limit:
                    content += f"\n(limit: {data.applied_limit})"
                if data.applied_offset:
                    content += f"\n(offset: {data.applied_offset})"
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content=content,
                )

            if data.num_files == 0:
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content="No matches found",
                )

            content = "\n".join(data.filenames)
            if data.applied_limit:
                content += f"\n(limit: {data.applied_limit})"
            return ToolResultBlock(
                tool_use_id=tool_use_id,
                content=content,
            )

        return ToolResultBlock(
            tool_use_id=tool_use_id,
            content=str(data),
        )


def build_grep_tool() -> GrepTool:
    """Build GrepTool instance."""
    return GrepTool()


__all__ = [
    "GrepTool",
    "GrepInput",
    "GrepOutput",
    "build_grep_tool",
    "get_grep_prompt",
    "DEFAULT_HEAD_LIMIT",
    "VCS_DIRECTORIES",
]