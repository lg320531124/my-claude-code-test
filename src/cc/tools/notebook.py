"""NotebookEditTool - Jupyter notebook editing with asyncio."""

from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import ClassVar, Literal, Optional

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class NotebookEditInput(ToolInput):
    """Input for NotebookEditTool."""

    notebook_path: str
    cell_id: Optional[str] = None
    cell_number: Optional[int] = None
    cell_type: Literal["code", "markdown"] | None = None
    new_source: str
    edit_mode: Literal["replace", "insert", "delete"] = "replace"


class NotebookEditTool(ToolDef):
    """Edit Jupyter notebooks."""

    name: ClassVar[str] = "NotebookEdit"
    description: ClassVar[str] = "Edit cells in Jupyter notebooks (.ipynb files)"
    input_schema: ClassVar[type] = NotebookEditInput

    async def execute(self, input: NotebookEditInput, ctx: ToolUseContext) -> ToolResult:
        """Execute notebook edit with asyncio."""
        try:
            # Use asyncio for file operations
            path = await self._resolve_path(input.notebook_path, ctx)

            if not path.exists():
                return ToolResult(
                    content=f"Notebook not found: {path}",
                    is_error=True,
                )

            if not path.suffix == ".ipynb":
                return ToolResult(
                    content=f"Not a notebook file: {path}",
                    is_error=True,
                )

            # Read notebook asynchronously
            notebook = await self._read_notebook(path)
            cells = notebook.get("cells", [])

            if input.edit_mode == "delete":
                cells, action = await self._delete_cell(cells, input)
            elif input.edit_mode == "insert":
                cells, action = await self._insert_cell(cells, input)
            else:
                cells, action = await self._replace_cell(cells, input)

            if action is None:
                return ToolResult(
                    content="Need cell_number or cell_id",
                    is_error=True,
                )

            # Write back asynchronously
            notebook["cells"] = cells
            await self._write_notebook(path, notebook)

            return ToolResult(
                content=f"{action} in {path}",
                metadata={"cells_count": len(cells)},
            )

        except json.JSONDecodeError:
            return ToolResult(content="Invalid notebook format", is_error=True)
        except Exception as e:
            return ToolResult(content=f"Error: {e}", is_error=True)

    async def _resolve_path(self, path_str: str, ctx: ToolUseContext) -> Path:
        """Resolve path asynchronously."""
        path = Path(path_str)
        if not path.is_absolute():
            path = Path(ctx.cwd) / path
        return path

    async def _read_notebook(self, path: Path) -> dict:
        """Read notebook file."""
        # Run in executor for I/O
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, path.read_text)
        return json.loads(content)

    async def _write_notebook(self, path: Path, notebook: dict) -> None:
        """Write notebook file."""
        loop = asyncio.get_event_loop()
        content = json.dumps(notebook, indent=1)
        await loop.run_in_executor(None, path.write_text, content)

    async def _delete_cell(self, cells: list, input: NotebookEditInput) -> tuple[list, str | None]:
        """Delete cell."""
        action = None
        if input.cell_number is not None and 0 <= input.cell_number < len(cells):
            del cells[input.cell_number]
            action = f"Deleted cell {input.cell_number}"
        elif input.cell_id:
            for i, cell in enumerate(cells):
                if cell.get("id") == input.cell_id:
                    del cells[i]
                    action = f"Deleted cell with id {input.cell_id}"
                    break
        return cells, action

    async def _insert_cell(self, cells: list, input: NotebookEditInput) -> tuple[list, str]:
        """Insert new cell."""
        new_cell = {
            "cell_type": input.cell_type or "code",
            "source": input.new_source.split("\n"),
            "metadata": {},
            "outputs": [] if input.cell_type == "code" else None,
            "execution_count": None if input.cell_type == "code" else None,
        }
        if input.cell_id:
            new_cell["id"] = input.cell_id

        insert_at = input.cell_number if input.cell_number is not None else len(cells)
        cells.insert(insert_at, new_cell)
        return cells, f"Inserted cell at position {insert_at}"

    async def _replace_cell(self, cells: list, input: NotebookEditInput) -> tuple[list, str | None]:
        """Replace cell content."""
        action = None
        if input.cell_number is not None and 0 <= input.cell_number < len(cells):
            cell = cells[input.cell_number]
            cell["source"] = input.new_source.split("\n")
            if input.cell_type:
                cell["cell_type"] = input.cell_type
            action = f"Replaced cell {input.cell_number}"
        elif input.cell_id:
            for cell in cells:
                if cell.get("id") == input.cell_id:
                    cell["source"] = input.new_source.split("\n")
                    if input.cell_type:
                        cell["cell_type"] = input.cell_type
                    action = f"Replaced cell with id {input.cell_id}"
                    break
        return cells, action


async def read_notebook_async(path: Path) -> dict:
    """Read notebook structure asynchronously."""
    loop = asyncio.get_event_loop()
    content = await loop.run_in_executor(None, path.read_text)
    notebook = json.loads(content)
    return {
        "cells": len(notebook.get("cells", [])),
        "cell_types": [c.get("cell_type") for c in notebook.get("cells", [])],
        "metadata": notebook.get("metadata", {}),
    }


def read_notebook(path: Path) -> dict:
    """Read notebook structure (sync wrapper)."""
    notebook = json.loads(path.read_text())
    return {
        "cells": len(notebook.get("cells", [])),
        "cell_types": [c.get("cell_type") for c in notebook.get("cells", [])],
        "metadata": notebook.get("metadata", {}),
    }
