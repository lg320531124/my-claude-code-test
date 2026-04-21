"""Tests for command registry."""

import pytest
from src.cc.services.command_registry import (
    CommandRegistry,
    RegistryConfig,
    CommandCategory,
    CommandMeta,
    RegisteredCommand,
)


@pytest.mark.asyncio
async def test_command_registry_init():
    """Test registry initialization."""
    registry = CommandRegistry()
    assert registry.config is not None


@pytest.mark.asyncio
async def test_register_command():
    """Test registering command."""
    registry = CommandRegistry()

    async def handler(args, context):
        return "result"

    result = await registry.register("test", handler)
    assert result is True


@pytest.mark.asyncio
async def test_register_with_meta():
    """Test registering with metadata."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        pass

    meta = CommandMeta(
        name="test_cmd",
        description="Test command",
        category=CommandCategory.DEV,
        aliases=["t", "tc"],
    )

    result = await registry.register("test_cmd", handler, meta)
    assert result is True


@pytest.mark.asyncio
async def test_unregister_command():
    """Test unregistering command."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        pass

    await registry.register("test", handler)
    result = await registry.unregister("test")

    assert result is True


@pytest.mark.asyncio
async def test_get_command():
    """Test getting command."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        return "result"

    await registry.register("test", handler)

    command = await registry.get("test")
    assert command is not None


@pytest.mark.asyncio
async def test_get_command_by_alias():
    """Test getting command by alias."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        pass

    meta = CommandMeta(name="test", aliases=["t"])

    await registry.register("test", handler, meta)

    command = await registry.get("t")
    assert command is not None


@pytest.mark.asyncio
async def test_execute_command():
    """Test executing command."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        return args

    await registry.register("test", handler)

    result = await registry.execute("test", ["arg1", "arg2"])
    assert result == ["arg1", "arg2"]


@pytest.mark.asyncio
async def test_execute_not_found():
    """Test executing not found."""
    registry = CommandRegistry()

    with pytest.raises(ValueError):
        await registry.execute("nonexistent")


@pytest.mark.asyncio
async def test_register_subcommand():
    """Test registering subcommand."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        pass

    await registry.register("test", handler)

    async def sub_handler(args, ctx):
        return "sub"

    result = await registry.register_subcommand("test", "sub", sub_handler)
    assert result is True


@pytest.mark.asyncio
async def test_list_commands():
    """Test listing commands."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        pass

    await registry.register("test1", handler)
    await registry.register("test2", handler)

    commands = await registry.list_commands()
    assert len(commands) == 2


@pytest.mark.asyncio
async def test_list_by_category():
    """Test listing by category."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        pass

    meta = CommandMeta(name="git_test", category=CommandCategory.GIT)

    await registry.register("git_test", handler, meta)
    await registry.register("core_test", handler)

    commands = await registry.list_commands(category=CommandCategory.GIT)
    assert len(commands) == 1


@pytest.mark.asyncio
async def test_get_help():
    """Test getting help."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        pass

    meta = CommandMeta(
        name="test",
        description="Test command",
        aliases=["t"],
        examples=["test arg1"],
    )

    await registry.register("test", handler, meta)

    help_text = await registry.get_help("test")
    assert help_text is not None
    assert "test" in help_text


@pytest.mark.asyncio
async def test_search_commands():
    """Test searching commands."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        pass

    meta = CommandMeta(
        name="git_status",
        description="Show git status",
        aliases=["gs"],
    )

    await registry.register("git_status", handler, meta)

    results = await registry.search("git")
    assert len(results) > 0


@pytest.mark.asyncio
async def test_get_stats():
    """Test getting stats."""
    registry = CommandRegistry()

    async def handler(args, ctx):
        pass

    await registry.register("test1", handler)
    await registry.register("test2", handler)

    stats = await registry.get_stats()
    assert stats["total_commands"] == 2


@pytest.mark.asyncio
async def test_command_category_enum():
    """Test command category enum."""
    assert CommandCategory.CORE.value == "core"
    assert CommandCategory.GIT.value == "git"


@pytest.mark.asyncio
async def test_command_meta():
    """Test command meta."""
    meta = CommandMeta(
        name="test",
        description="Test",
        category=CommandCategory.DEV,
        aliases=["t"],
    )

    assert meta.name == "test"
    assert len(meta.aliases) == 1


@pytest.mark.asyncio
async def test_registry_config():
    """Test registry config."""
    config = RegistryConfig(
        allow_overrides=True,
        case_sensitive=True,
        max_commands=50,
    )

    assert config.allow_overrides is True
    assert config.max_commands == 50