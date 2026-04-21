"""Tests for context builder."""

import pytest
from pathlib import Path
from src.cc.core.context_builder import (
    ContextBuilder,
    ContextType,
    ContextPriority,
    ContextBlock,
    ContextConfig,
    BuiltContext,
)


@pytest.mark.asyncio
async def test_context_builder_init():
    """Test context builder initialization."""
    builder = ContextBuilder()
    assert builder.config is not None
    assert builder._blocks == []


@pytest.mark.asyncio
async def test_add_system_context():
    """Test adding system context."""
    builder = ContextBuilder()

    block = await builder.add_system_context("System instructions")

    assert block.type == ContextType.SYSTEM
    assert block.priority == ContextPriority.CRITICAL
    assert block.content == "System instructions"


@pytest.mark.asyncio
async def test_add_user_context():
    """Test adding user context."""
    builder = ContextBuilder()

    block = await builder.add_user_context("User question")

    assert block.type == ContextType.USER
    assert block.priority == ContextPriority.HIGH


@pytest.mark.asyncio
async def test_add_file_context():
    """Test adding file context."""
    builder = ContextBuilder()

    # Create temp file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("print('hello')")
        f.flush()
        path = Path(f.name)

    block = await builder.add_file_context(path)

    assert block is not None
    assert block.type == ContextType.FILE

    # Clean up
    path.unlink()


@pytest.mark.asyncio
async def test_add_file_context_nonexistent():
    """Test adding nonexistent file."""
    builder = ContextBuilder()

    block = await builder.add_file_context(Path("/nonexistent/file.py"))

    assert block is None


@pytest.mark.asyncio
async def test_add_conversation_context():
    """Test adding conversation context."""
    builder = ContextBuilder()

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]

    blocks = await builder.add_conversation_context(messages)

    assert len(blocks) == 2
    assert all(b.type == ContextType.CONVERSATION for b in blocks)


@pytest.mark.asyncio
async def test_build():
    """Test building context."""
    builder = ContextBuilder()

    await builder.add_system_context("System")
    await builder.add_user_context("User")

    context = await builder.build()

    assert len(context.blocks) == 2
    assert context.total_tokens > 0


@pytest.mark.asyncio
async def test_build_with_limit():
    """Test building with token limit."""
    config = ContextConfig(max_tokens=100)
    builder = ContextBuilder(config)

    # Add large content with LOW priority so it gets truncated
    await builder.add_system_context("System" * 100, ContextPriority.LOW)
    await builder.add_user_context("User" * 100, ContextPriority.LOW)

    context = await builder.build()

    assert context.total_tokens <= 100
    assert context.truncated is True


@pytest.mark.asyncio
async def test_priority_ordering():
    """Test priority ordering."""
    builder = ContextBuilder()

    await builder.add_user_context("User", ContextPriority.LOW)
    await builder.add_system_context("System", ContextPriority.CRITICAL)

    context = await builder.build()

    # Critical should be first
    assert context.blocks[0].priority == ContextPriority.CRITICAL


@pytest.mark.asyncio
async def test_clear():
    """Test clearing blocks."""
    builder = ContextBuilder()

    await builder.add_system_context("Test")
    builder.clear()

    assert len(builder._blocks) == 0


@pytest.mark.asyncio
async def test_get_blocks():
    """Test getting blocks."""
    builder = ContextBuilder()

    await builder.add_system_context("S1")
    await builder.add_user_context("U1")

    blocks = builder.get_blocks()

    assert len(blocks) == 2


@pytest.mark.asyncio
async def test_get_token_estimate():
    """Test token estimate."""
    builder = ContextBuilder()

    await builder.add_system_context("Hello world")

    estimate = await builder.get_token_estimate()

    assert estimate > 0


@pytest.mark.asyncio
async def test_compression():
    """Test compression."""
    builder = ContextBuilder()

    # Add large content
    await builder.add_system_context("Test" * 1000)

    context = await builder.build(compress=True)

    # May be compressed
    if context.compressed:
        assert context.total_tokens < sum(b.token_estimate for b in builder._blocks)


@pytest.mark.asyncio
async def test_context_block():
    """Test context block."""
    block = ContextBlock(
        type=ContextType.FILE,
        content="code",
        priority=ContextPriority.HIGH,
        token_estimate=10,
        source="test.py",
    )

    assert block.type == ContextType.FILE
    assert block.content == "code"


@pytest.mark.asyncio
async def test_context_config():
    """Test context config."""
    config = ContextConfig(
        max_tokens=50000,
        include_system=True,
        include_project=True,
        include_files=False,
        include_history=True,
    )

    assert config.max_tokens == 50000
    assert config.include_files is False


@pytest.mark.asyncio
async def test_built_context():
    """Test built context."""
    context = BuiltContext(
        blocks=[],
        total_tokens=0,
        compressed=False,
        truncated=False,
        sources=["test"],
    )

    assert context.blocks == []
    assert context.sources == ["test"]