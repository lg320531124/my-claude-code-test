"""Enhanced API Client with advanced streaming and error handling."""

from __future__ import annotations
import asyncio
import json
import os
import time
from typing import AsyncIterator, Any, Callable, ClassVar, Optional
from dataclasses import dataclass, field
from enum import Enum

import httpx


class APIErrorType(Enum):
    """API error types."""
    RATE_LIMIT = "rate_limit"
    CONNECTION = "connection"
    AUTH = "auth"
    MODEL = "model"
    CONTEXT = "context"
    UNKNOWN = "unknown"


@dataclass
class APIError:
    """Structured API error."""
    type: APIErrorType
    message: str
    code: Optional[str] = None
    retry_after: Optional[float] = None
    recoverable: bool = True


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: float = 0.1  # Random jitter fraction
    retry_on: tuple = (APIErrorType.RATE_LIMIT, APIErrorType.CONNECTION)


@dataclass
class StreamEvent:
    """Stream event structure."""
    type: str
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class StreamingBuffer:
    """Buffer for streaming content."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.buffer: List[str] = []
        self.total_size = 0

    def add(self, text: str) -> None:
        """Add text to buffer."""
        if self.total_size + len(text) > self.max_size:
            # Trim oldest
            while self.buffer and self.total_size + len(text) > self.max_size:
                removed = self.buffer.pop(0)
                self.total_size -= len(removed)

        self.buffer.append(text)
        self.total_size += len(text)

    def get_all(self) -> str:
        """Get all buffered content."""
        return "".join(self.buffer)

    def clear(self) -> None:
        """Clear buffer."""
        self.buffer = []
        self.total_size = 0


class ToolCallBuffer:
    """Buffer for tool call parsing."""

    def __init__(self):
        self.current_tool: Optional[dict] = None
        self.json_buffer: str = ""
        self.completed_tools: List[dict] = []

    def start_tool(self, tool_id: str, name: str, index: int) -> None:
        """Start a new tool call."""
        self.current_tool = {
            "id": tool_id,
            "name": name,
            "index": index,
            "input": {},
        }
        self.json_buffer = ""

    def add_json(self, partial: str) -> None:
        """Add partial JSON."""
        if self.current_tool:
            self.json_buffer += partial

    def complete_tool(self) -> dict | None:
        """Complete current tool call."""
        if not self.current_tool:
            return None

        # Parse JSON
        try:
            self.current_tool["input"] = json.loads(self.json_buffer)
        except json.JSONDecodeError:
            self.current_tool["input"] = {"raw": self.json_buffer}

        completed = self.current_tool
        self.completed_tools.append(completed)
        self.current_tool = None
        self.json_buffer = ""

        return completed

    def get_completed(self) -> List[dict]:
        """Get all completed tool calls."""
        return self.completed_tools

    def clear(self) -> None:
        """Clear all buffers."""
        self.current_tool = None
        self.json_buffer = ""
        self.completed_tools = []


class EnhancedAPIClient:
    """Enhanced API client with advanced features."""

    PROVIDERS: ClassVar[dict] = {
        "anthropic": {
            "base_url": "https://api.anthropic.com",
            "models": ["claude-sonnet-4-6", "claude-opus-4-5", "claude-haiku-4-5"],
        },
        "zhipu": {
            "base_url": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
            "models": ["glm-4-plus", "glm-5", "glm-5-air"],
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "models": ["deepseek-chat", "deepseek-coder"],
        },
        "moonshot": {
            "base_url": "https://api.moonshot.cn/v1",
            "models": ["moonshot-v1-8k", "moonshot-v1-32k"],
        },
    }

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
        timeout: float = 120.0,
    ):
        self.model = model
        self.base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.retry_config = retry_config or RetryConfig()
        self.timeout = timeout

        # Stats
        self.stats = {
            "input_tokens": 0,
            "output_tokens": 0,
            "api_calls": 0,
            "retries": 0,
            "errors": 0,
            "total_time": 0.0,
        }

        # Callbacks
        self._on_stream: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        self._on_retry: Optional[Callable] = None

        # HTTP client
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context entry."""
        await self._init_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context exit."""
        await self._close_client()

    async def _init_client(self) -> None:
        """Initialize HTTP client."""
        if self._client is None:
            headers = {
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            if self.api_key:
                headers["x-api-key"] = self.api_key

            self._client = httpx.AsyncClient(
                base_url=self.base_url or "https://api.anthropic.com",
                headers=headers,
                timeout=self.timeout,
            )

    async def _close_client(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def create_message(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 8192,
        stream: bool = True,
    ) -> AsyncIterator[StreamEvent]:
        """Create message with advanced streaming."""
        await self._init_client()

        # Build request
        request_body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            request_body["system"] = system
        if tools:
            request_body["tools"] = tools

        # Retry loop
        for attempt in range(self.retry_config.max_retries + 1):
            start_time = time.time()

            try:
                self.stats["api_calls"] += 1

                if stream:
                    # Streaming request
                    async for event in self._stream_request(request_body):
                        yield event
                else:
                    # Non-streaming request
                    response = await self._single_request(request_body)
                    yield StreamEvent(type="message", data=response)

                # Success
                duration = time.time() - start_time
                self.stats["total_time"] += duration
                break

            except httpx.HTTPStatusError as e:
                error = self._parse_http_error(e)

                if error.recoverable and attempt < self.retry_config.max_retries:
                    self.stats["retries"] += 1

                    delay = self._calculate_delay(attempt, error.retry_after)

                    if self._on_retry:
                        self._on_retry(error, attempt, delay)

                    yield StreamEvent(
                        type="retry",
                        data={"attempt": attempt + 1, "delay": delay, "error": error.message},
                    )

                    await asyncio.sleep(delay)
                else:
                    self.stats["errors"] += 1
                    if self._on_error:
                        self._on_error(error)

                    yield StreamEvent(type="error", data={"error": error.message, "type": error.type.value})
                    break

            except httpx.RequestError as e:
                # Network error
                error = APIError(
                    type=APIErrorType.CONNECTION,
                    message=str(e),
                    recoverable=True,
                )

                if attempt < self.retry_config.max_retries:
                    self.stats["retries"] += 1
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    self.stats["errors"] += 1
                    yield StreamEvent(type="error", data={"error": error.message})
                    break

            except Exception as e:
                self.stats["errors"] += 1
                yield StreamEvent(type="error", data={"error": str(e)})
                break

    async def _stream_request(self, body: dict) -> AsyncIterator[StreamEvent]:
        """Execute streaming request."""
        buffer = StreamingBuffer()
        tool_buffer = ToolCallBuffer()

        async with self._client.stream(
            "POST",
            "/v1/messages",
            json=body,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line:
                    continue

                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = data.get("type", "")

                    # Process event
                    if event_type == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            buffer.add(text)

                            yield StreamEvent(
                                type="text_delta",
                                data={"text": text, "total": buffer.get_all()},
                            )

                        elif delta.get("type") == "input_json_delta":
                            tool_buffer.add_json(delta.get("partial_json", ""))

                    elif event_type == "content_block_start":
                        block = data.get("content_block", {})
                        if block.get("type") == "tool_use":
                            tool_buffer.start_tool(
                                block.get("id", ""),
                                block.get("name", ""),
                                data.get("index", 0),
                            )
                            yield StreamEvent(
                                type="tool_use_start",
                                data={"id": block.get("id"), "name": block.get("name")},
                            )

                    elif event_type == "content_block_stop":
                        tool = tool_buffer.complete_tool()
                        if tool:
                            yield StreamEvent(
                                type="tool_use_complete",
                                data=tool,
                            )

                    elif event_type == "message_delta":
                        # Usage update
                        usage = data.get("usage", {})
                        if usage:
                            self.stats["output_tokens"] = usage.get("output_tokens", 0)

                    elif event_type == "message_start":
                        message = data.get("message", {})
                        usage = message.get("usage", {})
                        if usage:
                            self.stats["input_tokens"] = usage.get("input_tokens", 0)

                        yield StreamEvent(type="message_start", data={"message": message})

                    elif event_type == "message_stop":
                        yield StreamEvent(
                            type="message_complete",
                            data={"content": buffer.get_all(), "tools": tool_buffer.get_completed()},
                        )

                    elif event_type == "ping":
                        yield StreamEvent(type="ping")

    async def _single_request(self, body: dict) -> dict:
        """Execute non-streaming request."""
        response = await self._client.post("/v1/messages", json=body)
        response.raise_for_status()

        data = response.json()

        # Update stats
        usage = data.get("usage", {})
        self.stats["input_tokens"] = usage.get("input_tokens", 0)
        self.stats["output_tokens"] = usage.get("output_tokens", 0)

        return data

    def _parse_http_error(self, error: httpx.HTTPStatusError) -> APIError:
        """Parse HTTP error."""
        status = error.response.status_code

        try:
            body = error.response.json()
            message = body.get("error", {}).get("message", str(error))
        except json.JSONDecodeError:
            message = str(error)

        if status == 429:
            # Rate limit
            retry_after = error.response.headers.get("retry-after")
            return APIError(
                type=APIErrorType.RATE_LIMIT,
                message=message,
                retry_after=float(retry_after) if retry_after else None,
                recoverable=True,
            )
        elif status == 401:
            return APIError(
                type=APIErrorType.AUTH,
                message=message,
                recoverable=False,
            )
        elif status == 404:
            return APIError(
                type=APIErrorType.MODEL,
                message=message,
                recoverable=False,
            )
        elif status >= 500:
            return APIError(
                type=APIErrorType.CONNECTION,
                message=message,
                recoverable=True,
            )
        else:
            return APIError(
                type=APIErrorType.UNKNOWN,
                message=message,
                recoverable=False,
            )

    def _calculate_delay(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """Calculate retry delay."""
        if retry_after:
            return retry_after

        delay = self.retry_config.initial_delay * (self.retry_config.multiplier ** attempt)
        delay = min(delay, self.retry_config.max_delay)

        # Add jitter
        jitter = delay * self.retry_config.jitter
        delay += (jitter * (2 * (time.time() % 1) - 1))  # Random between -jitter and +jitter

        return delay

    def set_callbacks(
        self,
        on_stream: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_retry: Optional[Callable] = None,
    ) -> None:
        """Set event callbacks."""
        self._on_stream = on_stream
        self._on_error = on_error
        self._on_retry = on_retry

    async def count_tokens(self, messages: List[dict]) -> int:
        """Count tokens using API or estimation."""
        # Try API first
        try:
            await self._init_client()
            response = await self._client.post(
                "/v1/messages/count_tokens",
                json={"model": self.model, "messages": messages},
            )
            data = response.json()
            return data.get("input_tokens", 0)
        except Exception:
            return self._estimate_tokens(messages)

    def _estimate_tokens(self, messages: List[dict]) -> int:
        """Estimate token count."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text", "") or block.get("content", "")
                        total += len(text) // 4
        return total

    def get_stats(self) -> dict:
        """Get usage statistics."""
        return {
            **self.stats,
            "total_tokens": self.stats["input_tokens"] + self.stats["output_tokens"],
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "input_tokens": 0,
            "output_tokens": 0,
            "api_calls": 0,
            "retries": 0,
            "errors": 0,
            "total_time": 0.0,
        }

    async def close(self) -> None:
        """Close client."""
        await self._close_client()


def create_client(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    **kwargs,
) -> EnhancedAPIClient:
    """Create API client."""
    effective_model = model or os.environ.get("CC_MODEL", "claude-sonnet-4-6")

    if provider and provider in EnhancedAPIClient.PROVIDERS:
        config = EnhancedAPIClient.PROVIDERS[provider]
        return EnhancedAPIClient(
            model=effective_model,
            base_url=config["base_url"],
            **kwargs,
        )

    return EnhancedAPIClient(model=effective_model, **kwargs)
