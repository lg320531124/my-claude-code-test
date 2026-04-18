"""WriteTool - File writing."""

from pathlib import Path
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
from ..types.permission import PermissionResult, PermissionDecision


class WriteInput(ToolInput):
    """Input for WriteTool."""

    file_path: str
    content: str


class WriteTool(ToolDef):
    """Write files to the filesystem."""

    name: ClassVar[str] = "Write"
    description: ClassVar[str] = "Write or overwrite file contents"
    input_schema: ClassVar[type[ToolInput]] = WriteInput

    async def execute(self, input: WriteInput, ctx: ToolUseContext) -> ToolResult:
        """Write the file."""
        try:
            path = Path(input.file_path)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            path.write_text(input.content, encoding="utf-8")

            return ToolResult(
                content=f"Successfully wrote {len(input.content)} chars to {path}",
                metadata={"path": str(path), "size": len(input.content)},
            )

        except Exception as e:
            return ToolResult(
                content=f"Error writing file: {e}",
                is_error=True,
            )

    def check_permission(self, input: WriteInput, ctx: ToolUseContext) -> PermissionResult:
        """Check if write is allowed."""
        # Write operations need confirmation by default
        return PermissionResult(
            decision=PermissionDecision.ASK.value,
            reason="File write operation",
        )