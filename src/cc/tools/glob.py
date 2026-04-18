"""GlobTool - File pattern matching."""

from pathlib import Path
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class GlobInput(ToolInput):
    """Input for GlobTool."""

    pattern: str
    path: str | None = None


class GlobTool(ToolDef):
    """Find files by glob pattern."""

    name: ClassVar[str] = "Glob"
    description: ClassVar[str] = "Find files matching glob patterns"
    input_schema: ClassVar[type[ToolInput]] = GlobInput

    async def execute(self, input: GlobInput, ctx: ToolUseContext) -> ToolResult:
        """Execute glob search."""
        try:
            base_path = Path(input.path or ctx.cwd)
            if not base_path.is_absolute():
                base_path = Path(ctx.cwd) / base_path

            # Find matching files
            matches = sorted(base_path.glob(input.pattern), key=lambda p: p.stat().st_mtime, reverse=True)

            # Format output
            if not matches:
                return ToolResult(content="No files found matching pattern")

            output_lines = [str(m.relative_to(base_path)) for m in matches]
            return ToolResult(
                content="\n".join(output_lines),
                metadata={"count": len(matches), "pattern": input.pattern},
            )

        except Exception as e:
            return ToolResult(
                content=f"Error in glob search: {e}",
                is_error=True,
            )