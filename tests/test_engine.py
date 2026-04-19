"""Tests for QueryEngine and MessageHistory."""

import pytest
import asyncio
from pathlib import Path
import tempfile

from cc.core.engine import QueryEngine, MessageHistory, ToolExecutor, QueryStats
from cc.types.message import create_user_message, UserMessage, AssistantMessage, TextBlock
from cc.types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
from cc.types.permission import PermissionDecision


class MockTool(ToolDef):
    """Mock tool for testing."""

    name = "MockTool"
    description = "A mock tool"

    class MockInput(ToolInput):
        value: str = "test"

    input_schema = MockInput

    async def execute(self, input: MockInput, ctx: ToolUseContext) -> ToolResult:
        return ToolResult(content=f"Mock result: {input.value}")

    def check_permission(self, input: MockInput, ctx: ToolUseContext) -> PermissionResult:
        from cc.types.permission import PermissionResult, PermissionDecision
        return PermissionResult(decision=PermissionDecision.ALLOW.value)


def test_message_history_add():
    """Test adding messages to history."""
    history = MessageHistory(max_messages=10)

    msg = create_user_message("Hello")
    history.add(msg)

    assert len(history.messages) == 1
    assert history.messages[0].role == "user"


def test_message_history_limit():
    """Test message history limits."""
    history = MessageHistory(max_messages=5, max_tokens=1000)

    # Add many messages
    for i in range(10):
        msg = create_user_message(f"Message {i}")
        history.add(msg)

    # Should compress
    assert len(history.messages) <= 6  # compressed + recent


def test_message_history_compression():
    """Test message compression."""
    history = MessageHistory(max_messages=100, max_tokens=500)

    # Add large messages
    for i in range(10):
        msg = create_user_message("This is a long message " * 50)
        history.add(msg)

    # Check compression happened
    assert len(history.messages) < 10
    assert any("[COMPRESSED" in str(m.content) for m in history.messages)


def test_message_history_api_format():
    """Test converting to API format."""
    history = MessageHistory()

    msg = create_user_message("Test message")
    history.add(msg)

    api_format = history.to_api_format()
    assert len(api_format) == 1
    assert api_format[0]["role"] == "user"


def test_message_history_token_usage():
    """Test token usage tracking."""
    history = MessageHistory(max_tokens=10000)

    msg = create_user_message("Hello world")
    history.add(msg)

    usage = history.get_token_usage()
    assert usage["message_count"] == 1
    assert usage["estimated_tokens"] > 0
    assert usage["max_tokens"] == 10000


def test_tool_executor_get_tool():
    """Test tool executor tool retrieval."""
    tool = MockTool()
    executor = ToolExecutor([tool])

    assert executor.get_tool("MockTool") == tool
    assert executor.get_tool("NotExist") is None


def test_tool_executor_schemas():
    """Test getting tool schemas."""
    tool = MockTool()
    executor = ToolExecutor([tool])

    schemas = executor.get_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "MockTool"


@pytest.mark.asyncio
async def test_tool_executor_execute():
    """Test tool execution."""
    tool = MockTool()
    executor = ToolExecutor([tool])

    ctx = ToolUseContext(cwd="/tmp", session_id="test")

    result = await executor.execute_single(
        {"id": "1", "name": "MockTool", "input": {"value": "test"}},
        ctx,
    )

    assert result["type"] == "tool_result"
    assert "Mock result" in result["content"]


@pytest.mark.asyncio
async def test_tool_executor_unknown_tool():
    """Test executing unknown tool."""
    executor = ToolExecutor([])

    ctx = ToolUseContext(cwd="/tmp", session_id="test")

    result = await executor.execute_single(
        {"id": "1", "name": "Unknown", "input": {}},
        ctx,
    )

    assert result["is_error"] is True
    assert "Unknown tool" in result["content"]


@pytest.mark.asyncio
async def test_tool_executor_parallel():
    """Test parallel tool execution."""
    tool = MockTool()
    executor = ToolExecutor([tool], max_parallel=3)

    ctx = ToolUseContext(cwd="/tmp", session_id="test")

    results = await executor.execute_parallel(
        [
            {"id": "1", "name": "MockTool", "input": {"value": "a"}},
            {"id": "2", "name": "MockTool", "input": {"value": "b"}},
            {"id": "3", "name": "MockTool", "input": {"value": "c"}},
        ],
        ctx,
    )

    assert len(results) == 3


def test_tool_executor_stats():
    """Test execution statistics."""
    tool = MockTool()
    executor = ToolExecutor([tool])

    stats = executor.get_stats()
    assert stats["executed"] == 0
    assert stats["failed"] == 0
    assert stats["total"] == 0


def test_query_stats():
    """Test query statistics."""
    stats = QueryStats()

    stats.input_tokens = 1000
    stats.output_tokens = 500
    stats.tool_calls = 3
    stats.turns = 2

    data = stats.to_dict()
    assert data["input_tokens"] == 1000
    assert data["total_tokens"] == 1500
    assert data["tool_calls"] == 3


def test_query_stats_cost_estimate():
    """Test cost estimation."""
    stats = QueryStats()
    stats.input_tokens = 1_000_000
    stats.output_tokens = 500_000

    # Test different models
    cost_sonnet = stats.estimate_cost("claude-sonnet-4-6")
    cost_haiku = stats.estimate_cost("claude-haiku-4-5")
    cost_opus = stats.estimate_cost("claude-opus-4-5")

    assert cost_haiku < cost_sonnet < cost_opus


def test_message_history_clear():
    """Test clearing history."""
    history = MessageHistory()

    for i in range(5):
        history.add(create_user_message(f"Msg {i}"))

    assert len(history.messages) == 5

    history.clear()
    assert len(history.messages) == 0
    assert history._token_estimate == 0


def test_query_engine_init():
    """Test QueryEngine initialization."""
    engine = QueryEngine(
        model="claude-sonnet-4-6",
        tools=[],
        max_tokens=4096,
    )

    assert engine.model == "claude-sonnet-4-6"
    assert engine.max_tokens == 4096
    assert engine.max_turns == 20


def test_query_engine_callbacks():
    """Test setting callbacks."""
    engine = QueryEngine()

    def on_text(text): pass
    def on_tool_start(name): pass
    def on_tool_result(result): pass

    engine.set_callbacks(
        on_text=on_text,
        on_tool_start=on_tool_start,
        on_tool_result=on_tool_result,
    )

    assert engine._on_text == on_text
    assert engine._on_tool_start == on_tool_start


def test_query_engine_context_summary():
    """Test context summary."""
    engine = QueryEngine()

    summary = engine.get_context_summary()
    assert "history" in summary
    assert "tools" in summary
    assert "stats" in summary