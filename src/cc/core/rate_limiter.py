"""API Rate Limiter - Rate limiting for API calls."""

from __future__ import annotations
import asyncio
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..utils.log import get_logger

logger = get_logger(__name__)


class LimitType(Enum):
    """Limit types."""
    REQUESTS = "requests"
    TOKENS = "tokens"
    CONCURRENT = "concurrent"


@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000
    max_concurrent: int = 10
    retry_after: float = 60.0


@dataclass
class LimitState:
    """Limit tracking state."""
    requests: int = 0
    tokens: int = 0
    concurrent: int = 0
    last_reset: float = 0.0
    blocked_until: float = 0.0


@dataclass
class RateLimitConfig:
    """Rate limiter configuration."""
    limits: RateLimit = field(default_factory=RateLimit)
    auto_reset: bool = True
    reset_interval: float = 60.0
    queue_size: int = 100
    backoff_factor: float = 2.0
    max_backoff: float = 300.0


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._state = LimitState(last_reset=time.time())
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=config.queue_size if config else 100)
        self._lock = asyncio.Lock()
        self._backoff_level = 0

    async def acquire(
        self,
        tokens: int = 0
    ) -> bool:
        """Acquire rate limit slot."""
        async with self._lock:
            # Check if blocked
            if time.time() < self._state.blocked_until:
                return False

            # Reset if needed
            if self.config.auto_reset:
                await self._check_reset()

            # Check limits
            limits = self.config.limits

            # Requests limit
            if self._state.requests >= limits.requests_per_minute:
                return False

            # Tokens limit
            if self._state.tokens + tokens > limits.tokens_per_minute:
                return False

            # Concurrent limit
            if self._state.concurrent >= limits.max_concurrent:
                return False

            # Increment counters
            self._state.requests += 1
            self._state.tokens += tokens
            self._state.concurrent += 1

            return True

    async def release(self) -> None:
        """Release rate limit slot."""
        async with self._lock:
            self._state.concurrent -= 1

    async def _check_reset(self) -> None:
        """Check and reset counters."""
        elapsed = time.time() - self._state.last_reset

        if elapsed >= self.config.reset_interval:
            self._state.requests = 0
            self._state.tokens = 0
            self._state.concurrent = 0  # Also reset concurrent
            self._state.last_reset = time.time()
            self._backoff_level = 0

    async def wait_for_slot(
        self,
        tokens: int = 0,
        timeout: Optional[float] = None
    ) -> bool:
        """Wait for available slot."""
        start_time = time.time()

        while True:
            # First try to acquire
            if await self.acquire(tokens):
                return True

            # Check if timeout exceeded before waiting
            if timeout:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            # Calculate wait time - use shorter wait for quick retries
            backoff = min(
                self.config.backoff_factor ** self._backoff_level,
                self.config.max_backoff
            )
            self._backoff_level += 1

            # Use a reasonable wait time, considering reset_interval
            wait_time = min(backoff, self.config.reset_interval, 1.0)

            # Check if waiting would exceed timeout
            if timeout:
                elapsed = time.time() - start_time
                if elapsed + wait_time > timeout:
                    # Try one more time before timeout
                    await asyncio.sleep(timeout - elapsed)
                    if await self.acquire(tokens):
                        return True
                    return False

            await asyncio.sleep(wait_time)

    async def block(
        self,
        duration: Optional[float] = None
    ) -> None:
        """Block rate limiter."""
        use_duration = duration or self.config.limits.retry_after
        self._state.blocked_until = time.time() + use_duration

        logger.warning(f"Rate limited for {use_duration}s")

    async def unblock(self) -> None:
        """Unblock rate limiter."""
        self._state.blocked_until = 0.0

    async def get_state(self) -> LimitState:
        """Get current state."""
        return self._state

    async def get_usage(self) -> Dict[str, Any]:
        """Get usage metrics."""
        limits = self.config.limits

        return {
            "requests": self._state.requests,
            "requests_limit": limits.requests_per_minute,
            "requests_remaining": limits.requests_per_minute - self._state.requests,
            "tokens": self._state.tokens,
            "tokens_limit": limits.tokens_per_minute,
            "tokens_remaining": limits.tokens_per_minute - self._state.tokens,
            "concurrent": self._state.concurrent,
            "concurrent_limit": limits.max_concurrent,
            "blocked": time.time() < self._state.blocked_until,
        }

    async def reset(self) -> None:
        """Reset all counters."""
        async with self._lock:
            self._state.requests = 0
            self._state.tokens = 0
            self._state.concurrent = 0
            self._state.last_reset = time.time()
            self._state.blocked_until = 0.0
            self._backoff_level = 0

    def is_blocked(self) -> bool:
        """Check if blocked."""
        return time.time() < self._state.blocked_until

    async def queue_request(
        self,
        request: Dict[str, Any]
    ) -> bool:
        """Queue request."""
        try:
            self._queue.put_nowait(request)
            return True
        except asyncio.QueueFull:
            return False

    async def process_queue(
        self,
        processor: callable
    ) -> None:
        """Process queued requests."""
        while True:
            request = await self._queue.get()

            try:
                await self.wait_for_slot()
                await processor(request)
                await self.release()

            except Exception as e:
                logger.error(f"Queue processing error: {e}")

    def get_queue_size(self) -> int:
        """Get queue size."""
        return self._queue.qsize()


__all__ = [
    "LimitType",
    "RateLimit",
    "LimitState",
    "RateLimitConfig",
    "RateLimiter",
]