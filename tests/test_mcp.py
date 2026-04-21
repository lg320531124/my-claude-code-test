"""Tests for MCP client."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import json

from cc.mcp.client import MCPConnection, MCPManager, MCPToolWrapper
from cc.mcp.server import MCPToolRegistry, MCPServerProcess
from cc.mcp.resources import MCPResourceCache, MCPSubscription, ResourceRegistry


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_mcp_connection_init():
    """Test MCP connection initialization."""
    conn = MCPConnection(
        name="test",
        command="python",
        args=["-m", "test_server"],
    )

    assert conn.name == "test"
    assert conn.command == "python"
    assert not conn.connected
    assert conn.tools == []


@pytest.mark.asyncio
async def test_mcp_manager_load_config(temp_dir):
    """Test MCP manager config loading."""
    config_file = temp_dir / "mcp.json"
    config_data = {
        "mcpServers": {
            "test_server": {
                "command": "python",
                "args": ["-m", "server"],
            },
        },
    }

    config_file.write_text(json.dumps(config_data))

    manager = MCPManager(config_path=config_file)
    await manager.load_config()

    assert "test_server" in manager.connections


def test_mcp_manager_get_tools():
    """Test getting tool schemas."""
    manager = MCPManager()

    # Add mock connection
    conn = MCPConnection(name="test", command="test")
    conn.connected = True
    conn.tools = [
        {"name": "tool1", "description": "Test tool", "inputSchema": {}},
    ]
    manager.connections["test"] = conn

    tools = manager.get_all_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "mcp_test_tool1"


def test_mcp_tool_registry():
    """Test tool registry."""
    registry = MCPToolRegistry()

    registry.register("test_tool", {"name": "test_tool"}, lambda x: x)

    assert "test_tool" in registry.tools
    schema = registry.get_schema("test_tool")
    assert schema is not None

    registry.unregister("test_tool")
    assert "test_tool" not in registry.tools


def test_mcp_resource_cache():
    """Test resource cache."""
    cache = MCPResourceCache(ttl_seconds=60)

    assert cache.ttl == 60
    assert len(cache.cache) == 0

    cache.clear()
    stats = cache.get_stats()
    assert stats["count"] == 0


def test_mcp_subscription():
    """Test subscription."""
    results = []

    def callback(uri, content):
        results.append((uri, content))

    sub = MCPSubscription("test://uri", callback)
    assert sub.active

    sub.notify("test content")
    # Callback runs async, need to wait
    import time
    time.sleep(0.1)

    assert len(results) == 1
    assert results[0] == ("test://uri", "test content")

    sub.active = False
    sub.notify("should not trigger")
    time.sleep(0.1)
    assert len(results) == 1


def test_resource_registry():
    """Test resource registry."""
    registry = ResourceRegistry()

    def handler(params):
        return f"Handled: {params}"

    registry.register("file://{path}", handler)
    assert len(registry.templates) == 1


def test_mcp_tool_wrapper():
    """Test MCP tool wrapper."""
    conn = MCPConnection(name="test", command="test")
    tool_info = {
        "name": "test_tool",
        "description": "A test tool",
        "inputSchema": {"type": "object"},
    }

    wrapper = MCPToolWrapper("test", tool_info, conn)

    assert wrapper.name == "mcp_test_test_tool"
    assert wrapper.description == "A test tool"

    schema = wrapper.get_schema()
    assert schema["name"] == "mcp_test_test_tool"


@pytest.mark.asyncio
async def test_mcp_manager_connect_all():
    """Test connecting to all servers."""
    manager = MCPManager()

    # Add mock connection that won't actually connect
    conn = MCPConnection(name="mock", command="nonexistent")
    manager.connections["mock"] = conn

    results = await manager.connect_all()
    assert "mock" in results
    # Will fail since command doesn't exist
    assert results["mock"] is False


def test_mcp_manager_server_info():
    """Test getting server info."""
    manager = MCPManager()

    conn = MCPConnection(name="test", command="test")
    conn.connected = True
    conn.tools = [{"name": "tool1"}]
    conn.resources = [{"uri": "test://1"}]
    manager.connections["test"] = conn

    info = manager.get_server_info("test")
    assert info["connected"] is True
    assert info["tools"] == 1
    assert info["resources"] == 1