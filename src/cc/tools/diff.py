"""Diff Tool - Compare files or directories."""

from __future__ import annotations
import difflib
from pathlib import Path
from typing import ClassVar
from pydantic import Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class DiffInput(ToolInput):
    """Input for DiffTool."""
    source: str = Field(description="Source file path")
    target: str = Field(description="Target file path")
    context_lines: int = Field(default=3, description="Context lines around changes")
    show_unified: bool = Field(default=True, description="Show unified diff format")


class DiffTool(ToolDef):
    """Compare files and show differences."""

    name: ClassVar[str] = "Diff"
    description: ClassVar[str] = "Compare two files and show differences"
    input_schema: ClassVar[type] = DiffInput

    async def execute(self, input: DiffInput, ctx: ToolUseContext) -> ToolResult:
        """Compare files."""
        try:
            source = Path(input.source)
            target = Path(input.target)

            if not source.is_absolute():
                source = Path(ctx.cwd) / source
            if not target.is_absolute():
                target = Path(ctx.cwd) / target

            if not source.exists():
                return ToolResult(
                    content=f"Source not found: {source}",
                    is_error=True,
                )

            if not target.exists():
                return ToolResult(
                    content=f"Target not found: {target}",
                    is_error=True,
                )

            # Read files
            source_lines = source.read_text(encoding="utf-8").splitlines()
            target_lines = target.read_text(encoding="utf-8").splitlines()

            # Generate diff
            if input.show_unified:
                diff = difflib.unified_diff(
                    source_lines,
                    target_lines,
                    fromfile=str(source),
                    tofile=str(target),
                    n=input.context_lines,
                )
            else:
                diff = difflib.context_diff(
                    source_lines,
                    target_lines,
                    fromfile=str(source),
                    tofile=str(target),
                    n=input.context_lines,
                )

            diff_text = "\n".join(diff)

            if not diff_text:
                diff_text = "Files are identical."

            # Count changes
            additions = len([l for l in diff if l.startswith("+") and not l.startswith("++")])
            deletions = len([l for l in diff if l.startswith("-") and not l.startswith("--")])

            return ToolResult(
                content=diff_text,
                metadata={
                    "source": str(source),
                    "target": str(target),
                    "additions": additions,
                    "deletions": deletions,
                    "changed": additions + deletions > 0,
                },
            )

        except Exception as e:
            return ToolResult(
                content=f"Error comparing files: {e}",
                is_error=True,
            )


__all__ = ["DiffTool", "DiffInput"]