"""EditTool - File editing with string replacement."""

from pathlib import Path
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
from ..types.permission import PermissionResult, PermissionDecision


class EditInput(ToolInput):
    """Input for EditTool."""

    file_path: str
    old_string: str
    new_string: str
    replace_all: bool = False


class EditTool(ToolDef):
    """Edit files by replacing strings."""

    name: ClassVar[str] = "Edit"
    description: ClassVar[str] = "Edit a file by replacing an exact string match"
    input_schema: ClassVar[type[ToolInput]] = EditInput

    async def execute(self, input: EditInput, ctx: ToolUseContext) -> ToolResult:
        """Execute the edit."""
        try:
            path = Path(input.file_path)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path

            if not path.exists():
                return ToolResult(
                    content=f"File not found: {path}",
                    is_error=True,
                )

            if not path.is_file():
                return ToolResult(
                    content=f"Not a file: {path}",
                    is_error=True,
                )

            # Read file
            content = path.read_text(encoding="utf-8")

            # Count occurrences
            count = content.count(input.old_string)
            if count == 0:
                return ToolResult(
                    content=f"String not found in file: '{input.old_string[:50]}...'",
                    is_error=True,
                )

            # Check uniqueness if not replace_all
            if not input.replace_all and count > 1:
                return ToolResult(
                    content=f"Found {count} occurrences. Use replace_all=true or provide more context to make the match unique.",
                    is_error=True,
                    metadata={"occurrences": count},
                )

            # Perform replacement
            if input.replace_all:
                new_content = content.replace(input.old_string, input.new_string)
            else:
                # Only replace first occurrence
                new_content = content.replace(input.old_string, input.new_string, 1)

            # Write back
            path.write_text(new_content, encoding="utf-8")

            return ToolResult(
                content=f"Successfully replaced {count if input.replace_all else 1} occurrence(s) in {path}",
                metadata={
                    "path": str(path),
                    "replacements": count if input.replace_all else 1,
                },
            )

        except Exception as e:
            return ToolResult(
                content=f"Error editing file: {e}",
                is_error=True,
            )

    def check_permission(self, input: EditInput, ctx: ToolUseContext) -> PermissionResult:
        """Check if edit is allowed."""
        return PermissionResult(
            decision=PermissionDecision.ASK.value,
            reason="File edit operation",
        )