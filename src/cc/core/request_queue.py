"""Request Queue - Queue for API requests."""

from __future__ import annotations
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..utils.log import get_logger

logger = get_logger(__name__)


class QueuePriority(Enum):
    """Queue priority."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class QueueStatus(Enum):
    """Queue status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedRequest:
    """Queued request."""
    id: str
    data: Dict[str, Any]
    priority: QueuePriority = QueuePriority.NORMAL
    status: QueueStatus = QueueStatus.PENDING
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueueConfig:
    """Queue configuration."""
    max_size: int = 1000
    max_concurrent: int = 10
    timeout: float = 60.0
    retry_limit: int = 3
    priority_enabled: bool = True
    persist: bool = False


@dataclass
class QueueStats:
    """Queue statistics."""
    total_requests: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    avg_duration: float = 0.0


class RequestQueue:
    """Queue for API requests."""

    def __init__(self, config: Optional[QueueConfig] = None):
        self.config = config or QueueConfig()
        self._queues: Dict[QueuePriority, asyncio.Queue] = {
            QueuePriority.HIGH: asyncio.Queue(),
            QueuePriority.NORMAL: asyncio.Queue(),
            QueuePriority.LOW: asyncio.Queue(),
            QueuePriority.BACKGROUND: asyncio.Queue(),
        }
        self._pending: Dict[str, QueuedRequest] = {}
        self._running: Dict[str, QueuedRequest] = {}
        self._completed: List[QueuedRequest] = []
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(config.max_concurrent if config else 10)
        self._processor: Optional[Callable] = None

    async def enqueue(
        self,
        data: Dict[str, Any],
        priority: QueuePriority = QueuePriority.NORMAL
    ) -> QueuedRequest:
        """Enqueue request."""
        import uuid

        request_id = str(uuid.uuid4())[:8]

        request = QueuedRequest(
            id=request_id,
            data=data,
            priority=priority,
            status=QueueStatus.PENDING,
            created_at=time.time(),
        )

        # Add to queue
        queue = self._queues[priority]

        try:
            queue.put_nowait(request)
        except asyncio.QueueFull:
            raise Exception("Queue full")

        # Track pending
        self._pending[request_id] = request

        logger.debug(f"Enqueued request {request_id}")
        return request

    async def dequeue(
        self,
        timeout: Optional[float] = None
    ) -> Optional[QueuedRequest]:
        """Dequeue request."""
        use_timeout = timeout or self.config.timeout

        # Try queues in priority order
        for priority in [
            QueuePriority.HIGH,
            QueuePriority.NORMAL,
            QueuePriority.LOW,
            QueuePriority.BACKGROUND,
        ]:
            queue = self._queues[priority]

            try:
                request = queue.get_nowait()
                request.status = QueueStatus.RUNNING
                request.started_at = time.time()

                # Move to running
                if request.id in self._pending:
                    del self._pending[request.id]

                self._running[request.id] = request

                return request

            except asyncio.QueueEmpty:
                continue

        # Wait for any queue
        try:
            request = await asyncio.wait_for(
                self._queues[QueuePriority.NORMAL].get(),
                timeout=use_timeout
            )

            request.status = QueueStatus.RUNNING
            request.started_at = time.time()

            if request.id in self._pending:
                del self._pending[request.id]

            self._running[request.id] = request

            return request

        except asyncio.TimeoutError:
            return None

    async def complete(
        self,
        request_id: str,
        result: Any
    ) -> bool:
        """Mark request complete."""
        request = self._running.get(request_id)

        if not request:
            return False

        request.status = QueueStatus.COMPLETED
        request.completed_at = time.time()
        request.result = result

        # Move to completed
        del self._running[request_id]
        self._completed.append(request)

        logger.debug(f"Completed request {request_id}")
        return True

    async def fail(
        self,
        request_id: str,
        error: str
    ) -> bool:
        """Mark request failed."""
        request = self._running.get(request_id)

        if not request:
            return False

        request.status = QueueStatus.FAILED
        request.completed_at = time.time()
        request.error = error

        # Check retry
        if request.retries < self.config.retry_limit:
            request.retries += 1
            request.status = QueueStatus.PENDING

            # Re-enqueue
            queue = self._queues[request.priority]
            queue.put_nowait(request)

            self._pending[request_id] = request
            del self._running[request_id]

            logger.info(f"Retrying request {request_id}")
            return True

        # Final failure
        del self._running[request_id]
        self._completed.append(request)

        logger.error(f"Failed request {request_id}: {error}")
        return True

    async def cancel(
        self,
        request_id: str
    ) -> bool:
        """Cancel request."""
        # Check pending
        if request_id in self._pending:
            request = self._pending[request_id]
            request.status = QueueStatus.CANCELLED
            del self._pending[request_id]
            return True

        # Check running
        if request_id in self._running:
            request = self._running[request_id]
            request.status = QueueStatus.CANCELLED
            del self._running[request_id]
            return True

        return False

    async def get_request(
        self,
        request_id: str
    ) -> Optional[QueuedRequest]:
        """Get request by ID."""
        if request_id in self._pending:
            return self._pending[request_id]

        if request_id in self._running:
            return self._running[request_id]

        for request in self._completed:
            if request.id == request_id:
                return request

        return None

    async def process(
        self,
        processor: Callable
    ) -> None:
        """Process queue."""
        self._processor = processor

        while True:
            async with self._semaphore:
                request = await self.dequeue()

                if not request:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    result = await processor(request.data)
                    await self.complete(request.id, result)

                except Exception as e:
                    await self.fail(request.id, str(e))

    async def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        total_completed = len(self._completed)

        durations = [
            r.completed_at - r.started_at
            for r in self._completed
            if r.started_at and r.completed_at
        ]

        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return QueueStats(
            total_requests=len(self._pending) + len(self._running) + total_completed,
            pending=len(self._pending),
            running=len(self._running),
            completed=sum(1 for r in self._completed if r.status == QueueStatus.COMPLETED),
            failed=sum(1 for r in self._completed if r.status == QueueStatus.FAILED),
            avg_duration=avg_duration,
        )

    async def clear(self) -> int:
        """Clear queue."""
        count = len(self._pending) + len(self._running)

        self._pending.clear()
        self._running.clear()

        for queue in self._queues.values():
            while not queue.empty():
                queue.get_nowait()

        return count

    async def clear_completed(self) -> int:
        """Clear completed requests."""
        count = len(self._completed)
        self._completed.clear()
        return count

    def get_size(self) -> int:
        """Get total queue size."""
        return sum(q.qsize() for q in self._queues.values())

    def is_empty(self) -> bool:
        """Check if empty."""
        return self.get_size() == 0


__all__ = [
    "QueuePriority",
    "QueueStatus",
    "QueuedRequest",
    "QueueConfig",
    "QueueStats",
    "RequestQueue",
]