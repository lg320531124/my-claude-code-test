"""Tests for enhanced API client."""

import pytest
import asyncio
from pathlib import Path
import json
import time

from cc.services.api.enhanced_client import (
    EnhancedAPIClient,
    APIError,
    APIErrorType,
    RetryConfig,
    StreamEvent,
    StreamingBuffer,
    ToolCallBuffer,
    create_client,
)


def test_api_error_type():
    """Test API error types."""
    error = APIError(
        type=APIErrorType.RATE_LIMIT,
        message="Rate limited",
        retry_after=30.0,
    )

    assert error.type == APIErrorType.RATE_LIMIT
    assert error.recoverable is True


def test_api_error_auth():
    """Test auth error is not recoverable."""
    error = APIError(
        type=APIErrorType.AUTH,
        message="Invalid API key",
    )

    assert error.recoverable is False


def test_retry_config():
    """Test retry configuration."""
    config = RetryConfig(
        max_retries=5,
        initial_delay=0.5,
        max_delay=30.0,
        multiplier=2.0,
    )

    assert config.max_retries == 5
    assert config.initial_delay == 0.5


def test_streaming_buffer():
    """Test streaming buffer."""
    buffer = StreamingBuffer(max_size=1000)

    buffer.add("Hello")
    buffer.add(" World")

    assert buffer.get_all() == "Hello World"
    assert buffer.total_size == 11


def test_streaming_buffer_truncate():
    """Test buffer truncation."""
    buffer = StreamingBuffer(max_size=50)

    buffer.add("A" * 60)  # Over max

    assert len(buffer.get_all()) <= 50


def test_streaming_buffer_clear():
    """Test buffer clear."""
    buffer = StreamingBuffer()
    buffer.add("Content")

    buffer.clear()

    assert buffer.get_all() == ""
    assert buffer.total_size == 0


def test_tool_call_buffer():
    """Test tool call buffer."""
    buffer = ToolCallBuffer()

    buffer.start_tool("tool-1", "Bash", 0)
    buffer.add_json("{\"command\": \"")
    buffer.add_json("ls\"}")

    tool = buffer.complete_tool()

    assert tool is not None
    assert tool["name"] == "Bash"
    assert tool["input"]["command"] == "ls"


def test_tool_call_buffer_invalid_json():
    """Test buffer with invalid JSON."""
    buffer = ToolCallBuffer()

    buffer.start_tool("tool-1", "Bash", 0)
    buffer.add_json("invalid json")
    tool = buffer.complete_tool()

    assert tool is not None
    assert "raw" in tool["input"]


def test_stream_event():
    """Test stream event."""
    event = StreamEvent(
        type="text_delta",
        data={"text": "Hello"},
    )

    assert event.type == "text_delta"
    assert event.data["text"] == "Hello"
    assert event.timestamp > 0


def test_enhanced_client_init():
    """Test client initialization."""
    client = EnhancedAPIClient(
        model="claude-sonnet-4-6",
        timeout=60.0,
    )

    assert client.model == "claude-sonnet-4-6"
    assert client.timeout == 60.0
    assert client.stats["input_tokens"] == 0


def test_enhanced_client_providers():
    """Test provider configs."""
    assert "anthropic" in EnhancedAPIClient.PROVIDERS
    assert "zhipu" in EnhancedAPIClient.PROVIDERS
    assert "deepseek" in EnhancedAPIClient.PROVIDERS


def test_enhanced_client_stats():
    """Test statistics."""
    client = EnhancedAPIClient()

    client.stats["input_tokens"] = 1000
    client.stats["output_tokens"] = 500
    client.stats["api_calls"] = 3

    stats = client.get_stats()

    assert stats["total_tokens"] == 1500
    assert stats["api_calls"] == 3


def test_enhanced_client_reset_stats():
    """Test stats reset."""
    client = EnhancedAPIClient()

    client.stats["input_tokens"] = 1000
    client.reset_stats()

    assert client.stats["input_tokens"] == 0


def test_enhanced_client_estimate_tokens():
    """Test token estimation."""
    client = EnhancedAPIClient()

    messages = [
        {"role": "user", "content": "Hello world"},
        {"role": "assistant", "content": [{"type": "text", "text": "Hi there"}]},
    ]

    tokens = client._estimate_tokens(messages)

    assert tokens > 0


def test_enhanced_client_calculate_delay():
    """Test delay calculation."""
    client = EnhancedAPIClient()

    delay0 = client._calculate_delay(0)
    delay1 = client._calculate_delay(1)
    delay2 = client._calculate_delay(2)

    assert delay0 < delay1 < delay2


def test_enhanced_client_parse_error():
    """Test error parsing."""
    client = EnhancedAPIClient()

    # Mock rate limit error
    import httpx
    response = httpx.Response(429, headers={"retry-after": "30"})
    error = httpx.HTTPStatusError("Rate limit", request=None, response=response)

    parsed = client._parse_http_error(error)

    assert parsed.type == APIErrorType.RATE_LIMIT
    assert parsed.retry_after == 30.0


def test_create_client():
    """Test client factory."""
    client = create_client(model="claude-sonnet-4-6")

    assert client.model == "claude-sonnet-4-6"


def test_create_client_with_provider():
    """Test client factory with provider."""
    client = create_client(provider="zhipu")

    assert "dashscope" in client.base_url


@pytest.mark.asyncio
async def test_enhanced_client_context():
    """Test async context."""
    client = EnhancedAPIClient()

    async with client:
        assert client._client is not None

    assert client._client is None


@pytest.mark.asyncio
async def test_enhanced_client_close():
    """Test close method."""
    client = EnhancedAPIClient()

    await client._init_client()
    assert client._client is not None

    await client.close()
    assert client._client is None


def test_enhanced_client_callbacks():
    """Test callback setting."""
    client = EnhancedAPIClient()

    def on_stream(event): pass
    def on_error(error): pass
    def on_retry(error, attempt, delay): pass

    client.set_callbacks(on_stream=on_stream, on_error=on_error, on_retry=on_retry)

    assert client._on_stream == on_stream
    assert client._on_error == on_error