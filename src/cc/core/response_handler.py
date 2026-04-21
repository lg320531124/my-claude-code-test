"""Response Handler - Handle API responses."""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List, AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..utils.log import get_logger

logger = get_logger(__name__)


class ResponseStatus(Enum):
    """Response status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    OVERLOADED = "overloaded"


class ResponseType(Enum):
    """Response types."""
    TEXT = "text"
    TOOL_USE = "tool_use"
    THINKING = "thinking"
    IMAGE = "image"
    ERROR = "error"


@dataclass
class ResponseBlock:
    """Response block."""
    type: ResponseType
    content: Any
    index: int = 0
    tool_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Dict[str, Any] = field(default_factory=dict)
    thinking_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIResponse:
    """API response."""
    id: str
    status: ResponseStatus
    blocks: List[ResponseBlock] = field(default_factory=list)
    stop_reason: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = ""
    duration: float = 0.0
    error: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class HandlerConfig:
    """Handler configuration."""
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 60.0
    stream: bool = True
    handle_rate_limit: bool = True


class ResponseHandler:
    """Handle API responses."""

    def __init__(self, config: Optional[HandlerConfig] = None):
        self.config = config or HandlerConfig()
        self._callbacks: Dict[str, Callable] = {}
        self._history: List[APIResponse] = []

    async def handle(
        self,
        raw_response: Dict[str, Any]
    ) -> APIResponse:
        """Handle raw response."""
        response_id = raw_response.get("id", "")
        status = ResponseStatus.SUCCESS

        # Parse content
        blocks = []
        content_list = raw_response.get("content", [])

        for i, item in enumerate(content_list):
            type_str = item.get("type", "text")

            try:
                block_type = ResponseType(type_str)
            except ValueError:
                block_type = ResponseType.TEXT

            block = ResponseBlock(
                type=block_type,
                content=item.get("text", "") if block_type == ResponseType.TEXT else item,
                index=i,
                tool_id=item.get("id") if block_type == ResponseType.TOOL_USE else None,
                tool_name=item.get("name") if block_type == ResponseType.TOOL_USE else None,
                tool_input=item.get("input", {}) if block_type == ResponseType.TOOL_USE else {},
            )

            blocks.append(block)

        # Parse usage
        usage = raw_response.get("usage", {})
        stop_reason = raw_response.get("stop_reason", "")
        model = raw_response.get("model", "")

        response = APIResponse(
            id=response_id,
            status=status,
            blocks=blocks,
            stop_reason=stop_reason,
            usage=usage,
            model=model,
            timestamp=datetime.now(),
        )

        # Add to history
        self._history.append(response)

        # Call callbacks
        await self._call_callbacks(response)

        return response

    async def handle_stream(
        self,
        stream: AsyncIterator[Dict[str, Any]]
    ) -> AsyncIterator[ResponseBlock]:
        """Handle streaming response."""
        buffer: Dict[str, Any] = {}
        current_block_index = 0

        for event in stream:
            event_type = event.get("type", "")

            if event_type == "content_block_start":
                current_block_index = event.get("index", 0)
                block_data = event.get("content_block", {})
                block_type = block_data.get("type", "text")

                buffer[current_block_index] = {
                    "type": block_type,
                    "content": "",
                    "tool_name": block_data.get("name") if block_type == "tool_use" else None,
                    "tool_id": block_data.get("id") if block_type == "tool_use" else None,
                    "tool_input": "",
                }

            elif event_type == "content_block_delta":
                index = event.get("index", current_block_index)
                delta = event.get("delta", {})
                delta_type = delta.get("type", "text_delta")

                if index in buffer:
                    if delta_type == "text_delta":
                        text = delta.get("text", "")
                        buffer[index]["content"] += text

                        # Yield partial
                        yield ResponseBlock(
                            type=ResponseType.TEXT,
                            content=text,
                            index=index,
                        )

                    elif delta_type == "input_json_delta":
                        partial_json = delta.get("partial_json", "")
                        buffer[index]["tool_input"] += partial_json

            elif event_type == "content_block_stop":
                index = event.get("index", current_block_index)

                if index in buffer:
                    block_data = buffer[index]

                    # Finalize
                    if block_data["type"] == "tool_use":
                        try:
                            tool_input = json.loads(block_data["tool_input"])
                        except json.JSONDecodeError:
                            tool_input = {}

                        yield ResponseBlock(
                            type=ResponseType.TOOL_USE,
                            content=None,
                            index=index,
                            tool_id=block_data["tool_id"],
                            tool_name=block_data["tool_name"],
                            tool_input=tool_input,
                        )

                    elif block_data["type"] == "text":
                        yield ResponseBlock(
                            type=ResponseType.TEXT,
                            content=block_data["content"],
                            index=index,
                        )

        # Clear buffer
        buffer.clear()

    async def handle_error(
        self,
        error: Dict[str, Any]
    ) -> APIResponse:
        """Handle error response."""
        error_type = error.get("type", "unknown_error")
        error_message = error.get("message", "Unknown error")

        status = ResponseStatus.ERROR

        if error_type == "rate_limit_error":
            status = ResponseStatus.RATE_LIMITED
        elif error_type == "overloaded_error":
            status = ResponseStatus.OVERLOADED

        response = APIResponse(
            id="",
            status=status,
            error=error_message,
            timestamp=datetime.now(),
        )

        self._history.append(response)
        return response

    async def _call_callbacks(
        self,
        response: APIResponse
    ) -> None:
        """Call registered callbacks."""
        for event_type, callback in self._callbacks.items():
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(response)
                else:
                    callback(response)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def register_callback(
        self,
        event_type: str,
        callback: Callable
    ) -> None:
        """Register callback."""
        self._callbacks[event_type] = callback

    def unregister_callback(
        self,
        event_type: str
    ) -> bool:
        """Unregister callback."""
        if event_type in self._callbacks:
            del self._callbacks[event_type]
            return True
        return False

    async def extract_text(
        self,
        response: APIResponse
    ) -> str:
        """Extract text from response."""
        text_parts = []

        for block in response.blocks:
            if block.type == ResponseType.TEXT and isinstance(block.content, str):
                text_parts.append(block.content)

        return "\n".join(text_parts)

    async def extract_tool_calls(
        self,
        response: APIResponse
    ) -> List[Dict[str, Any]]:
        """Extract tool calls from response."""
        tool_calls = []

        for block in response.blocks:
            if block.type == ResponseType.TOOL_USE:
                tool_calls.append({
                    "id": block.tool_id,
                    "name": block.tool_name,
                    "input": block.tool_input,
                })

        return tool_calls

    async def get_history(
        self,
        limit: int = 50
    ) -> List[APIResponse]:
        """Get response history."""
        return self._history[-limit:]

    async def clear_history(self) -> int:
        """Clear history."""
        count = len(self._history)
        self._history.clear()
        return count

    async def should_retry(
        self,
        response: APIResponse
    ) -> bool:
        """Check if should retry."""
        if response.status == ResponseStatus.RATE_LIMITED:
            return self.config.handle_rate_limit

        if response.status == ResponseStatus.OVERLOADED:
            return True

        return False

    async def get_retry_delay(
        self,
        response: APIResponse
    ) -> float:
        """Get retry delay."""
        if response.status == ResponseStatus.RATE_LIMITED:
            return self.config.retry_delay * 2

        return self.config.retry_delay


__all__ = [
    "ResponseStatus",
    "ResponseType",
    "ResponseBlock",
    "APIResponse",
    "HandlerConfig",
    "ResponseHandler",
]