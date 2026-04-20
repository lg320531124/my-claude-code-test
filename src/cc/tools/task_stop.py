"""TaskStopTool - Stop background task.

Async tool for canceling running background tasks.
"""

from __future__ import annotations
import asyncio
from typing import ClassVar, Dict, Any, Optional, Callable

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext


class TaskStopInput(ToolInput):
    """Input for TaskStopTool."""

    task_id: str = Field(description="The task ID to stop")


class TaskStopOutput(BaseModel):
    """Output schema for TaskStopTool."""

    task_id: str
    stopped: bool
    message: str


class TaskStopTool(Tool):
    """Stop a background task."""

    name: str = "TaskStop"
    input_schema: type = TaskStopInput
    max_result_size_chars: float = 10_000
    strict: bool = True

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Stop the task."""
        input_data = TaskStopInput.model_validate(args)

        # In a full implementation, this would cancel actual background tasks
        # For now, return a placeholder
        output = TaskStopOutput(
            task_id=input_data.task_id,
            stopped=True,
            message="Task stopped - implement with actual task tracking",
        )

        return ToolResult(data=output)

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description."""
        task_id = input.get("task_id", "")
        if task_id:
            return f"Stop task {task_id}"
        return "Stop task"

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary."""
        if not input:
            return None
        return f"Stop: {input.get('task_id', '')}"

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description."""
        return "Stopping task"


def build_task_stop_tool() -> TaskStopTool:
    """Build TaskStopTool instance."""
    return TaskStopTool()


__all__ = ["TaskStopTool", "TaskStopInput", "TaskStopOutput", "build_task_stop_tool"]