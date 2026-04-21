"""Tests for request queue."""

import pytest
import asyncio
from src.cc.core.request_queue import (
    RequestQueue,
    QueueConfig,
    QueuePriority,
    QueueStatus,
    QueuedRequest,
    QueueStats,
)


@pytest.mark.asyncio
async def test_request_queue_init():
    """Test request queue initialization."""
    queue = RequestQueue()
    assert queue.config is not None
    assert len(queue._queues) == 4


@pytest.mark.asyncio
async def test_enqueue():
    """Test enqueue request."""
    queue = RequestQueue()

    request = await queue.enqueue({"data": "test"})
    assert request.id is not None
    assert request.status == QueueStatus.PENDING
    assert request.priority == QueuePriority.NORMAL

    assert queue.get_size() == 1


@pytest.mark.asyncio
async def test_enqueue_with_priority():
    """Test enqueue with priority."""
    queue = RequestQueue()

    request = await queue.enqueue(
        {"data": "urgent"},
        priority=QueuePriority.HIGH
    )

    assert request.priority == QueuePriority.HIGH


@pytest.mark.asyncio
async def test_dequeue():
    """Test dequeue request."""
    queue = RequestQueue()

    await queue.enqueue({"data": "test"})
    request = await queue.dequeue(timeout=1.0)

    assert request is not None
    assert request.status == QueueStatus.RUNNING


@pytest.mark.asyncio
async def test_dequeue_priority_order():
    """Test dequeue priority order."""
    queue = RequestQueue()

    # Enqueue in different priorities
    await queue.enqueue({"data": "low"}, priority=QueuePriority.LOW)
    await queue.enqueue({"data": "high"}, priority=QueuePriority.HIGH)
    await queue.enqueue({"data": "normal"}, priority=QueuePriority.NORMAL)

    # Should dequeue high first
    request = await queue.dequeue(timeout=1.0)
    assert request.data["data"] == "high"


@pytest.mark.asyncio
async def test_complete():
    """Test complete request."""
    queue = RequestQueue()

    request = await queue.enqueue({"data": "test"})
    await queue.dequeue(timeout=1.0)

    result = await queue.complete(request.id, {"result": "success"})
    assert result is True

    assert request.status == QueueStatus.COMPLETED
    assert request.result == {"result": "success"}


@pytest.mark.asyncio
async def test_fail():
    """Test fail request."""
    config = QueueConfig(retry_limit=0)
    queue = RequestQueue(config)

    request = await queue.enqueue({"data": "test"})
    await queue.dequeue(timeout=1.0)

    result = await queue.fail(request.id, "Error occurred")
    assert result is True

    assert request.status == QueueStatus.FAILED
    assert request.error == "Error occurred"


@pytest.mark.asyncio
async def test_fail_with_retry():
    """Test fail with retry."""
    config = QueueConfig(retry_limit=2)
    queue = RequestQueue(config)

    request = await queue.enqueue({"data": "test"})
    await queue.dequeue(timeout=1.0)

    await queue.fail(request.id, "Error")

    assert request.status == QueueStatus.PENDING
    assert request.retries == 1


@pytest.mark.asyncio
async def test_cancel_pending():
    """Test cancel pending request."""
    queue = RequestQueue()

    request = await queue.enqueue({"data": "test"})
    result = await queue.cancel(request.id)

    assert result is True
    assert request.status == QueueStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_running():
    """Test cancel running request."""
    queue = RequestQueue()

    request = await queue.enqueue({"data": "test"})
    await queue.dequeue(timeout=1.0)

    result = await queue.cancel(request.id)
    assert result is True


@pytest.mark.asyncio
async def test_get_request():
    """Test get request."""
    queue = RequestQueue()

    request = await queue.enqueue({"data": "test"})
    found = await queue.get_request(request.id)

    assert found is not None
    assert found.id == request.id


@pytest.mark.asyncio
async def test_get_stats():
    """Test get stats."""
    queue = RequestQueue()

    await queue.enqueue({"data": "test1"})
    await queue.enqueue({"data": "test2"})
    await queue.dequeue(timeout=1.0)

    stats = await queue.get_stats()

    assert stats.total_requests >= 2
    assert stats.pending >= 0
    assert stats.running >= 1


@pytest.mark.asyncio
async def test_clear():
    """Test clear queue."""
    queue = RequestQueue()

    await queue.enqueue({"data": "test1"})
    await queue.enqueue({"data": "test2"})
    await queue.dequeue(timeout=1.0)

    count = await queue.clear()

    assert count >= 1
    assert queue.get_size() == 0


@pytest.mark.asyncio
async def test_clear_completed():
    """Test clear completed."""
    queue = RequestQueue()

    request = await queue.enqueue({"data": "test"})
    await queue.dequeue(timeout=1.0)
    await queue.complete(request.id, "result")

    count = await queue.clear_completed()
    assert count == 1


@pytest.mark.asyncio
async def test_is_empty():
    """Test is empty."""
    queue = RequestQueue()

    assert queue.is_empty() is True

    await queue.enqueue({"data": "test"})
    assert queue.is_empty() is False


@pytest.mark.asyncio
async def test_queue_config():
    """Test queue config."""
    config = QueueConfig(
        max_size=500,
        max_concurrent=5,
        timeout=30.0,
        retry_limit=5,
    )

    assert config.max_size == 500
    assert config.max_concurrent == 5
    assert config.retry_limit == 5


@pytest.mark.asyncio
async def test_queued_request():
    """Test queued request."""
    request = QueuedRequest(
        id="test_123",
        data={"key": "value"},
        priority=QueuePriority.HIGH,
    )

    assert request.id == "test_123"
    assert request.priority == QueuePriority.HIGH
    assert request.status == QueueStatus.PENDING


@pytest.mark.asyncio
async def test_queue_priority():
    """Test queue priority enum."""
    assert QueuePriority.HIGH.value == "high"
    assert QueuePriority.NORMAL.value == "normal"
    assert QueuePriority.LOW.value == "low"
    assert QueuePriority.BACKGROUND.value == "background"


@pytest.mark.asyncio
async def test_queue_status():
    """Test queue status enum."""
    assert QueueStatus.PENDING.value == "pending"
    assert QueueStatus.RUNNING.value == "running"
    assert QueueStatus.COMPLETED.value == "completed"
    assert QueueStatus.FAILED.value == "failed"
    assert QueueStatus.CANCELLED.value == "cancelled"