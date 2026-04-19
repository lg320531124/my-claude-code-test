"""Tests for schedule tools."""

import pytest
import asyncio
import time

from cc.tools.schedule import (
    CronScheduler,
    ScheduledJob,
    CronCreateTool,
    ScheduleWakeupTool,
    RemoteTriggerTool,
    get_scheduler,
)
from cc.types.tool import ToolUseContext


def test_scheduled_job():
    """Test scheduled job structure."""
    job = ScheduledJob(
        job_id="job-123",
        cron="*/5 * * * *",
        prompt="Test prompt",
        recurring=True,
        created_at=time.time(),
    )

    assert job.job_id == "job-123"
    assert job.cron == "*/5 * * * *"
    assert job.run_count == 0


def test_cron_scheduler_init():
    """Test scheduler initialization."""
    scheduler = CronScheduler()

    assert len(scheduler.jobs) == 0
    assert len(scheduler._running_tasks) == 0


def test_cron_scheduler_create_job():
    """Test creating a job."""
    scheduler = CronScheduler()

    job = scheduler.create_job(
        cron="0 9 * * *",
        prompt="Morning reminder",
        recurring=True,
    )

    assert job.job_id.startswith("job-")
    assert job.recurring is True
    assert len(scheduler.jobs) == 1


def test_cron_scheduler_cancel_job():
    """Test cancelling a job."""
    scheduler = CronScheduler()

    job = scheduler.create_job("* * * * *", "test", True)

    assert len(scheduler.jobs) == 1

    result = scheduler.cancel_job(job.job_id)

    assert result is True
    assert len(scheduler.jobs) == 0


def test_cron_scheduler_list_jobs():
    """Test listing jobs."""
    scheduler = CronScheduler()

    scheduler.create_job("* * * * *", "job1", True)
    scheduler.create_job("0 * * * *", "job2", True)

    jobs = scheduler.list_jobs()

    assert len(jobs) == 2


def test_cron_scheduler_parse_cron():
    """Test cron parsing."""
    scheduler = CronScheduler()

    # Every minute
    next_run = scheduler._parse_cron_next("* * * * *")
    assert next_run > time.time()

    # Every 5 minutes
    next_run = scheduler._parse_cron_next("*/5 * * * *")
    assert next_run > time.time()

    # Specific minute
    next_run = scheduler._parse_cron_next("30 * * * *")
    assert next_run > time.time()


@pytest.mark.asyncio
async def test_cron_scheduler_run_job():
    """Test running a job."""
    scheduler = CronScheduler()

    results = []

    async def callback(prompt):
        results.append(prompt)

    scheduler.set_callback(callback)

    job = scheduler.create_job("* * * * *", "test prompt", True)
    job.next_run = time.time()  # Force immediate run

    # Run job
    await scheduler._run_job(job)

    assert len(results) == 1
    assert results[0] == "test prompt"


@pytest.mark.asyncio
async def test_cron_scheduler_start_stop():
    """Test starting and stopping scheduler."""
    scheduler = CronScheduler()

    await scheduler.start()
    assert scheduler._started is True

    await asyncio.sleep(0.1)

    await scheduler.stop()
    assert scheduler._started is False


def test_cron_create_tool():
    """Test CronCreateTool."""
    tool = CronCreateTool()

    assert tool.name == "CronCreate"
    assert "schedule" in tool.description.lower()


@pytest.mark.asyncio
async def test_cron_create_tool_execute():
    """Test executing CronCreateTool."""
    tool = CronCreateTool()
    ctx = ToolUseContext(cwd="/tmp", session_id="test")

    from cc.tools.schedule import ScheduleInput
    input = ScheduleInput(
        cron="* * * * *",
        prompt="Test prompt",
        recurring=True,
    )

    result = await tool.execute(input, ctx)

    assert not result.is_error
    assert "Scheduled job" in result.content


def test_schedule_wakeup_tool():
    """Test ScheduleWakeupTool."""
    tool = ScheduleWakeupTool()

    assert tool.name == "ScheduleWakeup"


@pytest.mark.asyncio
async def test_schedule_wakeup_tool_execute():
    """Test executing ScheduleWakeupTool."""
    tool = ScheduleWakeupTool()
    ctx = ToolUseContext(cwd="/tmp", session_id="test")

    from cc.tools.schedule import ScheduleWakeupInput
    input = ScheduleWakeupInput(
        delay_seconds=120,
        prompt="Wake up test",
        reason="Testing wakeup",
    )

    result = await tool.execute(input, ctx)

    assert not result.is_error
    assert "Wakeup scheduled" in result.content
    # Clamp to 60-3600
    assert result.metadata["delay_seconds"] == 120


def test_remote_trigger_tool():
    """Test RemoteTriggerTool."""
    tool = RemoteTriggerTool()

    assert tool.name == "RemoteTrigger"


@pytest.mark.asyncio
async def test_remote_trigger_tool_execute():
    """Test executing RemoteTriggerTool."""
    tool = RemoteTriggerTool()
    ctx = ToolUseContext(cwd="/tmp", session_id="test")

    from cc.tools.schedule import RemoteTriggerInput
    input = RemoteTriggerInput(
        action="list",
        trigger_id=None,
        body=None,
    )

    result = await tool.execute(input, ctx)

    assert not result.is_error
    assert "list" in result.content


def test_get_scheduler():
    """Test getting global scheduler."""
    scheduler1 = get_scheduler()
    scheduler2 = get_scheduler()

    # Should return same instance
    assert scheduler1 is scheduler2


@pytest.mark.asyncio
async def test_list_scheduled_jobs():
    """Test listing scheduled jobs."""
    scheduler = get_scheduler()

    # Clear existing jobs
    scheduler.jobs.clear()

    scheduler.create_job("* * * * *", "test", True)

    jobs = scheduler.list_jobs()
    assert len(jobs) >= 1