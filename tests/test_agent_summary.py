"""Tests for agent summary."""

import pytest
from src.cc.services.agent_summary import (
    AgentSummarizer,
    AgentRole,
    AgentSummaryConfig,
)


@pytest.mark.asyncio
async def test_agent_summarizer_init():
    """Test agent summarizer initialization."""
    summarizer = AgentSummarizer()
    assert summarizer.config is not None
    assert summarizer._activities is not None


@pytest.mark.asyncio
async def test_record_activity():
    """Test activity recording."""
    summarizer = AgentSummarizer()

    activity = await summarizer.record(
        agent_id="agent_1",
        role=AgentRole.EXECUTOR,
        action="run_task",
        success=True,
        duration=1.5,
    )

    assert activity.agent_id == "agent_1"
    assert activity.role == AgentRole.EXECUTOR
    assert activity.success is True
    assert activity.duration == 1.5


@pytest.mark.asyncio
async def test_summarize():
    """Test summarization."""
    summarizer = AgentSummarizer()

    # Record some activities
    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True, 1.0)
    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task2", True, 2.0)
    await summarizer.record("agent_2", AgentRole.ANALYZER, "analyze", False, 0.5)

    summary = await summarizer.summarize()

    assert summary.total_activities == 3
    assert summary.successful == 2
    assert summary.failed == 1
    assert summary.total_duration == 3.5


@pytest.mark.asyncio
async def test_summarize_by_agent():
    """Test summarize by specific agent."""
    summarizer = AgentSummarizer()

    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True)
    await summarizer.record("agent_2", AgentRole.ANALYZER, "task2", True)

    summary = await summarizer.summarize(agent_id="agent_1")

    assert summary.total_activities == 1


@pytest.mark.asyncio
async def test_summarize_by_role():
    """Test summarize by role."""
    summarizer = AgentSummarizer()

    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True)
    await summarizer.record("agent_2", AgentRole.ANALYZER, "task2", True)

    summary = await summarizer.summarize(role=AgentRole.EXECUTOR)

    assert summary.total_activities == 1


@pytest.mark.asyncio
async def test_role_grouping():
    """Test role grouping."""
    summarizer = AgentSummarizer()

    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True)
    await summarizer.record("agent_2", AgentRole.ANALYZER, "task2", True)
    await summarizer.record("agent_3", AgentRole.REVIEWER, "task3", True)

    summary = await summarizer.summarize()

    assert "executor" in summary.by_role
    assert "analyzer" in summary.by_role
    assert "reviewer" in summary.by_role


@pytest.mark.asyncio
async def test_key_findings():
    """Test key findings extraction."""
    summarizer = AgentSummarizer()

    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True, 1.0)
    await summarizer.record("agent_2", AgentRole.EXECUTOR, "task2", False)

    summary = await summarizer.summarize()

    assert len(summary.key_findings) > 0
    assert "Success rate" in summary.key_findings[0]


@pytest.mark.asyncio
async def test_get_activities():
    """Test get activities."""
    summarizer = AgentSummarizer()

    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True)
    await summarizer.record("agent_2", AgentRole.ANALYZER, "task2", True)

    activities = await summarizer.get_activities()

    assert len(activities) == 2


@pytest.mark.asyncio
async def test_clear():
    """Test clear activities."""
    summarizer = AgentSummarizer()

    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True)

    count = await summarizer.clear()

    assert count == 1
    assert len(summarizer._activities) == 0


@pytest.mark.asyncio
async def test_export_json():
    """Test JSON export."""
    summarizer = AgentSummarizer()

    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True)
    exported = await summarizer.export(format="json")

    assert exported.startswith("{")
    assert exported.endswith("}")


@pytest.mark.asyncio
async def test_export_text():
    """Test text export."""
    summarizer = AgentSummarizer()

    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True)
    exported = await summarizer.export(format="text")

    assert "Total activities" in exported


@pytest.mark.asyncio
async def test_agent_stats():
    """Test agent stats."""
    summarizer = AgentSummarizer()

    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task1", True, 1.0)
    await summarizer.record("agent_1", AgentRole.EXECUTOR, "task2", False, 0.5)

    stats = await summarizer.get_agent_stats("agent_1")

    assert stats["agent_id"] == "agent_1"
    assert stats["total"] == 2
    assert stats["success_rate"] == 0.5


@pytest.mark.asyncio
async def test_max_activities_limit():
    """Test max activities limit."""
    summarizer = AgentSummarizer(AgentSummaryConfig(max_activities=5))

    for i in range(10):
        await summarizer.record(f"agent_{i}", AgentRole.EXECUTOR, f"task{i}", True)

    assert len(summarizer._activities) == 5