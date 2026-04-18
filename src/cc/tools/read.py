"""ReadTool - File reading."""

from pathlib import Path
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class ReadInput(ToolInput):
    """Input for ReadTool."""

    file_path: str
    limit: int | None = None
    offset: int | None = None


class ReadTool(ToolDef):
    """Read files from the filesystem."""

    name: ClassVar[str] = "Read"
    description: ClassVar[str] = "Read file contents with optional pagination"
    input_schema: ClassVar[type[ToolInput]] = ReadInput

    async def execute(self, input: ReadInput, ctx: ToolUseContext) -> ToolResult:
        """Read the file."""
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
            content = path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            # Apply pagination
            if input.offset:
                lines = lines[input.offset:]
            if input.limit:
                lines = lines[:input.limit]

            # Add line numbers
            numbered = "\n".join(
                f"{i + (input.offset or 0) + 1:6}\t{line}"
                for i, line in enumerate(lines)
            )

            return ToolResult(
                content=numbered,
                metadata={
                    "path": str(path),
                    "total_lines": len(content.splitlines()),
                    "shown_lines": len(lines),
                },
            )

        except Exception as e:
            return ToolResult(
                content=f"Error reading file: {e}",
                is_error=True,
            )