"""TaskTools - Task management."""

from __future__ import annotations
from typing import List, Dict, Optional, Any, Callable, Optional, ClassVar
from datetime import datetime

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
import json


class TaskCreateInput(ToolInput):
    """Input for TaskCreate."""

    subject: str
    description: str
    activeForm: Optional[str] = None


class TaskUpdateInput(ToolInput):
    """Input for TaskUpdate."""

    taskId: str
    status: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None


class TaskListInput(ToolInput):
    """Input for TaskList."""

    pass


class TaskGetInput(ToolInput):
    """Input for TaskGet."""

    taskId: str


# In-memory task storage (for now)
_tasks: Dict[str, dict] = {}
_task_counter = 0


class TaskCreateTool(ToolDef):
    """Create a new task."""

    name: ClassVar[str] = "TaskCreate"
    description: ClassVar[str] = "Create a structured task to track work"
    input_schema: ClassVar[type] = TaskCreateInput

    async def execute(self, input: TaskCreateInput, ctx: ToolUseContext) -> ToolResult:
        """Create task."""
        global _task_counter
        _task_counter += 1
        task_id = str(_task_counter)

        task = {
            "id": task_id,
            "subject": input.subject,
            "description": input.description,
            "activeForm": input.activeForm or input.subject,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "owner": None,
        }
        _tasks[task_id] = task

        return ToolResult(
            content=f"Created task #{task_id}: {input.subject}",
            metadata={"taskId": task_id, "task": task},
        )


class TaskUpdateTool(ToolDef):
    """Update a task."""

    name: ClassVar[str] = "TaskUpdate"
    description: ClassVar[str] = "Update task status or details"
    input_schema: ClassVar[type] = TaskUpdateInput

    async def execute(self, input: TaskUpdateInput, ctx: ToolUseContext) -> ToolResult:
        """Update task."""
        if input.taskId not in _tasks:
            return ToolResult(
                content=f"Task not found: {input.taskId}",
                is_error=True,
            )

        task = _tasks[input.taskId]
        if input.status:
            task["status"] = input.status
        if input.subject:
            task["subject"] = input.subject
        if input.description:
            task["description"] = input.description
        task["updated_at"] = datetime.now().isoformat()

        return ToolResult(
            content=f"Updated task #{input.taskId}: {task['status']}",
            metadata={"taskId": input.taskId, "task": task},
        )


class TaskListTool(ToolDef):
    """List all tasks."""

    name: ClassVar[str] = "TaskList"
    description: ClassVar[str] = "List all tasks with their status"
    input_schema: ClassVar[type] = TaskListInput

    async def execute(self, input: TaskListInput, ctx: ToolUseContext) -> ToolResult:
        """List tasks."""
        if not _tasks:
            return ToolResult(content="No tasks found")

        lines = []
        for task_id, task in sorted(_tasks.items(), key=lambda x: int(x[0])):
            status_icon = {
                "pending": "○",
                "in_progress": "◐",
                "completed": "●",
            }.get(task["status"], "?")
            lines.append(f"{status_icon} #{task_id}: {task['subject']} [{task['status']}]")

        return ToolResult(
            content="\n".join(lines),
            metadata={"count": len(_tasks)},
        )


class TaskGetTool(ToolDef):
    """Get task details."""

    name: ClassVar[str] = "TaskGet"
    description: ClassVar[str] = "Get full details of a task"
    input_schema: ClassVar[type] = TaskGetInput

    async def execute(self, input: TaskGetInput, ctx: ToolUseContext) -> ToolResult:
        """Get task."""
        if input.taskId not in _tasks:
            return ToolResult(
                content=f"Task not found: {input.taskId}",
                is_error=True,
            )

        task = _tasks[input.taskId]
        return ToolResult(
            content=json.dumps(task, indent=2),
            metadata={"taskId": input.taskId},
        )
