"""API Streaming - SSE stream response parsing."""

from __future__ import annotations
import asyncio
import json
from typing import AsyncIterator, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class StreamEventType(Enum):
    """Stream event types."""
    MESSAGE_START = "message_start"
    CONTENT_BLOCK_START = "content_block_start"
    CONTENT_BLOCK_DELTA = "content_block_delta"
    CONTENT_BLOCK_STOP = "content_block_stop"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    PING = "ping"
    ERROR = "error"


@dataclass
class StreamEvent:
    """Parsed stream event."""
    type: StreamEventType
    data: Dict[str, Any] = field(default_factory=dict)
    index: int = 0
    raw_line: str = ""


@dataclass
class StreamingMessage:
    """Accumulated streaming message."""
    role: str = "assistant"
    content_blocks: list = field(default_factory=list)
    current_block: Optional[Dict[str, Any]] = None
    message_id: str = ""
    model: str = ""
    stop_reason: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)


class SSEParser:
    """Parser for Server-Sent Events."""

    def __init__(self):
        self._buffer = ""

    async def parse_stream(
        self,
        stream: AsyncIterator[bytes],
    ) -> AsyncIterator[StreamEvent]:
        """Parse SSE stream."""
        async for chunk in stream:
            self._buffer += chunk.decode("utf-8", errors="replace")

            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                line = line.rstrip("\r")

                if not line:
                    continue

                if line.startswith(":"):
                    # Comment line, ignore
                    continue

                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        yield StreamEvent(type=StreamEventType.MESSAGE_STOP)
                        continue

                    try:
                        data = json.loads(data_str)
                        event = self._parse_event(data)
                        if event:
                            yield event
                    except json.JSONDecodeError:
                        # Invalid JSON, skip
                        continue

    def _parse_event(self, data: Dict[str, Any]) -> Optional[StreamEvent]:
        """Parse event data."""
        event_type = data.get("type", "")

        if event_type == "message_start":
            return StreamEvent(
                type=StreamEventType.MESSAGE_START,
                data=data.get("message", {}),
            )

        elif event_type == "content_block_start":
            return StreamEvent(
                type=StreamEventType.CONTENT_BLOCK_START,
                data=data.get("content_block", {}),
                index=data.get("index", 0),
            )

        elif event_type == "content_block_delta":
            return StreamEvent(
                type=StreamEventType.CONTENT_BLOCK_DELTA,
                data=data.get("delta", {}),
                index=data.get("index", 0),
            )

        elif event_type == "content_block_stop":
            return StreamEvent(
                type=StreamEventType.CONTENT_BLOCK_STOP,
                index=data.get("index", 0),
            )

        elif event_type == "message_delta":
            return StreamEvent(
                type=StreamEventType.MESSAGE_DELTA,
                data=data.get("delta", {}),
            )

        elif event_type == "message_stop":
            return StreamEvent(type=StreamEventType.MESSAGE_STOP)

        elif event_type == "ping":
            return StreamEvent(type=StreamEventType.PING)

        elif event_type == "error":
            return StreamEvent(
                type=StreamEventType.ERROR,
                data=data.get("error", {}),
            )

        return None


