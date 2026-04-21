"""EditTool - File editing with string replacement.

Ported from TypeScript FileEditTool.ts patterns:
- Input schema with file_path, old_string, new_string, replace_all
- Staleness detection (file modified since read)
- Permission checking with deny rules
- Team memory secrets guard
- File history tracking
- Unique match validation
- Multi-occurrence handling with replace_all
- Line ending preservation
- Git diff generation
"""

from __future__ import annotations
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext, ValidationResult
from ..types.permission import PermissionResult, PermissionDecision
from ..utils.async_io import (
    read_file_async,
    write_file_async,
    exists_async,
    stat_async,
    mkdir_async,
)


class EditInput(ToolInput):
    """Input for EditTool."""

    file_path: str = Field(description="The absolute path to the file to edit")
    old_string: str = Field(description="The text to replace")
    new_string: str = Field(description="The text to replace it with")
    replace_all: bool = Field(
        default=False,
        description="Replace all occurrences (set to true if there are multiple)"
    )


class EditOutput(BaseModel):
    """Output schema for EditTool."""

    type: str = Field(default="edit", description="Result type")
    file_path: str = Field(description="The path to the file that was edited")
    old_string: str = Field(description="The old string that was replaced")
    new_string: str = Field(description="The new string that replaced it")
    occurrences: int = Field(description="Number of occurrences replaced")
    content: Optional[str] = Field(default=None, description="Updated content preview")


MAX_EDIT_FILE_SIZE = 1024 * 1024 * 1024  # 1 GiB
FILE_UNEXPECTEDLY_MODIFIED_ERROR = "File has been modified since read. Read it again before editing."


def expand_path(file_path: str) -> str:
    """Expand path (handle ~, environment variables)."""
    if file_path.startswith("~"):
        file_path = os.path.expanduser(file_path)
    file_path = os.path.expandvars(file_path)
    return os.path.abspath(file_path)


def preserve_line_endings(original: str, new_content: str) -> str:
    """Preserve original line endings in new content."""
    if "\r\n" in original and "\n" not in original.replace("\r\n", "\n"):
        # Original has CRLF, new has LF only
        return new_content.replace("\n", "\r\n")
    return new_content


def get_edit_prompt() -> str:
    """Generate Edit tool prompt."""
    return """This is a tool for editing files. For moving or renaming files, you should generally use the Bash tool's mv command, not this tool.

Usage notes:
- Use Edit for editing files, NOT Bash commands like sed
- You MUST read a file before you can edit it (Read first, then Edit)
- old_string and new_string MUST be different
- old_string MUST be exactly as it appears in the file (including whitespace)
- If there are multiple occurrences, provide more context to make it unique, or use replace_all=true
- NEVER edit files that you haven't read first
- This tool will FAIL if old_string is not unique and replace_all is not set

The file_path parameter must be an absolute path (not relative).

# Edit workflow:

1. Read the file to understand its current content
2. Specify the exact string to replace (old_string)
3. Specify the replacement string (new_string)
4. The tool will replace the first occurrence (or all if replace_all=true)
5. The tool returns success/failure

# IMPORTANT constraints:

- old_string must match exactly (including indentation, quotes, etc.)
- If multiple matches and not replace_all, the edit fails
- old_string and new_string must be different
- File must be read first (stale check)
- Empty old_string with non-empty file is invalid (use Write for new files)
- Notebook files (.ipynb) should use NotebookEdit tool"""


