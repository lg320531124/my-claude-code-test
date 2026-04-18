"""Anthropic API client with streaming, retry, and error handling."""

import asyncio
import os
from typing import AsyncIterator, Any, Callable

import httpx
from anthropic import AsyncAnthropic, APIError, RateLimitError, APIConnectionError


class RetryConfig:
    """Retry configuration."""

    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    retry_multiplier: float = 2.0  # exponential backoff
    retry_on_errors: tuple = (RateLimitError, APIConnectionError)


class APIClient:
    """API client supporting Anthropic and compatible APIs with retry."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "claude-sonnet-4-6",
        retry_config: RetryConfig | None = None,
    ):
        # Get from environment if not provided
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
        self.model = model
        self.retry_config = retry_config or RetryConfig()

        # Usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_calls = 0

        # Initialize client
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the Anthropic client."""
        client_kwargs: dict[str, Any] = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = AsyncAnthropic(**client_kwargs)

    async def create_message(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 8192,
        stream: bool = True,
    ) -> AsyncIterator[dict]:
        """
        Create a message with streaming response and retry logic.
        """
        params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            params["system"] = system
        if tools:
            params["tools"] = tools

        # Retry loop
        for attempt in range(self.retry_config.max_retries):
            try:
                self.api_calls += 1

                if stream:
                    async with self.client.messages.stream(**params) as stream:
                        usage = None
                        for event in stream:
                            # Track usage
                            if hasattr(event, "message") and hasattr(event.message, "usage"):
                                usage = event.message.usage
                            yield self._process_stream_event(event)

                        # Record usage
                        if usage:
                            self.total_input_tokens += usage.input_tokens
                            self.total_output_tokens += usage.output_tokens or 0
                else:
                    response = await self.client.messages.create(**params)
                    self.total_input_tokens += response.usage.input_tokens
                    self.total_output_tokens += response.usage.output_tokens
                    yield {"type": "message", "message": response}

                # Success - break retry loop
                break

            except self.retry_config.retry_on_errors as e:
                if attempt < self.retry_config.max_retries - 1:
                    delay = self.retry_config.retry_delay * (
                        self.retry_config.retry_multiplier ** attempt
                    )
                    yield {
                        "type": "retry",
                        "attempt": attempt + 1,
                        "delay": delay,
                        "error": str(e),
                    }
                    await asyncio.sleep(delay)
                else:
                    yield {"type": "error", "error": str(e), "final": True}

            except APIError as e:
                yield {"type": "error", "error": str(e)}
                break

    def _process_stream_event(self, event: Any) -> dict:
        """Process a streaming event."""
        if hasattr(event, "type"):
            event_type = event.type

            if event_type == "content_block_delta":
                delta = event.delta
                if hasattr(delta, "type"):
                    if delta.type == "text_delta":
                        return {
                            "type": "text_delta",
                            "text": delta.text,
                        }
                    elif delta.type == "input_json_delta":
                        return {
                            "type": "input_json_delta",
                            "partial_json": getattr(delta, "partial_json", ""),
                        }

            elif event_type == "content_block_start":
                block = event.content_block
                if hasattr(block, "type"):
                    if block.type == "text":
                        return {
                            "type": "text_start",
                            "index": event.index,
                        }
                    elif block.type == "tool_use":
                        return {
                            "type": "tool_use_start",
                            "id": block.id,
                            "name": block.name,
                            "index": event.index,
                        }

            elif event_type == "content_block_stop":
                return {"type": "content_block_stop", "index": event.index}

            elif event_type == "message_stop":
                return {"type": "message_stop"}

            elif event_type == "message_start":
                return {"type": "message_start", "message": event.message}

            elif event_type == "ping":
                return {"type": "ping"}

        return {"type": "unknown", "event": str(event)}

    async def count_tokens(self, messages: list[dict]) -> int:
        """Count tokens in messages."""
        try:
            response = await self.client.messages.count_tokens(
                model=self.model,
                messages=messages,
            )
            return response.input_tokens
        except Exception:
            # Fallback estimation
            return self._estimate_tokens(messages)

    def _estimate_tokens(self, messages: list[dict]) -> int:
        """Estimate token count (rough: ~4 chars per token)."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            total += len(block.get("text", "")) // 4
                        elif block.get("type") == "tool_result":
                            total += len(block.get("content", "")) // 4
        return total

    def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "api_calls": self.api_calls,
        }


class CompatClient(APIClient):
    """Client for compatible APIs (智谱 Coding Plan, DeepSeek, etc.)."""

    # Known compatible API configurations
    COMPAT_PROVIDERS = {
        "zhipu": {
            "base_url": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
            "models": ["glm-4-plus", "glm-4", "glm-5", "glm-5-air"],
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "models": ["deepseek-chat", "deepseek-coder"],
        },
        "moonshot": {
            "base_url": "https://api.moonshot.cn/v1",
            "models": ["moonshot-v1-8k", "moonshot-v1-32k"],
        },
        "siliconflow": {
            "base_url": "https://api.siliconflow.cn/v1",
            "models": ["Qwen/Qwen2.5-72B-Instruct"],
        },
    }

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ):
        # Auto-detect provider from base_url or model
        if provider and provider in self.COMPAT_PROVIDERS:
            config = self.COMPAT_PROVIDERS[provider]
            base_url = base_url or config["base_url"]
            model = model or config["models"][0]

        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://coding.dashscope.aliyuncs.com/apps/anthropic",
            model=model or "glm-5",
        )


def get_client(
    model: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
) -> APIClient:
    """Get appropriate API client based on configuration."""
    effective_model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    effective_base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")

    # Check if using compatible API
    if provider:
        return CompatClient(model=effective_model, base_url=effective_base_url, provider=provider)

    if effective_base_url and "anthropic.com" not in effective_base_url:
        return CompatClient(model=effective_model, base_url=effective_base_url)

    return APIClient(model=effective_model)


def detect_provider_from_url(url: str) -> str | None:
    """Detect provider from URL."""
    if "dashscope" in url or "aliyuncs" in url:
        return "zhipu"
    if "deepseek" in url:
        return "deepseek"
    if "moonshot" in url:
        return "moonshot"
    if "siliconflow" in url:
        return "siliconflow"
    return None