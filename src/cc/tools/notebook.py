"""NotebookEditTool - Jupyter notebook editing."""

import json
from pathlib import Path
from typing import ClassVar, Literal

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class NotebookEditInput(ToolInput):
    """Input for NotebookEditTool."""

    notebook_path: str
    cell_id: str | None = None
    cell_number: int | None = None
    cell_type: Literal["code", "markdown"] | None = None
    new_source: str
    edit_mode: Literal["replace", "insert", "delete"] = "replace"


class NotebookEditTool(ToolDef):
    """Edit Jupyter notebooks."""

    name: ClassVar[str] = "NotebookEdit"
    description: ClassVar[str] = "Edit cells in Jupyter notebooks (.ipynb files)"
    input_schema: ClassVar[type[ToolInput]] = NotebookEditInput

    async def execute(self, input: NotebookEditInput, ctx: ToolUseContext) -> ToolResult:
        """Execute notebook edit."""
        try:
            path = Path(input.notebook_path)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path

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

            # Read notebook
            notebook = json.loads(path.read_text())

            cells = notebook.get("cells", [])

            if input.edit_mode == "delete":
                # Delete cell
                if input.cell_number is not None and 0 <= input.cell_number < len(cells):
                    del cells[input.cell_number]
                    action = f"Deleted cell {input.cell_number}"
                elif input.cell_id:
                    for i, cell in enumerate(cells):
                        if cell.get("id") == input.cell_id:
                            del cells[i]
                            action = f"Deleted cell with id {input.cell_id}"
                            break
                else:
                    return ToolResult(content="Need cell_number or cell_id for delete", is_error=True)

            elif input.edit_mode == "insert":
                # Insert new cell
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
                action = f"Inserted cell at position {insert_at}"

            else:  # replace
                # Replace cell content
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
                else:
                    return ToolResult(content="Need cell_number or cell_id for replace", is_error=True)

            # Write back
            notebook["cells"] = cells
            path.write_text(json.dumps(notebook, indent=1))

            return ToolResult(
                content=f"{action} in {path}",
                metadata={"cells_count": len(cells)},
            )

        except json.JSONDecodeError:
            return ToolResult(
                content=f"Invalid notebook format",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"Error editing notebook: {e}",
                is_error=True,
            )


def read_notebook(path: Path) -> dict:
    """Read notebook structure."""
    notebook = json.loads(path.read_text())
    return {
        "cells": len(notebook.get("cells", [])),
        "cell_types": [c.get("cell_type") for c in notebook.get("cells", [])],
        "metadata": notebook.get("metadata", {}),
    }