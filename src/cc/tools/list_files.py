"""List Files Tool - Directory listing."""

from __future__ import annotations
import os
from pathlib import Path
from typing import ClassVar, List, Optional
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class ListFilesInput(ToolInput):
    """Input for ListFilesTool."""
    path: Optional[str] = Field(default=None, description="Directory path to list")
    pattern: Optional[str] = Field(default=None, description="Filter pattern (glob)")
    show_hidden: bool = Field(default=False, description="Show hidden files")
    max_depth: int = Field(default=1, description="Maximum depth to traverse")
    sort_by: str = Field(default="name", description="Sort by: name, size, time")


class FileInfo(BaseModel):
    """File information."""
    name: str
    path: str
    is_dir: bool
    size: int = 0
    modified: Optional[str] = None


class ListFilesTool(ToolDef):
    """List files in a directory."""

    name: ClassVar[str] = "ListFiles"
    description: ClassVar[str] = "List files and directories with optional filtering"
    input_schema: ClassVar[type] = ListFilesInput

    async def execute(self, input: ListFilesInput, ctx: ToolUseContext) -> ToolResult:
        """List files."""
        try:
            path = Path(input.path or ctx.cwd)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path

            if not path.exists():
                return ToolResult(
                    content=f"Directory not found: {path}",
                    is_error=True,
                )

            if not path.is_dir():
                return ToolResult(
                    content=f"Not a directory: {path}",
                    is_error=True,
                )

            # Collect files
            files = self._collect_files(path, input)

            # Sort
            sort_by = input.sort_by
            if sort_by == "size":
                files.sort(key=lambda f: f.size)
            elif sort_by == "time":
                files.sort(key=lambda f: f.modified or "")
            else:
                files.sort(key=lambda f: f.name.lower())

            # Format output
            lines = [f"Directory: {path}\n"]
            for f in files:
                icon = "📁" if f.is_dir else "📄"
                size_str = "" if f.is_dir else f" ({self._format_size(f.size)})"
                lines.append(f"{icon} {f.name}{size_str}")

            return ToolResult(
                content="\n".join(lines),
                metadata={
                    "path": str(path),
                    "total": len(files),
                    "files": [f.model_dump() for f in files],
                },
            )

        except Exception as e:
            return ToolResult(
                content=f"Error listing files: {e}",
                is_error=True,
            )

    def _collect_files(self, path: Path, input: ListFilesInput) -> List[FileInfo]:
        """Collect files from directory."""
        files = []
        pattern = input.pattern or "*"

        for item in path.iterdir():
            # Skip hidden if not requested
            if not input.show_hidden and item.name.startswith("."):
                continue

            # Pattern match
            if not self._matches_pattern(item.name, pattern):
                continue

            info = FileInfo(
                name=item.name,
                path=str(item),
                is_dir=item.is_dir(),
                size=item.stat().st_size if item.is_file() else 0,
                modified=self._format_time(item.stat().st_mtime),
            )
            files.append(info)

            # Recursion
            if input.max_depth > 1 and item.is_dir():
                sub_files = self._collect_files(item, input)
                for sf in sub_files:
                    sf.name = f"{item.name}/{sf.name}"
                    files.append(sf)

        return files

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches pattern."""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)

    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

    def _format_time(self, timestamp: float) -> str:
        """Format modification time."""
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")


__all__ = ["ListFilesTool", "ListFilesInput", "FileInfo"]