"""Tests for response handler."""

import pytest
from src.cc.core.response_handler import (
    ResponseHandler,
    ResponseStatus,
    ResponseType,
    ResponseBlock,
    APIResponse,
    HandlerConfig,
)


@pytest.mark.asyncio
async def test_response_handler_init():
    """Test response handler initialization."""
    handler = ResponseHandler()
    assert handler.config is not None
    assert handler._callbacks == {}


@pytest.mark.asyncio
async def test_handle_success():
    """Test handling success response."""
    handler = ResponseHandler()

    raw_response = {
        "id": "msg_123",
        "content": [
            {"type": "text", "text": "Hello"}
        ],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "model": "claude-sonnet-4-6",
    }

    response = await handler.handle(raw_response)

    assert response.status == ResponseStatus.SUCCESS
    assert len(response.blocks) == 1
    assert response.blocks[0].type == ResponseType.TEXT


@pytest.mark.asyncio
async def test_handle_tool_use():
    """Test handling tool use response."""
    handler = ResponseHandler()

    raw_response = {
        "id": "msg_123",
        "content": [
            {"type": "tool_use", "id": "tool_1", "name": "read", "input": {"path": "/tmp"}}
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }

    response = await handler.handle(raw_response)

    assert len(response.blocks) == 1
    assert response.blocks[0].type == ResponseType.TOOL_USE
    assert response.blocks[0].tool_name == "read"


@pytest.mark.asyncio
async def test_handle_multiple_blocks():
    """Test handling multiple blocks."""
    handler = ResponseHandler()

    raw_response = {
        "id": "msg_123",
        "content": [
            {"type": "text", "text": "Hello"},
            {"type": "tool_use", "id": "tool_1", "name": "bash", "input": {"cmd": "ls"}},
            {"type": "text", "text": "Goodbye"},
        ],
        "stop_reason": "end_turn",
    }

    response = await handler.handle(raw_response)

    assert len(response.blocks) == 3


@pytest.mark.asyncio
async def test_handle_error():
    """Test handling error response."""
    handler = ResponseHandler()

    error = {
        "type": "api_error",
        "message": "Request failed",
    }

    response = await handler.handle_error(error)

    assert response.status == ResponseStatus.ERROR
    assert response.error == "Request failed"


@pytest.mark.asyncio
async def test_handle_rate_limit():
    """Test handling rate limit error."""
    handler = ResponseHandler()

    error = {
        "type": "rate_limit_error",
        "message": "Rate limited",
    }

    response = await handler.handle_error(error)

    assert response.status == ResponseStatus.RATE_LIMITED


@pytest.mark.asyncio
async def test_handle_overloaded():
    """Test handling overloaded error."""
    handler = ResponseHandler()

    error = {
        "type": "overloaded_error",
        "message": "Server overloaded",
    }

    response = await handler.handle_error(error)

    assert response.status == ResponseStatus.OVERLOADED


@pytest.mark.asyncio
async def test_extract_text():
    """Test extracting text."""
    handler = ResponseHandler()

    response = APIResponse(
        id="msg_1",
        status=ResponseStatus.SUCCESS,
        blocks=[
            ResponseBlock(type=ResponseType.TEXT, content="Hello"),
            ResponseBlock(type=ResponseType.TEXT, content="World"),
        ],
    )

    text = await handler.extract_text(response)

    assert text == "Hello\nWorld"


@pytest.mark.asyncio
async def test_extract_tool_calls():
    """Test extracting tool calls."""
    handler = ResponseHandler()

    response = APIResponse(
        id="msg_1",
        status=ResponseStatus.SUCCESS,
        blocks=[
            ResponseBlock(
                type=ResponseType.TOOL_USE,
                content=None,
                tool_id="tool_1",
                tool_name="read",
                tool_input={"path": "/tmp"},
            ),
        ],
    )

    tool_calls = await handler.extract_tool_calls(response)

    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "read"


@pytest.mark.asyncio
async def test_register_callback():
    """Test registering callback."""
    handler = ResponseHandler()

    def callback(response):
        pass

    handler.register_callback("test", callback)

    assert "test" in handler._callbacks


@pytest.mark.asyncio
async def test_unregister_callback():
    """Test unregistering callback."""
    handler = ResponseHandler()

    handler.register_callback("test", lambda r: None)
    result = handler.unregister_callback("test")

    assert result is True
    assert "test" not in handler._callbacks


@pytest.mark.asyncio
async def test_should_retry_rate_limit():
    """Test should retry rate limit."""
    handler = ResponseHandler()

    response = APIResponse(
        id="",
        status=ResponseStatus.RATE_LIMITED,
    )

    should_retry = await handler.should_retry(response)

    assert should_retry is True


@pytest.mark.asyncio
async def test_should_retry_error():
    """Test should retry error."""
    handler = ResponseHandler()

    response = APIResponse(
        id="",
        status=ResponseStatus.ERROR,
    )

    should_retry = await handler.should_retry(response)

    assert should_retry is False


@pytest.mark.asyncio
async def test_get_retry_delay():
    """Test retry delay."""
    handler = ResponseHandler()

    response = APIResponse(id="", status=ResponseStatus.RATE_LIMITED)

    delay = await handler.get_retry_delay(response)

    assert delay == handler.config.retry_delay * 2


@pytest.mark.asyncio
async def test_get_history():
    """Test getting history."""
    handler = ResponseHandler()

    raw_response = {"id": "msg_1", "content": [{"type": "text", "text": "test"}]}
    await handler.handle(raw_response)

    history = await handler.get_history()

    assert len(history) == 1


@pytest.mark.asyncio
async def test_clear_history():
    """Test clearing history."""
    handler = ResponseHandler()

    raw_response = {"id": "msg_1", "content": [{"type": "text", "text": "test"}]}
    await handler.handle(raw_response)

    count = await handler.clear_history()

    assert count == 1
    assert len(handler._history) == 0


@pytest.mark.asyncio
async def test_handler_config():
    """Test handler config."""
    config = HandlerConfig(
        max_retries=5,
        retry_delay=2.0,
        timeout=120.0,
        stream=True,
    )

    assert config.max_retries == 5
    assert config.timeout == 120.0


@pytest.mark.asyncio
async def test_response_block():
    """Test response block."""
    block = ResponseBlock(
        type=ResponseType.TEXT,
        content="test",
        index=0,
    )

    assert block.type == ResponseType.TEXT
    assert block.content == "test"


@pytest.mark.asyncio
async def test_api_response():
    """Test API response."""
    response = APIResponse(
        id="msg_123",
        status=ResponseStatus.SUCCESS,
        blocks=[],
        usage={"input": 10, "output": 5},
    )

    assert response.id == "msg_123"
    assert response.status == ResponseStatus.SUCCESS