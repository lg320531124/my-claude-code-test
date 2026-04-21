"""Streaming Utilities - SSE stream processing."""

from __future__ import annotations
import asyncio
import json
from typing import AsyncIterator, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum



class SSEEventType(Enum):
    """SSE event types."""
    MESSAGE_START = "message_start"
    CONTENT_BLOCK_START = "content_block_start"
    CONTENT_BLOCK_DELTA = "content_block_delta"
    CONTENT_BLOCK_STOP = "content_block_stop"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    ERROR = "error"
    PING = "ping"


@dataclass
class SSEEvent:
    """SSE event structure."""
    type: SSEEventType
    data: Dict[str, Any]
    raw: str = ""


@dataclass
class StreamState:
    """State for streaming message assembly."""
    message_id: str = ""
    current_block_index: int = 0
    current_block_type: str = ""
    text_buffer: str = ""
    tool_input_buffer: str = ""
    tool_name: str = ""
    tool_id: str = ""
    stop_reason: str = ""
    usage: Dict[str, int] = field(default_factory=dict)


class SSEParser:
    """Parse SSE streams from Anthropic API."""

    def __init__(self):
        self.state = StreamState()

    def parse_event(self, raw_event: str) -> Optional[SSEEvent]:
        """Parse a single SSE event."""
        if not raw_event.strip():
            return None

        # Parse SSE format: event: type\n data: json
        lines = raw_event.strip().split("\n")

        event_type = None
        data = {}

        for line in lines:
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                try:
                    data = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    data = {"raw": line[5:]}

        if not event_type:
            return None

        try:
            sse_type = SSEEventType(event_type)
        except ValueError:
            return SSEEvent(type=SSEEventType.PING, data={}, raw=raw_event)

        return SSEEvent(type=sse_type, data=data, raw=raw_event)

    def process_event(self, event: SSEEvent) -> Dict[str, Any]:
        """Process SSE event and return update."""
        result = {"type": event.type.value}

        if event.type == SSEEventType.MESSAGE_START:
            self.state.message_id = event.data.get("message", {}).get("id", "")
            self.state.usage = event.data.get("message", {}).get("usage", {})
            result["message_id"] = self.state.message_id
            result["usage"] = self.state.usage

        elif event.type == SSEEventType.CONTENT_BLOCK_START:
            self.state.current_block_index = event.data.get("index", 0)
            block = event.data.get("content_block", {})
            self.state.current_block_type = block.get("type", "text")

            if self.state.current_block_type == "text":
                self.state.text_buffer = ""
            elif self.state.current_block_type == "tool_use":
                self.state.tool_name = block.get("name", "")
                self.state.tool_id = block.get("id", "")
                self.state.tool_input_buffer = ""

            result["block_index"] = self.state.current_block_index
            result["block_type"] = self.state.current_block_type
            result["tool_name"] = self.state.tool_name

        elif event.type == SSEEventType.CONTENT_BLOCK_DELTA:
            delta = event.data.get("delta", {})
            delta_type = delta.get("type", "text_delta")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                self.state.text_buffer += text
                result["text"] = text
            elif delta_type == "input_json_delta":
                partial_json = delta.get("partial_json", "")
                self.state.tool_input_buffer += partial_json
                result["partial_json"] = partial_json

        elif event.type == SSEEventType.CONTENT_BLOCK_STOP:
            result["block_index"] = self.state.current_block_index

            if self.state.current_block_type == "tool_use":
                try:
                    tool_input = json.loads(self.state.tool_input_buffer)
                    result["tool_input"] = tool_input
                    result["tool_id"] = self.state.tool_id
                    result["tool_name"] = self.state.tool_name
                except json.JSONDecodeError:
                    result["tool_input"] = {}
                    result["error"] = "Invalid tool input JSON"

        elif event.type == SSEEventType.MESSAGE_DELTA:
            delta = event.data.get("delta", {})
            usage = event.data.get("usage", {})
            self.state.stop_reason = delta.get("stop_reason", "")
            result["stop_reason"] = self.state.stop_reason
            result["usage_delta"] = usage

        elif event.type == SSEEventType.MESSAGE_STOP:
            result["message_id"] = self.state.message_id
            result["complete"] = True

        elif event.type == SSEEventType.ERROR:
            error = event.data.get("error", {})
            result["error"] = error.get("message", "Unknown error")
            result["error_type"] = error.get("type", "")

        return result


