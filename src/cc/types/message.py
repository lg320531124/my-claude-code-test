"""Message types for Claude Code Python."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Literal, Optional, Union, List

from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    """Base class for message content blocks."""

    type: str


class TextBlock(ContentBlock):
    """Text content block."""

    type: Literal["text"] = "text"
    text: str


class ToolUseBlock(ContentBlock):
    """Tool use request block."""

    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any] = Field(default_factory=dict)


class ToolResultBlock(ContentBlock):
    """Tool result response block."""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


class ImageBlock(ContentBlock):
    """Image content block."""

    type: Literal["image"] = "image"
    source: Dict[str, Any]  # {"type": "base64", "media_type": "image/png", "data": "...}


class ThinkingBlock(ContentBlock):
    """Thinking content block (extended thinking)."""

    type: Literal["thinking"] = "thinking"
    thinking: str


class RedactedThinkingBlock(ContentBlock):
    """Redacted thinking block."""

    type: Literal["redacted_thinking"] = "redacted_thinking"
    data: str


class Message(BaseModel):
    """Base message type."""

    role: str
    content: List[ContentBlock] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    uuid: Optional[str] = None


class UserMessage(Message):
    """User message."""

    role: Literal["user"] = "user"
    is_meta: bool = False
    tool_use_result: Optional[str] = None


class AssistantMessage(Message):
    """Assistant message."""

    role: Literal["assistant"] = "assistant"
    stop_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    is_api_error_message: bool = False
    api_error: Optional[str] = None


class ToolResultMessage(Message):
    """Tool result message (sent back to model)."""

    role: Literal["user"] = "user"


class SystemMessage(Message):
    """System message."""

    role: Literal["system"] = "system"
    subtype: Optional[str] = None  # e.g., "compact_boundary", "local_command"
    content: str = ""
    compact_metadata: Optional[Dict[str, Any]] = None


class ProgressMessage(Message):
    """Progress message for tool execution tracking."""

    role: Literal["progress"] = "progress"
    data: Optional[Dict[str, Any]] = None


class AttachmentMessage(Message):
    """Attachment message for additional context."""

    role: Literal["attachment"] = "attachment"
    attachment: Dict[str, Any] = Field(default_factory=dict)


class TombstoneMessage(Message):
    """Tombstone message for removing orphaned messages."""

    role: Literal["tombstone"] = "tombstone"
    message: Optional[Message] = None


class StreamEventMessage(Message):
    """Stream event message."""

    role: Literal["stream_event"] = "stream_event"
    event: Dict[str, Any] = Field(default_factory=dict)


class RequestStartEvent(Message):
    """Request start event."""

    role: Literal["request_start"] = "request_start"


class ToolUseSummaryMessage(Message):
    """Tool use summary message."""

    role: Literal["tool_use_summary"] = "tool_use_summary"
    summary: str = ""
    preceding_tool_use_ids: List[str] = Field(default_factory=list)


def create_user_message(text: str, attachments: Optional[List[ContentBlock]] = None) -> UserMessage:
    """Create a user message with optional attachments."""
    content: List[ContentBlock] = [TextBlock(text=text)]
    if attachments:
        content.extend(attachments)
    return UserMessage(content=content)


def create_assistant_message(
    blocks: List[ContentBlock],
    stop_reason: Optional[str] = None,
    usage: Optional[Dict[str, int]] = None,
) -> AssistantMessage:
    """Create an assistant message."""
    return AssistantMessage(content=blocks, stop_reason=stop_reason, usage=usage)


def create_tool_result(tool_use_id: str, content: str, is_error: bool = False) -> ToolResultMessage:
    """Create a tool result message."""
    return ToolResultMessage(
        content=[ToolResultBlock(tool_use_id=tool_use_id, content=content, is_error=is_error)]
    )
