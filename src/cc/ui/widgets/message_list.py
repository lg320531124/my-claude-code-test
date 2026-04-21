"""Message List Widget - List of chat messages."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .virtual_list import VirtualListWidget, VirtualListConfig


class MessageRole(Enum):
    """Message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class MessageItem:
    """Message item."""
    id: str
    role: MessageRole
    content: str
    timestamp: datetime = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageListConfig:
    """Message list configuration."""
    max_messages: int = 100
    show_timestamps: bool = True
    show_tool_calls: bool = True
    wrap_content: bool = True
    max_content_width: int = 80


class MessageListWidget:
    """Widget to display message list."""
    
    def __init__(self, config: MessageListConfig = None):
        self.config = config or MessageListConfig()
        self._messages: List[MessageItem] = []
        self._virtual_list = VirtualListWidget(
            VirtualListConfig(visible_count=20)
        )
    
    def add_message(self, message: MessageItem) -> None:
        """Add message."""
        self._messages.append(message)
        
        # Trim if over limit
        if len(self._messages) > self.config.max_messages:
            self._messages = self._messages[-self.config.max_messages:]
        
        # Update virtual list
        self._virtual_list.set_items(self._messages)
        self._virtual_list.set_renderer(self._render_message)
    
    def get_message(self, message_id: str) -> Optional[MessageItem]:
        """Get message by ID."""
        for msg in self._messages:
            if msg.id == message_id:
                return msg
        return None
    
    def get_last_message(self) -> Optional[MessageItem]:
        """Get last message."""
        if self._messages:
            return self._messages[-1]
        return None
    
    def get_by_role(self, role: MessageRole) -> List[MessageItem]:
        """Get messages by role."""
        return [m for m in self._messages if m.role == role]
    
    def _render_message(self, message: MessageItem, index: int) -> str:
        """Render single message."""
        role_icon = self._get_role_icon(message.role)
        
        lines = [f"{role_icon} [{message.role.value}]"]
        
        # Content
        content = message.content
        if self.config.wrap_content and len(content) > self.config.max_content_width:
            # Wrap content
            wrapped = []
            for i in range(0, len(content), self.config.max_content_width):
                wrapped.append(content[i:i + self.config.max_content_width])
            content = "\n".join(wrapped)
        
        lines.append(content)
        
        # Timestamp
        if self.config.show_timestamps and message.timestamp:
            lines.append(f"[{message.timestamp.strftime('%H:%M:%S')}]")
        
        # Tool calls
        if self.config.show_tool_calls and message.tool_calls:
            lines.append("Tool calls:")
            for tc in message.tool_calls:
                lines.append(f"  - {tc.get('name', 'unknown')}")
        
        return "\n".join(lines)
    
    def _get_role_icon(self, role: MessageRole) -> str:
        """Get icon for role."""
        icons = {
            MessageRole.USER: "👤",
            MessageRole.ASSISTANT: "🤖",
            MessageRole.SYSTEM: "⚙️",
            MessageRole.TOOL: "🔧",
        }
        return icons.get(role, "•")
    
    def render(self) -> str:
        """Render message list."""
        return self._virtual_list.render()
    
    def scroll_up(self) -> None:
        """Scroll up."""
        self._virtual_list.scroll_up()
    
    def scroll_down(self) -> None:
        """Scroll down."""
        self._virtual_list.scroll_down()
    
    def scroll_to_bottom(self) -> None:
        """Scroll to bottom."""
        self._virtual_list.scroll_to_index(len(self._messages) - 1)
    
    def clear(self) -> None:
        """Clear messages."""
        self._messages.clear()
        self._virtual_list.set_items([])
    
    def count(self) -> int:
        """Get message count."""
        return len(self._messages)


__all__ = [
    "MessageRole",
    "MessageItem",
    "MessageListConfig",
    "MessageListWidget",
]
