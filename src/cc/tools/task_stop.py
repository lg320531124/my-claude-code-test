"""Task Stop Tool - Cancel running tasks."""

from __future__ import annotations
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..types.tool import ToolDef, ToolResult, ToolInput, ToolUseContext


@dataclass
class TaskStopInput(ToolInput):
    """Task stop input schema."""
    task_id: str = ""
    force: bool = False


class TaskStopTool(ToolDef):
    """Tool to stop/cancel background tasks."""
    
    name = "TaskStop"
    input_schema = TaskStopInput
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any = None,
        parent_message: Any = None,
        on_progress: Optional[Any] = None,
    ) -> ToolResult:
        """Stop task."""
        task_id = args.get("task_id", "")
        force = args.get("force", False)
        
        if not task_id:
            return ToolResult(data="Error: task_id is required")
        
        # Mock implementation
        return ToolResult(data=f"Task {task_id} cancelled (simulated)")


# Tool registration
_task_stop_tool: Optional[TaskStopTool] = None


def get_task_stop_tool() -> TaskStopTool:
    """Get global task stop tool."""
    global _task_stop_tool
    if _task_stop_tool is None:
        _task_stop_tool = TaskStopTool()
    return _task_stop_tool


__all__ = [
    "TaskStopInput",
    "TaskStopTool",
    "get_task_stop_tool",
]
