"""Core Types - Serializable SDK message and session types.

Common types that can be serialized and sent over the wire.
"""

from __future__ import annotations
from typing import Any, Optional, Dict, List, Union
from dataclasses import dataclass, field
from enum import Enum


class MessageRole(Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class SDKTextBlock:
    """Text content block."""
    type: str = "text"
    text: str = ""


@dataclass
class SDKToolUseBlock:
    """Tool use content block."""
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SDKToolResultBlock:
    """Tool result content block."""
    type: str = "tool_result"
    tool_use_id: str = ""
    content: Union[str, List[Any]] = ""
    is_error: bool = False


SDKContentBlock = Union[SDKTextBlock, SDKToolUseBlock, SDKToolResultBlock]


@dataclass
class SDKUserMessage:
    """User message in SDK format."""
    role: str = "user"
    content: Union[str, List[SDKContentBlock]] = ""
    uuid: Optional[str] = None
    parent_uuid: Optional[str] = None
    timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"role": self.role, "content": self.content}
        if self.uuid:
            result["uuid"] = self.uuid
        if self.parent_uuid:
            result["parentUuid"] = self.parent_uuid
        if self.timestamp:
            result["timestamp"] = self.timestamp
        return result


@dataclass
class SDKAssistantMessage:
    """Assistant message in SDK format."""
    role: str = "assistant"
    content: List[SDKContentBlock] = field(default_factory=list)
    uuid: Optional[str] = None
    parent_uuid: Optional[str] = None
    timestamp: Optional[float] = None
    model: Optional[str] = None
    stop_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "role": self.role,
            "content": [c if isinstance(c, dict) else {"type": c.type, "text": c.text} for c in self.content]
        }
        if self.uuid:
            result["uuid"] = self.uuid
        if self.parent_uuid:
            result["parentUuid"] = self.parent_uuid
        if self.timestamp:
            result["timestamp"] = self.timestamp
        if self.model:
            result["model"] = self.model
        if self.stop_reason:
            result["stop_reason"] = self.stop_reason
        if self.usage:
            result["usage"] = self.usage
        return result


@dataclass
class SDKSystemMessage:
    """System message in SDK format."""
    role: str = "system"
    content: Union[str, List[Dict[str, Any]]] = ""
    uuid: Optional[str] = None
    parent_uuid: Optional[str] = None
    timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"role": self.role, "content": self.content}
        if self.uuid:
            result["uuid"] = self.uuid
        if self.parent_uuid:
            result["parentUuid"] = self.parent_uuid
        if self.timestamp:
            result["timestamp"] = self.timestamp
        return result


SDKMessage = Union[SDKUserMessage, SDKAssistantMessage, SDKSystemMessage]


@dataclass
class SDKResultMessage:
    """Result message from SDK query."""
    role: str = "assistant"
    content: List[SDKContentBlock] = field(default_factory=list)
    model: Optional[str] = None
    stop_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "role": self.role,
            "content": [
                {"type": c.type, "text": c.text} if hasattr(c, "text") else c
                for c in self.content
            ]
        }
        if self.model:
            result["model"] = self.model
        if self.stop_reason:
            result["stop_reason"] = self.stop_reason
        if self.usage:
            result["usage"] = self.usage
        if self.session_id:
            result["session_id"] = self.session_id
        return result


@dataclass
class SDKSessionInfo:
    """Session metadata."""
    session_id: str
    project: Optional[str] = None
    title: Optional[str] = None
    tag: Optional[str] = None
    model: Optional[str] = None
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    message_count: int = 0
    cost: float = 0.0
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sessionId": self.session_id,
            "project": self.project,
            "title": self.title,
            "tag": self.tag,
            "model": self.model,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "messageCount": self.message_count,
            "cost": self.cost,
            "tokensUsed": self.tokens_used,
        }