"""Task Output Tool - Get output from running/completed tasks."""

from __future__ import annotations
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..types.tool import ToolDef, ToolResult, ToolInput, ToolUseContext


class TaskStatus(Enum):
    """Task status types."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskOutputInput(ToolInput):
    """Task output input schema."""
    task_id: str = ""
    block: bool = True
    timeout: int = 30000


class TaskOutputTool(ToolDef):
    """Tool to get output from background tasks."""
    
    name = "TaskOutput"
    input_schema = TaskOutputInput
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any = None,
        parent_message: Any = None,
        on_progress: Optional[Any] = None,
    ) -> ToolResult:
        """Get task output."""
        task_id = args.get("task_id", "")
        args.get("block", True)
        args.get("timeout", 30000)
        
        if not task_id:
            return ToolResult(data="Error: task_id is required")
        
        # Mock implementation - return simulated output
        return ToolResult(data=f"Task {task_id} output (simulated)")


# Tool registration
_task_output_tool: Optional[TaskOutputTool] = None


def get_task_output_tool() -> TaskOutputTool:
    """Get global task output tool."""
    global _task_output_tool
    if _task_output_tool is None:
        _task_output_tool = TaskOutputTool()
    return _task_output_tool


__all__ = [
    "TaskStatus",
    "TaskOutputInput",
    "TaskOutputTool",
    "get_task_output_tool",
]
