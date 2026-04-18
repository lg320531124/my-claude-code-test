"""Message types for Claude Code Python."""

from datetime import datetime
from typing import Any, Literal

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
    input: dict[str, Any]


class ToolResultBlock(ContentBlock):
    """Tool result response block."""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


class ImageBlock(ContentBlock):
    """Image content block."""

    type: Literal["image"] = "image"
    source: dict[str, Any]  # {"type": "base64", "media_type": "image/png", "data": "...}


class Message(BaseModel):
    """Base message type."""

    role: str
    content: list[ContentBlock]
    timestamp: datetime = Field(default_factory=datetime.now)


class UserMessage(Message):
    """User message."""

    role: Literal["user"] = "user"


class AssistantMessage(Message):
    """Assistant message."""

    role: Literal["assistant"] = "assistant"
    stop_reason: str | None = None
    usage: dict[str, int] | None = None


class ToolResultMessage(Message):
    """Tool result message (sent back to model)."""

    role: Literal["user"] = "user"


class SystemMessage(BaseModel):
    """System message (for API)."""

    role: Literal["system"] = "system"
    content: str


def create_user_message(text: str, attachments: list[ContentBlock] | None = None) -> UserMessage:
    """Create a user message with optional attachments."""
    content: list[ContentBlock] = [TextBlock(text=text)]
    if attachments:
        content.extend(attachments)
    return UserMessage(content=content)


def create_assistant_message(
    blocks: list[ContentBlock],
    stop_reason: str | None = None,
    usage: dict[str, int] | None = None,
) -> AssistantMessage:
    """Create an assistant message."""
    return AssistantMessage(content=blocks, stop_reason=stop_reason, usage=usage)


def create_tool_result(tool_use_id: str, content: str, is_error: bool = False) -> ToolResultMessage:
    """Create a tool result message."""
    return ToolResultMessage(
        content=[ToolResultBlock(tool_use_id=tool_use_id, content=content, is_error=is_error)]
    )