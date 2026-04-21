"""Message Row Widget - Single message row."""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MessageStatus(Enum):
    """Message status."""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class MessageRowConfig:
    """Message row configuration."""
    show_role: bool = True
    show_time: bool = False
    show_status: bool = True
    max_width: int = 100
    indent_tool_calls: bool = True


@dataclass
class MessageRowData:
    """Message row data."""
    role: str
    content: str
    status: MessageStatus = MessageStatus.COMPLETE
    timestamp: datetime = None
    is_tool_result: bool = False
    tool_name: Optional[str] = None
    tool_id: Optional[str] = None


class MessageRowWidget:
    """Widget to display single message row."""
    
    def __init__(self, config: MessageRowConfig = None):
        self.config = config or MessageRowConfig()
        self._data: Optional[MessageRowData] = None
    
    def set_data(self, data: MessageRowData) -> None:
        """Set message data."""
        self._data = data
    
    def render(self) -> str:
        """Render message row."""
        if not self._data:
            return ""
        
        lines = []
        data = self._data
        
        # Header line
        header_parts = []
        
        if self.config.show_role:
            role_icon = self._get_role_icon(data.role)
            header_parts.append(f"{role_icon} {data.role}")
        
        if self.config.show_time and data.timestamp:
            header_parts.append(f"[{data.timestamp.strftime('%H:%M:%S')}]")
        
        if self.config.show_status:
            status_icon = self._get_status_icon(data.status)
            header_parts.append(status_icon)
        
        if data.is_tool_result and data.tool_name:
            header_parts.append(f"Tool: {data.tool_name}")
        
        if header_parts:
            lines.append(" ".join(header_parts))
        
        # Content
        content = data.content
        
        # Truncate if needed
        if len(content) > self.config.max_width:
            content = content[:self.config.max_width] + "..."
        
        # Indent if tool result
        if data.is_tool_result and self.config.indent_tool_calls:
            lines.append(f"  {content}")
        else:
            lines.append(content)
        
        return "\n".join(lines)
    
    def _get_role_icon(self, role: str) -> str:
        """Get icon for role."""
        icons = {
            "user": "👤",
            "assistant": "🤖",
            "system": "⚙️",
            "tool": "🔧",
        }
        return icons.get(role.lower(), "•")
    
    def _get_status_icon(self, status: MessageStatus) -> str:
        """Get icon for status."""
        icons = {
            MessageStatus.PENDING: "⏳",
            MessageStatus.STREAMING: "🔄",
            MessageStatus.COMPLETE: "✓",
            MessageStatus.ERROR: "✗",
        }
        return icons.get(status, "")
    
    def is_streaming(self) -> bool:
        """Check if streaming."""
        return self._data and self._data.status == MessageStatus.STREAMING
    
    def is_complete(self) -> bool:
        """Check if complete."""
        return self._data and self._data.status == MessageStatus.COMPLETE
    
    def get_role(self) -> str:
        """Get role."""
        return self._data.role if self._data else ""
    
    def get_content_preview(self, max_len: int = 50) -> str:
        """Get content preview."""
        if not self._data:
            return ""
        
        content = self._data.content
        if len(content) > max_len:
            return content[:max_len] + "..."
        return content


__all__ = [
    "MessageStatus",
    "MessageRowConfig",
    "MessageRowData",
    "MessageRowWidget",
]
