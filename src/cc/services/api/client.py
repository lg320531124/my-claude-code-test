"""Anthropic API client with streaming and compatible API support."""

import os
from typing import AsyncIterator, Any

import httpx
from anthropic import AsyncAnthropic


class APIClient:
    """API client supporting Anthropic and compatible APIs."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "claude-sonnet-4-6",
    ):
        # Get from environment if not provided
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
        self.model = model

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
        Create a message with streaming response.

        Yields content blocks as they arrive.
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

        if stream:
            async with self.client.messages.stream(**params) as stream:
                for event in stream:
                    yield self._process_stream_event(event)
        else:
            response = await self.client.messages.create(**params)
            yield {"type": "message", "message": response}

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

            elif event_type == "message_stop":
                return {"type": "message_stop"}

            elif event_type == "message_start":
                return {"type": "message_start", "message": event.message}

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
        """Estimate token count (rough)."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                # Rough: 1 token ~ 4 chars
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            total += len(block.get("text", "")) // 4
        return total


class CompatClient(APIClient):
    """Client for compatible APIs (智谱 Coding Plan, etc.)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://coding.dashscope.aliyuncs.com/apps/anthropic",
        model: str = "glm-5",  # 智谱 model
    ):
        super().__init__(api_key=api_key, base_url=base_url, model=model)


def get_client(model: str | None = None, base_url: str | None = None) -> APIClient:
    """Get appropriate API client."""
    effective_model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    effective_base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")

    # Check if using compatible API
    if effective_base_url and "anthropic.com" not in effective_base_url:
        return CompatClient(model=effective_model, base_url=effective_base_url)

    return APIClient(model=effective_model)