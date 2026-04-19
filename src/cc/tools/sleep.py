"""Sleep Tool - Async delay functionality."""

from __future__ import annotations
import asyncio
from typing import Any, Optional
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolResult, ToolUseContext


class SleepInput(BaseModel):
    """Input for SleepTool."""
    seconds: float = Field(description="Number of seconds to sleep", ge=0, le=3600)
    reason: Optional[str] = Field(default=None, description="Reason for the delay")


class SleepTool(ToolDef):
    """Tool for async delays."""

    name = "Sleep"
    description = "Pause execution for specified duration"
    input_schema = SleepInput

    async def execute(self, input: SleepInput, ctx: Optional[ToolUseContext] = None) -> ToolResult:
        """Execute sleep."""
        seconds = input.seconds
        reason = input.reason or "Delay"

        await asyncio.sleep(seconds)

        return ToolResult(
            content=f"Sleep completed: {seconds}s ({reason})",
            metadata={
                "seconds": seconds,
                "reason": reason,
            }
        )


__all__ = ["SleepTool", "SleepInput"]