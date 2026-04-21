"""File Operations Tools - Move, Copy, Delete files."""

from __future__ import annotations
import shutil
from pathlib import Path
from typing import ClassVar
from pydantic import Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
from ..types.permission import PermissionResult, PermissionDecision


class MoveInput(ToolInput):
    """Input for MoveTool."""
    source: str = Field(description="Source file path")
    destination: str = Field(description="Destination file path")
    overwrite: bool = Field(default=False, description="Overwrite existing file")


class CopyInput(ToolInput):
    """Input for CopyTool."""
    source: str = Field(description="Source file path")
    destination: str = Field(description="Destination file path")
    overwrite: bool = Field(default=False, description="Overwrite existing file")


class DeleteInput(ToolInput):
    """Input for DeleteTool."""
    path: str = Field(description="File or directory path to delete")
    recursive: bool = Field(default=False, description="Delete directories recursively")


class MoveTool(ToolDef):
    """Move files or directories."""

    name: ClassVar[str] = "Move"
    description: ClassVar[str] = "Move a file or directory to a new location"
    input_schema: ClassVar[type] = MoveInput

    async def execute(self, input: MoveInput, ctx: ToolUseContext) -> ToolResult:
        """Move the file."""
        try:
            source = Path(input.source)
            dest = Path(input.destination)

            if not source.is_absolute():
                source = Path(ctx.cwd) / source
            if not dest.is_absolute():
                dest = Path(ctx.cwd) / dest

            if not source.exists():
                return ToolResult(
                    content=f"Source not found: {source}",
                    is_error=True,
                )

            if dest.exists() and not input.overwrite:
                return ToolResult(
                    content=f"Destination already exists: {dest}",
                    is_error=True,
                )

            # Create parent directory if needed
            dest.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(source), str(dest))

            return ToolResult(
                content=f"Moved {source} to {dest}",
                metadata={"source": str(source), "destination": str(dest)},
            )

        except Exception as e:
            return ToolResult(
                content=f"Error moving file: {e}",
                is_error=True,
            )

    def check_permission(self, input: MoveInput, ctx: ToolUseContext) -> PermissionResult:
        return PermissionResult(
            decision=PermissionDecision.ASK.value,
            reason="File move operation",
        )


class CopyTool(ToolDef):
    """Copy files or directories."""

    name: ClassVar[str] = "Copy"
    description: ClassVar[str] = "Copy a file or directory"
    input_schema: ClassVar[type] = CopyInput

    async def execute(self, input: CopyInput, ctx: ToolUseContext) -> ToolResult:
        """Copy the file."""
        try:
            source = Path(input.source)
            dest = Path(input.destination)

            if not source.is_absolute():
                source = Path(ctx.cwd) / source
            if not dest.is_absolute():
                dest = Path(ctx.cwd) / dest

            if not source.exists():
                return ToolResult(
                    content=f"Source not found: {source}",
                    is_error=True,
                )

            if dest.exists() and not input.overwrite:
                return ToolResult(
                    content=f"Destination already exists: {dest}",
                    is_error=True,
                )

            # Create parent directory if needed
            dest.parent.mkdir(parents=True, exist_ok=True)

            if source.is_dir():
                shutil.copytree(str(source), str(dest), dirs_exist_ok=input.overwrite)
            else:
                shutil.copy2(str(source), str(dest))

            return ToolResult(
                content=f"Copied {source} to {dest}",
                metadata={"source": str(source), "destination": str(dest)},
            )

        except Exception as e:
            return ToolResult(
                content=f"Error copying file: {e}",
                is_error=True,
            )

    def check_permission(self, input: CopyInput, ctx: ToolUseContext) -> PermissionResult:
        return PermissionResult(
            decision=PermissionDecision.ASK.value,
            reason="File copy operation",
        )


class DeleteTool(ToolDef):
    """Delete files or directories."""

    name: ClassVar[str] = "Delete"
    description: ClassVar[str] = "Delete a file or directory"
    input_schema: ClassVar[type] = DeleteInput

    async def execute(self, input: DeleteInput, ctx: ToolUseContext) -> ToolResult:
        """Delete the file or directory."""
        try:
            path = Path(input.path)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path

            if not path.exists():
                return ToolResult(
                    content=f"Path not found: {path}",
                    is_error=True,
                )

            if path.is_dir():
                if not input.recursive and any(path.iterdir()):
                    return ToolResult(
                        content=f"Directory not empty: {path}. Use recursive=True to delete.",
                        is_error=True,
                    )
                shutil.rmtree(str(path)) if input.recursive else path.rmdir()
            else:
                path.unlink()

            return ToolResult(
                content=f"Deleted {path}",
                metadata={"path": str(path)},
            )

        except Exception as e:
            return ToolResult(
                content=f"Error deleting: {e}",
                is_error=True,
            )

    def check_permission(self, input: DeleteInput, ctx: ToolUseContext) -> PermissionResult:
        return PermissionResult(
            decision=PermissionDecision.ASK.value,
            reason="File delete operation - destructive",
        )


__all__ = ["MoveTool", "MoveInput", "CopyTool", "CopyInput", "DeleteTool", "DeleteInput"]