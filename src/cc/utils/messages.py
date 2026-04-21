"""Messages Utilities - Message handling and processing."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

from ..services.token_estimation import estimate_tokens, estimate_messages_tokens


class MessageRole(Enum):
    """Message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ContentBlock:
    """Content block in a message."""
    type: str  # text, image, tool_use, tool_result
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Structured message."""
    role: MessageRole
    content: List[ContentBlock]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    message_id: str = ""

    def to_api_format(self) -> Dict[str, Any]:
        """Convert to API format."""
        content_list = []

        for block in self.content:
            if block.type == "text":
                content_list.append({
                    "type": "text",
                    "text": block.content,
                })
            elif block.type == "image":
                content_list.append({
                    "type": "image",
                    "source": block.metadata.get("source", {}),
                })
            elif block.type == "tool_use":
                content_list.append({
                    "type": "tool_use",
                    "name": block.metadata.get("name", ""),
                    "input": block.metadata.get("input", {}),
                    "id": block.metadata.get("id", ""),
                })
            elif block.type == "tool_result":
                content_list.append({
                    "type": "tool_result",
                    "tool_use_id": block.metadata.get("tool_use_id", ""),
                    "content": block.content,
                })

        return {
            "role": self.role.value,
            "content": content_list,
        }


def create_user_message(text: str, images: List[str] = None) -> Message:
    """Create user message."""
    content = [ContentBlock(type="text", content=text)]

    if images:
        for image_path in images:
            content.append(ContentBlock(
                type="image",
                metadata={"source": {"type": "file", "path": image_path}},
            ))

    return Message(
        role=MessageRole.USER,
        content=content,
    )


def create_assistant_message(
    text: str,
    tool_calls: List[Dict] = None,
    thinking: str = None
) -> Message:
    """Create assistant message."""
    content = []

    if thinking:
        content.append(ContentBlock(
            type="thinking",
            content=thinking,
            metadata={"budget": 10000},
        ))

    content.append(ContentBlock(type="text", content=text))

    if tool_calls:
        for call in tool_calls:
            content.append(ContentBlock(
                type="tool_use",
                content=call.get("input"),
                metadata={
                    "name": call.get("name"),
                    "id": call.get("id"),
                    "input": call.get("input"),
                },
            ))

    return Message(
        role=MessageRole.ASSISTANT,
        content=content,
    )


def create_tool_result_message(
    tool_use_id: str,
    result: Any,
    is_error: bool = False
) -> Message:
    """Create tool result message."""
    content = ContentBlock(
        type="tool_result",
        content=str(result),
        metadata={
            "tool_use_id": tool_use_id,
            "is_error": is_error,
        },
    )

    return Message(
        role=MessageRole.TOOL,
        content=[content],
    )


async def estimate_message_tokens(message: Message) -> int:
    """Estimate tokens for message."""
    total = 0

    for block in message.content:
        if block.type == "text":
            total += await estimate_tokens(block.content)
        elif block.type == "image":
            # Images have fixed cost based on size
            total += 1000  # Placeholder
        elif block.type == "thinking":
            total += await estimate_tokens(block.content)

    return total


async def format_messages_for_api(messages: List[Message]) -> List[Dict]:
    """Format messages for API call."""
    formatted = []

    for message in messages:
        formatted.append(message.to_api_format())

    return formatted


def extract_text_from_messages(messages: List[Message]) -> str:
    """Extract all text content from messages."""
    texts = []

    for message in messages:
        for block in message.content:
            if block.type == "text" and isinstance(block.content, str):
                texts.append(block.content)

    return "\n".join(texts)


def get_tool_calls_from_message(message: Message) -> List[Dict]:
    """Extract tool calls from assistant message."""
    tool_calls = []

    for block in message.content:
        if block.type == "tool_use":
            tool_calls.append({
                "name": block.metadata.get("name"),
                "id": block.metadata.get("id"),
                "input": block.metadata.get("input"),
            })

    return tool_calls


async def stream_message_updates(
    stream: AsyncIterator[Dict]
) -> AsyncIterator[Message]:
    """Stream message updates from API."""
    current_message = Message(
        role=MessageRole.ASSISTANT,
        content=[],
    )
    current_block = None

    for event in stream:
        event_type = event.get("type")

        if event_type == "content_block_start":
            block_type = event.get("content_block", {}).get("type")
            current_block = ContentBlock(type=block_type, content="")

        elif event_type == "content_block_delta":
            if current_block:
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    current_block.content += delta.get("text", "")

        elif event_type == "content_block_stop":
            if current_block:
                current_message.content.append(current_block)
                current_block = None

        elif event_type == "message_stop":
            yield current_message
            current_message = Message(
                role=MessageRole.ASSISTANT,
                content=[],
            )


__all__ = [
    "MessageRole",
    "ContentBlock",
    "Message",
    "create_user_message",
    "create_assistant_message",
    "create_tool_result_message",
    "estimate_message_tokens",
    "format_messages_for_api",
    "extract_text_from_messages",
    "get_tool_calls_from_message",
    "stream_message_updates",
]