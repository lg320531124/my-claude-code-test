"""REPLTool - REPL mode management.

Async tool for entering/controlling REPL mode.
"""

from __future__ import annotations
import asyncio
from typing import ClassVar, Dict, Any, Optional, Callable

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext


class REPLInput(ToolInput):
    """Input for REPLTool."""

    action: str = Field(description="Action: enter, exit, status")
    prompt: Optional[str] = Field(default=None, description="Initial prompt")


class REPLOutput(BaseModel):
    """Output schema for REPLTool."""

    action: str
    status: str
    message: str


class REPLTool(Tool):
    """Manage REPL mode."""

    name: str = "REPL"
    input_schema: type = REPLInput
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
        """Manage REPL."""
        input_data = REPLInput.model_validate(args)

        action = input_data.action

        if action == "enter":
            output = REPLOutput(
                action=action,
                status="active",
                message="Entered REPL mode",
            )
        elif action == "exit":
            output = REPLOutput(
                action=action,
                status="inactive",
                message="Exited REPL mode",
            )
        elif action == "status":
            output = REPLOutput(
                action=action,
                status="active",
                message="REPL mode status",
            )
        else:
            output = REPLOutput(
                action=action,
                status="error",
                message=f"Unknown action: {action}",
            )
            return ToolResult(data=output, is_error=True)

        return ToolResult(data=output)

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description."""
        action = input.get("action", "")
        return f"REPL: {action}"

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary."""
        if not input:
            return None
        return f"REPL {input.get('action', '')}"

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description."""
        return "REPL mode"


def build_repl_tool() -> REPLTool:
    """Build REPLTool instance."""
    return REPLTool()


__all__ = ["REPLTool", "REPLInput", "REPLOutput", "build_repl_tool"]