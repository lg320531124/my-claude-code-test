"""GrepTool - Content search using ripgrep."""

import subprocess
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class GrepInput(ToolInput):
    """Input for GrepTool."""

    pattern: str
    path: str | None = None
    output_mode: str = "content"  # content, files_with_matches, count
    glob: str | None = None
    head_limit: int | None = None


class GrepTool(ToolDef):
    """Search file contents using ripgrep."""

    name: ClassVar[str] = "Grep"
    description: ClassVar[str] = "Search for patterns in file contents (ripgrep)"
    input_schema: ClassVar[type[ToolInput]] = GrepInput

    async def execute(self, input: GrepInput, ctx: ToolUseContext) -> ToolResult:
        """Execute grep search."""
        try:
            # Build ripgrep command
            cmd = ["rg", "--line-number"]

            # Output mode
            if input.output_mode == "files_with_matches":
                cmd.append("--files-with-matches")
            elif input.output_mode == "count":
                cmd.append("--count")

            # Glob filter
            if input.glob:
                cmd.extend(["--glob", input.glob])

            # Head limit
            if input.head_limit:
                cmd.extend(["--max-count", str(input.head_limit)])

            # Pattern and path
            cmd.append(input.pattern)
            if input.path:
                cmd.append(input.path)
            else:
                cmd.append(ctx.cwd)

            # Run ripgrep
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=ctx.cwd,
            )

            if proc.returncode != 0 and not proc.stdout:
                return ToolResult(
                    content="No matches found",
                    metadata={"pattern": input.pattern},
                )

            return ToolResult(
                content=proc.stdout or "No matches found",
                metadata={"pattern": input.pattern, "output_mode": input.output_mode},
            )

        except FileNotFoundError:
            return ToolResult(
                content="ripgrep (rg) not installed. Install with: brew install ripgrep",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"Error in grep search: {e}",
                is_error=True,
            )