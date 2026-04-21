"""Synthetic Output Tool - Generate synthetic/placeholder output."""

from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..types.tool import ToolDef, ToolResult, ToolInput, ToolUseContext


class SyntheticType(Enum):
    """Types of synthetic output."""
    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"
    JSON = "json"


@dataclass
class SyntheticInput(ToolInput):
    """Synthetic output input schema."""
    type: str = "text"
    length: int = 100


class SyntheticOutputTool(ToolDef):
    """Tool to generate synthetic output for testing/demo."""
    
    name = "SyntheticOutput"
    input_schema = SyntheticInput
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any = None,
        parent_message: Any = None,
        on_progress: Optional[Any] = None,
    ) -> ToolResult:
        """Generate synthetic output."""
        type_str = args.get("type", "text")
        length = args.get("length", 100)
        
        # Generate based on type
        outputs = {
            "text": "This is synthetic text output for testing purposes.",
            "code": "def example():\n    return 'synthetic code'",
            "markdown": "# Synthetic Output\n\nThis is a **sample** markdown.",
            "json": '{"status": "synthetic", "data": []}',
        }
        
        output = outputs.get(type_str, outputs["text"])
        return ToolResult(data=output[:length])


# Tool registration
_synthetic_tool: Optional[SyntheticOutputTool] = None


def get_synthetic_tool() -> SyntheticOutputTool:
    """Get global synthetic output tool."""
    global _synthetic_tool
    if _synthetic_tool is None:
        _synthetic_tool = SyntheticOutputTool()
    return _synthetic_tool


__all__ = [
    "SyntheticType",
    "SyntheticInput",
    "SyntheticOutputTool",
    "get_synthetic_tool",
]
