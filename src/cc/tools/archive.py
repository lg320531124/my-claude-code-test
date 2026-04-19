"""Archive Tool - Archive file operations."""

from __future__ import annotations
import zipfile
import tarfile
import shutil
from pathlib import Path
from typing import ClassVar, List, Optional
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class ArchiveInput(ToolInput):
    """Input for ArchiveTool."""
    action: str = Field(description="Action: create, extract, list, info")
    archive_path: str = Field(description="Archive file path")
    source: Optional[str] = Field(default=None, description="Source path for create")
    destination: Optional[str] = Field(default=None, description="Destination for extract")
    format: str = Field(default="zip", description="Archive format: zip, tar, tar.gz")
    files: Optional[List[str]] = Field(default=None, description="Files to include")


class ArchiveTool(ToolDef):
    """Archive file operations."""

    name: ClassVar[str] = "Archive"
    description: ClassVar[str] = "Create, extract, and manage archive files"
    input_schema: ClassVar[type] = ArchiveInput

    SUPPORTED_FORMATS = ["zip", "tar", "tar.gz", "tar.bz2"]

    async def execute(self, input: ArchiveInput, ctx: ToolUseContext) -> ToolResult:
        """Execute archive operation."""
        action = input.action

        try:
            if action == "create":
                return self._create_archive(input, ctx)
            elif action == "extract":
                return self._extract_archive(input, ctx)
            elif action == "list":
                return self._list_archive(input, ctx)
            elif action == "info":
                return self._archive_info(input, ctx)
            else:
                return ToolResult(
                    content=f"Unknown action: {action}",
                    is_error=True,
                )
        except Exception as e:
            return ToolResult(
                content=f"Archive error: {e}",
                is_error=True,
            )

    def _create_archive(self, input: ArchiveInput, ctx: ToolUseContext) -> ToolResult:
        """Create archive."""
        archive_path = Path(input.archive_path)
        if not archive_path.is_absolute():
            archive_path = Path(ctx.cwd) / archive_path

        source = Path(input.source or ctx.cwd)
        if not source.is_absolute():
            source = Path(ctx.cwd) / source

        format = input.format.lower()
        if format not in self.SUPPORTED_FORMATS:
            return ToolResult(
                content=f"Unsupported format: {format}",
                is_error=True,
            )

        files_added = 0

        if format == "zip":
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                if input.files:
                    for f in input.files:
                        file_path = source / f
                        if file_path.exists():
                            zf.write(file_path, f)
                            files_added += 1
                else:
                    for file_path in source.rglob("*"):
                        if file_path.is_file():
                            rel_path = file_path.relative_to(source)
                            zf.write(file_path, rel_path)
                            files_added += 1

        elif format in ["tar", "tar.gz", "tar.bz2"]:
            mode = "w" if format == "tar" else f"w:{format.split('.')[-1]}"
            with tarfile.open(archive_path, mode) as tf:
                if input.files:
                    for f in input.files:
                        file_path = source / f
                        if file_path.exists():
                            tf.add(file_path, f)
                            files_added += 1
                else:
                    tf.add(source, source.name)
                    files_added = len(list(source.rglob("*")))

        return ToolResult(
            content=f"Created archive: {archive_path}\nFiles: {files_added}",
            metadata={"archive": str(archive_path), "format": format, "files": files_added},
        )

    def _extract_archive(self, input: ArchiveInput, ctx: ToolUseContext) -> ToolResult:
        """Extract archive."""
        archive_path = Path(input.archive_path)
        if not archive_path.is_absolute():
            archive_path = Path(ctx.cwd) / archive_path

        if not archive_path.exists():
            return ToolResult(
                content=f"Archive not found: {archive_path}",
                is_error=True,
            )

        dest = Path(input.destination or ctx.cwd)
        if not dest.is_absolute():
            dest = Path(ctx.cwd) / dest

        dest.mkdir(parents=True, exist_ok=True)

        files_extracted = 0

        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest)
                files_extracted = len(zf.namelist())

        elif ".tar" in archive_path.name:
            with tarfile.open(archive_path, "r:*") as tf:
                tf.extractall(dest)
                files_extracted = len(tf.getnames())

        return ToolResult(
            content=f"Extracted to: {dest}\nFiles: {files_extracted}",
            metadata={"destination": str(dest), "files": files_extracted},
        )

    def _list_archive(self, input: ArchiveInput, ctx: ToolUseContext) -> ToolResult:
        """List archive contents."""
        archive_path = Path(input.archive_path)
        if not archive_path.is_absolute():
            archive_path = Path(ctx.cwd) / archive_path

        if not archive_path.exists():
            return ToolResult(
                content=f"Archive not found: {archive_path}",
                is_error=True,
            )

        files = []

        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                for info in zf.infolist():
                    files.append({
                        "name": info.filename,
                        "size": info.file_size,
                        "compressed": info.compress_size,
                        "is_dir": info.is_dir(),
                    })

        elif ".tar" in archive_path.name:
            with tarfile.open(archive_path, "r:*") as tf:
                for member in tf.getmembers():
                    files.append({
                        "name": member.name,
                        "size": member.size,
                        "is_dir": member.isdir(),
                    })

        lines = [f["name"] for f in files]

        return ToolResult(
            content="\n".join(lines),
            metadata={"files": files, "count": len(files)},
        )

    def _archive_info(self, input: ArchiveInput, ctx: ToolUseContext) -> ToolResult:
        """Get archive info."""
        archive_path = Path(input.archive_path)
        if not archive_path.is_absolute():
            archive_path = Path(ctx.cwd) / archive_path

        if not archive_path.exists():
            return ToolResult(
                content=f"Archive not found: {archive_path}",
                is_error=True,
            )

        stat = archive_path.stat()

        info = {
            "path": str(archive_path),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "format": self._detect_format(archive_path),
        }

        return ToolResult(
            content=f"Archive: {archive_path}\nSize: {stat.st_size}\nFormat: {info['format']}",
            metadata=info,
        )

    def _detect_format(self, path: Path) -> str:
        """Detect archive format."""
        name = path.name.lower()
        if name.endswith(".zip"):
            return "zip"
        elif name.endswith(".tar.gz") or name.endswith(".tgz"):
            return "tar.gz"
        elif name.endswith(".tar.bz2") or name.endswith(".tbz2"):
            return "tar.bz2"
        elif name.endswith(".tar"):
            return "tar"
        return "unknown"


__all__ = ["ArchiveTool", "ArchiveInput"]