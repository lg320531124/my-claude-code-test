"""TodoWriteTool - Todo list management."""

from __future__ import annotations
from typing import Optional, ClassVar
from datetime import datetime

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class TodoItem(ToolInput):
    """A todo item."""

    content: str
    activeForm: Optional[str] = None


class TodoWriteInput(ToolInput):
    """Input for TodoWriteTool."""

    todos: List[TodoItem]


# In-memory todo storage
_todos: List[dict] = []


class TodoWriteTool(ToolDef):
    """Write todo list."""

    name: ClassVar[str] = "TodoWrite"
    description: ClassVar[str] = "Write a todo list for tracking work during a session"
    input_schema: ClassVar[type] = TodoWriteInput

    async def execute(self, input: TodoWriteInput, ctx: ToolUseContext) -> ToolResult:
        """Write todos."""
        global _todos

        # Clear existing and add new
        _todos = []
        for i, item in enumerate(input.todos):
            _todos.append({
                "id": i + 1,
                "content": item.content,
                "activeForm": item.activeForm or item.content,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            })

        return ToolResult(
            content=self._format_todos(),
            metadata={"todos_count": len(_todos)},
        )

    def _format_todos(self) -> str:
        """Format todo list."""
        if not _todos:
            return "No todos"

        lines = ["# Todo List"]
        for todo in _todos:
            status_icon = "○" if todo["status"] == "pending" else "●"
            lines.append(f"{status_icon} {todo['id']}. {todo['content']}")

        return "\n".join(lines)


def get_todos() -> List[dict]:
    """Get current todos."""
    return _todos


def update_todo_status(todo_id: int, status: str) -> None:
    """Update todo status."""
    for todo in _todos:
        if todo["id"] == todo_id:
            todo["status"] = status
            todo["updated_at"] = datetime.now().isoformat()
            break


def clear_todos() -> None:
    """Clear todos."""
    _todos.clear()