class MessageAccumulator:
    """Accumulate streaming message from events."""

    def __init__(self):
        self._message = StreamingMessage()

    def process_event(self, event: StreamEvent) -> Optional[StreamingMessage]:
        """Process event and return completed message."""
        if event.type == StreamEventType.MESSAGE_START:
            msg_data = event.data
            self._message = StreamingMessage(
                role=msg_data.get("role", "assistant"),
                message_id=msg_data.get("id", ""),
                model=msg_data.get("model", ""),
                usage=msg_data.get("usage", {}),
            )

        elif event.type == StreamEventType.CONTENT_BLOCK_START:
            block = event.data
            self._message.current_block = block
            self._message.current_block["index"] = event.index

        elif event.type == StreamEventType.CONTENT_BLOCK_DELTA:
            if self._message.current_block:
                delta = event.data
                delta_type = delta.get("type", "")

                if delta_type == "text_delta":
                    text = delta.get("text", "")
                    current_text = self._message.current_block.get("text", "")
                    self._message.current_block["text"] = current_text + text

                elif delta_type == "input_json_delta":
                    partial_json = delta.get("partial_json", "")
                    current_json = self._message.current_block.get("partial_json", "")
                    self._message.current_block["partial_json"] = current_json + partial_json

                elif delta_type == "thinking_delta":
                    thinking = delta.get("thinking", "")
                    current_thinking = self._message.current_block.get("thinking", "")
                    self._message.current_block["thinking"] = current_thinking + thinking

        elif event.type == StreamEventType.CONTENT_BLOCK_STOP:
            if self._message.current_block:
                # Try to parse accumulated JSON for tool_use blocks
                if self._message.current_block.get("type") == "tool_use":
                    partial_json = self._message.current_block.get("partial_json", "")
                    if partial_json:
                        try:
                            self._message.current_block["input"] = json.loads(partial_json)
                        except json.JSONDecodeError:
                            self._message.current_block["input"] = {}

                self._message.content_blocks.append(self._message.current_block)
                self._message.current_block = None

        elif event.type == StreamEventType.MESSAGE_DELTA:
            delta = event.data
            self._message.stop_reason = delta.get("stop_reason")
            if "usage" in delta:
                self._message.usage["output_tokens"] = delta["usage"].get("output_tokens", 0)

        elif event.type == StreamEventType.MESSAGE_STOP:
            return self._message

        return None

    def get_partial_text(self) -> str:
        """Get current accumulated text."""
        text_parts = []
        for block in self._message.content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return "".join(text_parts)


class StreamingResponseHandler:
    """Handle streaming API responses."""

    def __init__(self):
        self._parser = SSEParser()
        self._accumulator = MessageAccumulator()
        self._callbacks: Dict[StreamEventType, Callable] = {}

    def on_event(self, event_type: StreamEventType, callback: Callable) -> None:
        """Register callback for event type."""
        self._callbacks[event_type] = callback

    async def handle_stream(
        self,
        stream: AsyncIterator[bytes],
        yield_partial: bool = False,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Handle stream and yield updates."""
        async for event in self._parser.parse_stream(stream):
            # Call registered callbacks
            if event.type in self._callbacks:
                await self._call_callback(event.type, event)

            # Process event
            completed = self._accumulator.process_event(event)

            # Yield partial updates if requested
            if yield_partial:
                yield {
                    "type": event.type.value,
                    "partial_text": self._accumulator.get_partial_text(),
                    "event_data": event.data,
                }

            # Yield completed message
            if completed:
                yield {
                    "type": "message_complete",
                    "message": self._to_api_format(completed),
                }

    async def _call_callback(self, event_type: StreamEventType, event: StreamEvent) -> None:
        """Call event callback."""
        callback = self._callbacks.get(event_type)
        if callback:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)

    def _to_api_format(self, msg: StreamingMessage) -> Dict[str, Any]:
        """Convert message to API format."""
        content = []

        for block in msg.content_blocks:
            block_type = block.get("type", "text")

            if block_type == "text":
                content.append({
                    "type": "text",
                    "text": block.get("text", ""),
                })

            elif block_type == "tool_use":
                content.append({
                    "type": "tool_use",
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                })

            elif block_type == "thinking":
                content.append({
                    "type": "thinking",
                    "thinking": block.get("thinking", ""),
                })

        return {
            "id": msg.message_id,
            "type": "message",
            "role": msg.role,
            "content": content,
            "model": msg.model,
            "stop_reason": msg.stop_reason,
            "usage": msg.usage,
        }


__all__ = [
    "StreamEventType",
    "StreamEvent",
    "StreamingMessage",
    "SSEParser",
    "MessageAccumulator",
    "StreamingResponseHandler",
]