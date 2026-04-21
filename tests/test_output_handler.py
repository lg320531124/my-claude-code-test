"""Tests for output handler."""

import pytest
from src.cc.services.output_handler import (
    OutputHandler,
    OutputConfig,
    OutputType,
    OutputFormat,
    OutputChunk,
)


@pytest.mark.asyncio
async def test_output_handler_init():
    """Test handler initialization."""
    handler = OutputHandler()
    assert handler.config is not None


@pytest.mark.asyncio
async def test_handle_text():
    """Test handling text."""
    handler = OutputHandler()

    chunk = await handler.handle("test content")
    assert chunk.type == OutputType.TEXT
    assert chunk.content == "test content"


@pytest.mark.asyncio
async def test_handle_json():
    """Test handling JSON."""
    handler = OutputHandler()

    chunk = await handler.handle(
        '{"key": "value"}',
        OutputType.JSON
    )
    assert chunk.type == OutputType.JSON


@pytest.mark.asyncio
async def test_handle_error():
    """Test handling error."""
    handler = OutputHandler()

    chunk = await handler.error("Error message", code="E001")
    assert chunk.type == OutputType.ERROR
    assert chunk.metadata.get("code") == "E001"


@pytest.mark.asyncio
async def test_handle_success():
    """Test handling success."""
    handler = OutputHandler()

    chunk = await handler.success("Success message")
    assert chunk.type == OutputType.SUCCESS


@pytest.mark.asyncio
async def test_handle_warning():
    """Test handling warning."""
    handler = OutputHandler()

    chunk = await handler.warning("Warning message")
    assert chunk.type == OutputType.WARNING


@pytest.mark.asyncio
async def test_handle_info():
    """Test handling info."""
    handler = OutputHandler()

    chunk = await handler.info("Info message")
    assert chunk.type == OutputType.INFO


@pytest.mark.asyncio
async def test_handle_code():
    """Test handling code."""
    handler = OutputHandler()

    chunk = await handler.code("print('hello')", language="python")
    assert chunk.type == OutputType.CODE
    assert chunk.metadata.get("language") == "python"


@pytest.mark.asyncio
async def test_handle_table():
    """Test handling table."""
    handler = OutputHandler()

    chunk = await handler.table([
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ])

    assert chunk.type == OutputType.TABLE


@pytest.mark.asyncio
async def test_handle_markdown():
    """Test handling markdown."""
    handler = OutputHandler()

    chunk = await handler.markdown("# Heading")
    assert chunk.type == OutputType.MARKDOWN


@pytest.mark.asyncio
async def test_get_buffer():
    """Test getting buffer."""
    handler = OutputHandler()

    await handler.handle("content1")
    await handler.handle("content2")

    buffer = await handler.get_buffer()
    assert len(buffer) == 2


@pytest.mark.asyncio
async def test_clear_buffer():
    """Test clearing buffer."""
    handler = OutputHandler()

    await handler.handle("content")
    count = await handler.clear_buffer()

    assert count == 1
    assert len(handler._buffer) == 0


@pytest.mark.asyncio
async def test_register_callback():
    """Test registering callback."""
    handler = OutputHandler()

    callbacks = []

    def callback(chunk):
        callbacks.append(chunk)

    handler.register_callback(callback)

    await handler.handle("test")

    assert len(callbacks) == 1


@pytest.mark.asyncio
async def test_output_type_enum():
    """Test output type enum."""
    assert OutputType.TEXT.value == "text"
    assert OutputType.JSON.value == "json"
    assert OutputType.ERROR.value == "error"


@pytest.mark.asyncio
async def test_output_format_enum():
    """Test output format enum."""
    assert OutputFormat.PLAIN.value == "plain"
    assert OutputFormat.PRETTY.value == "pretty"


@pytest.mark.asyncio
async def test_output_config():
    """Test output config."""
    config = OutputConfig(
        format=OutputFormat.COMPACT,
        colorize=True,
        max_width=100,
    )

    assert config.format == OutputFormat.COMPACT
    assert config.max_width == 100