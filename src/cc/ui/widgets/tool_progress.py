"""Tool Progress Widget - Tool execution progress."""

from __future__ import annotations
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class ToolProgressState(Enum):
    """Tool progress states."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolProgressInfo:
    """Tool progress info."""
    tool_name: str
    state: ToolProgressState = ToolProgressState.PENDING
    progress: float = 0.0  # 0-100
    message: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolProgressConfig:
    """Tool progress configuration."""
    show_duration: bool = True
    show_progress: bool = True
    show_message: bool = True
    max_tools: int = 5


class ToolProgressWidget:
    """Widget to display tool execution progress."""
    
    def __init__(self, config: ToolProgressConfig = None):
        self.config = config or ToolProgressConfig()
        self._tools: Dict[str, ToolProgressInfo] = {}
        self._history: List[ToolProgressInfo] = []
    
    def start_tool(self, tool_name: str, message: str = "") -> str:
        """Start tool execution."""
        import uuid
        tool_id = str(uuid.uuid4())[:8]
        
        info = ToolProgressInfo(
            tool_name=tool_name,
            state=ToolProgressState.RUNNING,
            message=message,
            start_time=time.time(),
        )
        
        self._tools[tool_id] = info
        return tool_id
    
    def update_progress(self, tool_id: str, progress: float, message: str = None) -> None:
        """Update tool progress."""
        if tool_id in self._tools:
            info = self._tools[tool_id]
            info.progress = progress
            if message:
                info.message = message
    
    def complete_tool(self, tool_id: str, success: bool = True) -> None:
        """Complete tool execution."""
        if tool_id in self._tools:
            info = self._tools[tool_id]
            info.end_time = time.time()
            info.duration = info.end_time - info.start_time
            info.state = ToolProgressState.SUCCESS if success else ToolProgressState.FAILED
            
            self._history.append(info)
            del self._tools[tool_id]
    
    def render(self) -> str:
        """Render tool progress."""
        lines = []
        
        # Current tools
        for tool_id, info in list(self._tools.items())[-self.config.max_tools:]:
            state_icon = self._get_state_icon(info.state)
            
            parts = [f"{state_icon} {info.tool_name}"]
            
            if self.config.show_progress and info.progress > 0:
                parts.append(f"[{info.progress:.0f}%]")
            
            if self.config.show_message and info.message:
                parts.append(f"- {info.message}")
            
            if self.config.show_duration and info.start_time > 0:
                elapsed = time.time() - info.start_time
                parts.append(f"({elapsed:.1f}s)")
            
            lines.append(" ".join(parts))
        
        return "\n".join(lines) if lines else "No tools running"
    
    def _get_state_icon(self, state: ToolProgressState) -> str:
        """Get icon for state."""
        icons = {
            ToolProgressState.PENDING: "⏳",
            ToolProgressState.RUNNING: "🔄",
            ToolProgressState.SUCCESS: "✓",
            ToolProgressState.FAILED: "✗",
            ToolProgressState.TIMEOUT: "⏱",
        }
        return icons.get(state, "•")
    
    def get_running_count(self) -> int:
        """Get number of running tools."""
        return len(self._tools)
    
    def get_history(self, limit: int = 10) -> List[ToolProgressInfo]:
        """Get tool history."""
        return self._history[-limit:]
    
    def clear_history(self) -> None:
        """Clear history."""
        self._history.clear()


# Global tool progress
_tool_progress: Optional[ToolProgressWidget] = None


def get_tool_progress() -> ToolProgressWidget:
    """Get global tool progress widget."""
    global _tool_progress
    if _tool_progress is None:
        _tool_progress = ToolProgressWidget()
    return _tool_progress


__all__ = [
    "ToolProgressState",
    "ToolProgressInfo",
    "ToolProgressConfig",
    "ToolProgressWidget",
    "get_tool_progress",
]