async def stream_api_response(
    response: AsyncIterator[str]
) -> AsyncIterator[Dict[str, Any]]:
    """Stream API response and yield parsed events."""
    parser = SSEParser()

    for raw_event in response:
        event = parser.parse_event(raw_event)
        if event:
            yield parser.process_event(event)


async def collect_stream_text(
    stream: AsyncIterator[Dict[str, Any]]
) -> str:
    """Collect all text from stream."""
    text = ""

    for event in stream:
        if event.get("type") == "content_block_delta":
            if "text" in event:
                text += event["text"]

    return text


async def collect_stream_tool_calls(
    stream: AsyncIterator[Dict[str, Any]]
) -> list:
    """Collect all tool calls from stream."""
    tool_calls = []
    current_tool = None

    for event in stream:
        if event.get("type") == "content_block_start":
            if event.get("block_type") == "tool_use":
                current_tool = {
                    "id": event.get("tool_id", ""),
                    "name": event.get("tool_name", ""),
                    "input": "",
                }

        elif event.get("type") == "content_block_delta":
            if current_tool and "partial_json" in event:
                current_tool["input"] += event["partial_json"]

        elif event.get("type") == "content_block_stop":
            if current_tool:
                try:
                    current_tool["input"] = json.loads(current_tool["input"])
                except json.JSONDecodeError:
                    current_tool["input"] = {}
                tool_calls.append(current_tool)
                current_tool = None

    return tool_calls


class StreamBuffer:
    """Buffer for streaming content."""

    def __init__(self, max_size: int = 10000):
        self.text_buffer: str = ""
        self.max_size = max_size
        self._callbacks: list[Callable] = []

    def add_text(self, text: str) -> None:
        """Add text to buffer."""
        self.text_buffer += text

        # Notify callbacks
        for callback in self._callbacks:
            if asyncio.iscoroutinefunction(callback):
                asyncio.create_task(callback(text))
            else:
                callback(text)

    def get_text(self) -> str:
        """Get buffered text."""
        return self.text_buffer

    def clear(self) -> None:
        """Clear buffer."""
        self.text_buffer = ""

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to buffer updates."""
        self._callbacks.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from buffer updates."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)


class ToolCallBuffer:
    """Buffer for streaming tool calls."""

    def __init__(self):
        self._buffers: Dict[str, str] = {}  # tool_id -> input_json
        self._complete: Dict[str, dict] = {}  # tool_id -> complete tool call

    def start_tool(self, tool_id: str, tool_name: str) -> None:
        """Start a new tool call."""
        self._buffers[tool_id] = ""

    def add_partial(self, tool_id: str, partial: str) -> None:
        """Add partial JSON to tool call."""
        if tool_id in self._buffers:
            self._buffers[tool_id] += partial

    def complete_tool(self, tool_id: str) -> Optional[dict]:
        """Complete tool call."""
        if tool_id not in self._buffers:
            return None

        try:
            input_json = json.loads(self._buffers[tool_id])
            tool_call = {
                "id": tool_id,
                "input": input_json,
            }
            self._complete[tool_id] = tool_call
            return tool_call
        except json.JSONDecodeError:
            return None

    def get_complete_calls(self) -> list:
        """Get all complete tool calls."""
        return list(self._complete.values())

    def clear(self) -> None:
        """Clear buffers."""
        self._buffers.clear()
        self._complete.clear()


__all__ = [
    "SSEEventType",
    "SSEEvent",
    "StreamState",
    "SSEParser",
    "stream_api_response",
    "collect_stream_text",
    "collect_stream_tool_calls",
    "StreamBuffer",
    "ToolCallBuffer",
]