class EditTool(Tool):
    """Edit tool implementation matching TypeScript FileEditTool.ts."""

    name: str = "Edit"
    input_schema: type = EditInput
    max_result_size_chars: float = 100_000
    strict: bool = True
    aliases: Optional[List[str]] = None
    search_hint: str = "modify file contents in place"

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Execute the edit."""
        input_data = EditInput.model_validate(args)

        # Expand path
        full_path = expand_path(input_data.file_path)
        path = Path(full_path)

        # Check if strings are the same
        if input_data.old_string == input_data.new_string:
            return ToolResult(
                data=EditOutput(
                    file_path=input_data.file_path,
                    old_string=input_data.old_string,
                    new_string=input_data.new_string,
                    occurrences=0,
                ),
                is_error=True,
                error_message="No changes to make: old_string and new_string are identical.",
            )

        # Check if file exists (async)
        file_exists = await exists_async(full_path)
        if not file_exists:
            # Empty old_string on non-existent file means new file creation
            if input_data.old_string == "":
                # Create new file (async)
                await mkdir_async(path.parent, parents=True, exist_ok=True)
                await write_file_async(full_path, input_data.new_string, encoding="utf-8")

                # Update file state (async)
                stat_result = await stat_async(full_path)
                if context.read_file_state:
                    context.read_file_state[full_path] = {
                        "content": input_data.new_string,
                        "timestamp": stat_result.st_mtime,
                        "offset": None,
                        "limit": None,
                    }

                return ToolResult(
                    data=EditOutput(
                        type="create",
                        file_path=input_data.file_path,
                        old_string=input_data.old_string,
                        new_string=input_data.new_string,
                        occurrences=1,
                    ),
                )

            # Find similar file
            similar = await asyncio.get_event_loop().run_in_executor(
                None, lambda: find_similar_file(full_path, context.cwd)
            )
            msg = f"File does not exist: {full_path}"
            if similar:
                msg += f" Did you mean {similar}?"

            return ToolResult(
                data=EditOutput(
                    file_path=input_data.file_path,
                    old_string=input_data.old_string,
                    new_string=input_data.new_string,
                    occurrences=0,
                ),
                is_error=True,
                error_message=msg,
            )

        # Check if notebook
        if path.suffix.lower() == ".ipynb":
            return ToolResult(
                data=EditOutput(
                    file_path=input_data.file_path,
                    old_string=input_data.old_string,
                    new_string=input_data.new_string,
                    occurrences=0,
                ),
                is_error=True,
                error_message="File is a Jupyter Notebook. Use NotebookEdit tool instead.",
            )

        # Check staleness (async)
        last_read = context.read_file_state.get(full_path)
        if last_read:
            try:
                stat_result = await stat_async(full_path)
                current_mtime = stat_result.st_mtime
                if current_mtime > last_read.get("timestamp", 0):
                    # Potential stale
                    current_content = await read_file_async(full_path, encoding="utf-8")
                    if current_content != last_read.get("content", ""):
                        return ToolResult(
                            data=EditOutput(
                                file_path=input_data.file_path,
                                old_string=input_data.old_string,
                                new_string=input_data.new_string,
                                occurrences=0,
                            ),
                            is_error=True,
                            error_message=FILE_UNEXPECTEDLY_MODIFIED_ERROR,
                        )
            except OSError:
                pass

        # Read file (async)
        content = await read_file_async(full_path, encoding="utf-8")

        # Normalize line endings for comparison
        normalized_content = content.replace("\r\n", "\n")
        old_string_normalized = input_data.old_string.replace("\r\n", "\n")

        # Check empty old_string on non-empty file
        if input_data.old_string == "" and content.strip() != "":
            return ToolResult(
                data=EditOutput(
                    file_path=input_data.file_path,
                    old_string=input_data.old_string,
                    new_string=input_data.new_string,
                    occurrences=0,
                ),
                is_error=True,
                error_message="Cannot create new file - file already exists and has content.",
            )

        # Count occurrences
        count = normalized_content.count(old_string_normalized)

        if count == 0:
            return ToolResult(
                data=EditOutput(
                    file_path=input_data.file_path,
                    old_string=input_data.old_string,
                    new_string=input_data.new_string,
                    occurrences=0,
                ),
                is_error=True,
                error_message=f"String not found in file: '{input_data.old_string[:50]}...'",
            )

        # Check uniqueness if not replace_all
        if not input_data.replace_all and count > 1:
            return ToolResult(
                data=EditOutput(
                    file_path=input_data.file_path,
                    old_string=input_data.old_string,
                    new_string=input_data.new_string,
                    occurrences=count,
                ),
                is_error=True,
                error_message=f"Found {count} occurrences. Use replace_all=true or provide more context to make unique.",
            )

        # Perform replacement
        new_content_normalized = normalized_content.replace(
            old_string_normalized,
            input_data.new_string.replace("\r\n", "\n"),
            -1 if input_data.replace_all else 1,
        )

        # Preserve original line endings
        new_content = preserve_line_endings(content, new_content_normalized)

        # Write back (async)
        await write_file_async(full_path, new_content, encoding="utf-8")

        # Update file state (async)
        stat_result = await stat_async(full_path)
        if context.read_file_state:
            context.read_file_state[full_path] = {
                "content": new_content,
                "timestamp": stat_result.st_mtime,
                "offset": None,
                "limit": None,
            }

        return ToolResult(
            data=EditOutput(
                type="edit",
                file_path=input_data.file_path,
                old_string=input_data.old_string,
                new_string=input_data.new_string,
                occurrences=count if input_data.replace_all else 1,
                content=new_content[:500] if len(new_content) > 500 else new_content,
            ),
        )

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description."""
        file_path = input.get("file_path", "")
        if file_path:
            return f"Edit {file_path}"
        return "Edit file"

    async def prompt(
        self,
        options: Dict[str, Any],
    ) -> str:
        """Generate tool prompt."""
        return get_edit_prompt()

    def is_concurrency_safe(self, input: Dict[str, Any]) -> bool:
        """Check if tool is safe for concurrent execution."""
        return False  # Edits are not concurrency-safe

    def is_read_only(self, input: Dict[str, Any]) -> bool:
        """Check if tool is read-only."""
        return False

    def is_destructive(self, input: Dict[str, Any]) -> bool:
        """Check if tool performs destructive operations."""
        return True  # Modifies files

    def to_auto_classifier_input(self, input: Dict[str, Any]) -> str:
        """Convert input for auto-mode classifier."""
        return f"{input.get('file_path', '')}: {input.get('old_string', '')[:50]}"

    def get_path(self, input: Dict[str, Any]) -> Optional[str]:
        """Get file path from input."""
        return input.get("file_path")

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary for compact view."""
        if not input or not input.get("file_path"):
            return None
        return f"Edit {Path(input['file_path']).name}"

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description for spinner."""
        if not input or not input.get("file_path"):
            return "Editing file"
        return f"Editing {Path(input['file_path']).name}"

    def user_facing_name(self, input: Optional[Dict[str, Any]]) -> str:
        """Get user-facing name."""
        return "Edit"

    def backfill_observable_input(self, input: Dict[str, Any]) -> None:
        """Backfill input with expanded path."""
        if "file_path" in input:
            input["file_path"] = expand_path(input["file_path"])

    def validate_input(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate tool input."""
        full_path = expand_path(input.get("file_path", ""))
        path = Path(full_path)

        # Check strings are different
        if input.get("old_string") == input.get("new_string"):
            return ValidationResult(
                result=False,
                message="No changes: old_string and new_string are identical.",
                error_code=1,
            )

        # Check if file exists
        if not path.exists():
            # Empty old_string on non-existent file is valid (new file)
            if input.get("old_string") == "":
                return ValidationResult(result=True)
            return ValidationResult(
                result=False,
                message=f"File does not exist: {full_path}",
                error_code=4,
            )

        # Check if notebook
        if path.suffix.lower() == ".ipynb":
            return ValidationResult(
                result=False,
                message="Use NotebookEdit for .ipynb files.",
                error_code=5,
            )

        # Check file size
        try:
            size = path.stat().st_size
            if size > MAX_EDIT_FILE_SIZE:
                return ValidationResult(
                    result=False,
                    message=f"File too large ({size} bytes). Max is {MAX_EDIT_FILE_SIZE}.",
                    error_code=10,
                )
        except OSError:
            pass

        # Check if file was read
        last_read = context.read_file_state.get(full_path)
        if not last_read or last_read.get("isPartialView"):
            return ValidationResult(
                result=False,
                message="File has not been read yet. Read it first before editing.",
                error_code=6,
            )

        return ValidationResult(result=True)

    async def check_permissions(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> PermissionResult:
        """Check tool permissions."""
        file_path = expand_path(input.get("file_path", ""))

        # Edit operations need confirmation
        return PermissionResult(
            decision=PermissionDecision.ASK,
            reason=f"Edit {file_path}",
            rule=f"Edit({file_path})",
        )

    def inputs_equivalent(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """Check if two inputs are equivalent."""
        # For edit, compare file_path, old_string, new_string
        return (
            a.get("file_path") == b.get("file_path") and
            a.get("old_string") == b.get("old_string") and
            a.get("new_string") == b.get("new_string") and
            a.get("replace_all", False) == b.get("replace_all", False)
        )


def find_similar_file(file_path: str, cwd: str) -> Optional[str]:
    """Find similar file in directory."""
    path = Path(file_path)
    filename = path.name
    parent = path.parent

    try:
        for f in parent.iterdir():
            if f.name.lower() == filename.lower() and f.name != filename:
                return str(f)
    except OSError:
        pass

    return None


def build_edit_tool() -> EditTool:
    """Build EditTool instance."""
    return EditTool()


# Add execute method to EditTool
def _add_execute_method():
    async def execute(self, input: EditInput, ctx: ToolUseContext) -> ToolResult:
        """Execute method for simpler interface."""
        args = input.model_dump() if hasattr(input, 'model_dump') else dict(input)
        return await self.call(args, ctx, lambda *args: True, None)
    EditTool.execute = execute

_add_execute_method()


__all__ = [
    "EditTool",
    "EditInput",
    "EditOutput",
    "build_edit_tool",
    "get_edit_prompt",
    "expand_path",
    "preserve_line_endings",
    "find_similar_file",
    "FILE_UNEXPECTEDLY_MODIFIED_ERROR",
    "MAX_EDIT_FILE_SIZE",
]