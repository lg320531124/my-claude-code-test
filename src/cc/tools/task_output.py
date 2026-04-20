"""TaskOutputTool - Get task output.

Async tool for waiting on background task results.
"""

from __future__ import annotations
import asyncio
from typing import ClassVar, Dict, Any, Optional, Callable

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext


class TaskOutputInput(ToolInput):
    """Input for TaskOutputTool."""

    task_id: str = Field(description="The task ID to get output for")
    block: bool = Field(default=True, description="Whether to wait for task completion")
    timeout: Optional[int] = Field(default=30000, description="Timeout in milliseconds")


class TaskOutputOutput(BaseModel):
    """Output schema for TaskOutputTool."""

    task_id: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class TaskOutputTool(Tool):
    """Get output from a background task."""

    name: str = "TaskOutput"
    input_schema: type = TaskOutputInput
    max_result_size_chars: float = 100_000
    strict: bool = True

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Get task output."""
        input_data = TaskOutputInput.model_validate(args)

        # In a full implementation, this would check actual background tasks
        # For now, return a placeholder
        output = TaskOutputOutput(
            task_id=input_data.task_id,
            status="completed",
            output="Task output placeholder - implement with actual task tracking",
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
            return f"Get output for task {task_id}"
        return "Get task output"

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary."""
        if not input:
            return None
        return f"Get output: {input.get('task_id', '')}"

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description."""
        return "Getting task output"


def build_task_output_tool() -> TaskOutputTool:
    """Build TaskOutputTool instance."""
    return TaskOutputTool()


__all__ = ["TaskOutputTool", "TaskOutputInput", "TaskOutputOutput", "build_task_output_tool"]