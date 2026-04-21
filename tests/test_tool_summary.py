"""Tests for tool summary."""

import pytest
from src.cc.services.tool_summary import (
    ToolSummarizer,
    ToolCategory,
)


@pytest.mark.asyncio
async def test_tool_summarizer_init():
    """Test tool summarizer initialization."""
    summarizer = ToolSummarizer()
    assert summarizer.config is not None
    assert summarizer._usage is not None


@pytest.mark.asyncio
async def test_record_usage():
    """Test recording usage."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", success=True, duration=1.0)

    assert len(summarizer._usage) == 1


@pytest.mark.asyncio
async def test_summarize():
    """Test summarization."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True, 1.0)
    await summarizer.record("write", True, 2.0)
    await summarizer.record("bash", False, 0.5)

    summary = await summarizer.summarize()

    assert summary.total_calls == 3
    assert summary.successful == 2
    assert summary.failed == 1


@pytest.mark.asyncio
async def test_by_tool():
    """Test grouping by tool."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True)
    await summarizer.record("read", True)
    await summarizer.record("write", True)

    summary = await summarizer.summarize()

    assert summary.by_tool["read"] == 2
    assert summary.by_tool["write"] == 1


@pytest.mark.asyncio
async def test_by_category():
    """Test grouping by category."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True)
    await summarizer.record("write", True)
    await summarizer.record("bash", True)

    summary = await summarizer.summarize()

    assert ToolCategory.FILE.value in summary.by_category
    assert ToolCategory.SYSTEM.value in summary.by_category


@pytest.mark.asyncio
async def test_most_used():
    """Test most used tools."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True)
    await summarizer.record("read", True)
    await summarizer.record("read", True)
    await summarizer.record("write", True)

    summary = await summarizer.summarize()

    assert "read" in summary.most_used


@pytest.mark.asyncio
async def test_filter_by_tool():
    """Test filtering by tool."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True)
    await summarizer.record("write", True)

    summary = await summarizer.summarize(tool_name="read")

    assert summary.total_calls == 1


@pytest.mark.asyncio
async def test_filter_by_category():
    """Test filtering by category."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True)
    await summarizer.record("bash", True)

    summary = await summarizer.summarize(category=ToolCategory.FILE)

    assert summary.total_calls == 1


@pytest.mark.asyncio
async def test_get_usage_history():
    """Test getting usage history."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True)
    await summarizer.record("write", True)

    history = await summarizer.get_usage_history()

    assert len(history) == 2


@pytest.mark.asyncio
async def test_clear():
    """Test clearing usage."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True)
    count = await summarizer.clear()

    assert count == 1
    assert len(summarizer._usage) == 0


@pytest.mark.asyncio
async def test_export_json():
    """Test JSON export."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True)
    exported = await summarizer.export(format="json")

    assert exported.startswith("{")
    assert exported.endswith("}")


@pytest.mark.asyncio
async def test_export_text():
    """Test text export."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True)
    exported = await summarizer.export(format="text")

    assert "Total calls" in exported


@pytest.mark.asyncio
async def test_get_tool_stats():
    """Test getting tool stats."""
    summarizer = ToolSummarizer()

    await summarizer.record("read", True, 1.0)
    await summarizer.record("read", False, 0.5)

    stats = await summarizer.get_tool_stats("read")

    assert stats["total_calls"] == 2
    assert stats["success_rate"] == 0.5


@pytest.mark.asyncio
async def test_error_tracking():
    """Test error tracking."""
    from src.cc.services.tool_summary import ToolSummaryConfig

    summarizer = ToolSummarizer(ToolSummaryConfig(include_errors=True))

    await summarizer.record("bash", False, error="Command failed")

    summary = await summarizer.summarize()

    assert len(summary.errors) > 0


@pytest.mark.asyncio
async def test_size_tracking():
    """Test size tracking."""
    from src.cc.services.tool_summary import ToolSummaryConfig

    summarizer = ToolSummarizer(ToolSummaryConfig(track_sizes=True))

    await summarizer.record("read", True, input_size=100, output_size=500)

    stats = await summarizer.get_tool_stats("read")

    assert stats["total_input_size"] == 100
    assert stats["total_output_size"] == 500