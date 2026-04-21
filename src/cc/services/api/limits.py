"""API Limits - API rate limits and usage tracking."""

from __future__ import annotations
import asyncio
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class LimitType(Enum):
    """Types of API limits."""
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_DAY = "requests_per_day"
    TOKENS_PER_MINUTE = "tokens_per_minute"
    TOKENS_PER_DAY = "tokens_per_day"
    CONCURRENT_REQUESTS = "concurrent_requests"
    CONTEXT_LENGTH = "context_length"
    OUTPUT_LENGTH = "output_length"


@dataclass
class LimitConfig:
    """Limit configuration."""
    requests_per_minute: int = 60
    requests_per_day: int = 1000
    tokens_per_minute: int = 100000
    tokens_per_day: int = 1000000
    max_concurrent: int = 5
    max_context_tokens: int = 200000
    max_output_tokens: int = 4096


@dataclass
class UsageRecord:
    """Record of API usage."""
    timestamp: float
    requests: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


@dataclass
class LimitStatus:
    """Current limit status."""
    limit_type: LimitType
    used: int
    limit: int
    remaining: int
    reset_time: Optional[float] = None
    percentage_used: float = 0.0

    def is_exceeded(self) -> bool:
        """Check if limit is exceeded."""
        return self.used >= self.limit

    def is_near_limit(self, threshold: float = 0.8) -> bool:
        """Check if near limit threshold."""
        return self.percentage_used >= threshold


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, config: Optional[LimitConfig] = None):
        self.config = config or LimitConfig()
        self._request_history: List[UsageRecord] = []
        self._token_history: List[UsageRecord] = []
        self._active_requests: int = 0
        self._lock = asyncio.Lock()

    async def check_request_limit(self) -> LimitStatus:
        """Check request limit status."""
        async with self._lock:
            now = time.time()

            # Minute limit
            minute_requests = len([
                r for r in self._request_history
                if now - r.timestamp < 60
            ])

            return LimitStatus(
                limit_type=LimitType.REQUESTS_PER_MINUTE,
                used=minute_requests,
                limit=self.config.requests_per_minute,
                remaining=self.config.requests_per_minute - minute_requests,
                reset_time=now + 60,
                percentage_used=minute_requests / self.config.requests_per_minute,
            )

    async def check_token_limit(self) -> LimitStatus:
        """Check token limit status."""
        async with self._lock:
            now = time.time()

            # Minute tokens
            minute_tokens = sum(
                r.input_tokens + r.output_tokens
                for r in self._token_history
                if now - r.timestamp < 60
            )

            return LimitStatus(
                limit_type=LimitType.TOKENS_PER_MINUTE,
                used=minute_tokens,
                limit=self.config.tokens_per_minute,
                remaining=self.config.tokens_per_minute - minute_tokens,
                reset_time=now + 60,
                percentage_used=minute_tokens / self.config.tokens_per_minute,
            )

    async def can_make_request(self) -> bool:
        """Check if can make a request."""
        request_status = await self.check_request_limit()

        if request_status.is_exceeded():
            return False

        if self._active_requests >= self.config.max_concurrent:
            return False

        return True

    async def acquire(self, estimated_tokens: int = 0) -> bool:
        """Acquire request slot."""
        async with self._lock:
            if not await self.can_make_request():
                return False

            self._active_requests += 1

            # Record request
            record = UsageRecord(
                timestamp=time.time(),
                input_tokens=estimated_tokens,
            )
            self._request_history.append(record)

            return True

    async def release(self, actual_tokens: int = 0) -> None:
        """Release request slot."""
        async with self._lock:
            self._active_requests = max(0, self._active_requests - 1)

            # Update last record with actual tokens
            if self._request_history:
                self._request_history[-1].output_tokens = actual_tokens
                self._token_history.append(self._request_history[-1])

    async def wait_for_slot(self, timeout: float = 60.0) -> bool:
        """Wait for available slot."""
        start = time.time()

        while time.time() - start < timeout:
            if await self.can_make_request():
                return True

            # Wait a bit before checking again
            await asyncio.sleep(1)

        return False

    async def get_wait_time(self) -> float:
        """Get estimated wait time."""
        request_status = await self.check_request_limit()

        if not request_status.is_exceeded():
            if self._active_requests >= self.config.max_concurrent:
                # Wait for a concurrent slot
                return 5.0
            return 0.0

        # Wait until reset
        if request_status.reset_time:
            return request_status.reset_time - time.time()

        return 60.0

    def cleanup_history(self) -> None:
        """Clean up old history."""
        now = time.time()
        self._request_history = [
            r for r in self._request_history
            if now - r.timestamp < 3600  # Keep 1 hour
        ]
        self._token_history = [
            r for r in self._token_history
            if now - r.timestamp < 3600
        ]


class UsageTracker:
    """Track API usage."""

    def __init__(self):
        self._daily_records: Dict[str, List[UsageRecord]] = {}
        self._session_total: Dict[str, int] = {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """Record usage."""
        record = UsageRecord(
            timestamp=time.time(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
        )

        date_key = time.strftime("%Y-%m-%d")
        if date_key not in self._daily_records:
            self._daily_records[date_key] = []

        self._daily_records[date_key].append(record)

        self._session_total["requests"] += 1
        self._session_total["input_tokens"] += input_tokens
        self._session_total["output_tokens"] += output_tokens

    def get_daily_usage(self, date: str = None) -> Dict[str, int]:
        """Get usage for a specific date."""
        if date is None:
            date = time.strftime("%Y-%m-%d")

        records = self._daily_records.get(date, [])

        return {
            "requests": len(records),
            "input_tokens": sum(r.input_tokens for r in records),
            "output_tokens": sum(r.output_tokens for r in records),
        }

    def get_session_usage(self) -> Dict[str, int]:
        """Get session usage."""
        return self._session_total.copy()

    def get_total_cost(self, pricing: Dict[str, Dict] = None) -> float:
        """Calculate total cost."""
        if pricing is None:
            # Default pricing (per 1M tokens)
            pricing = {
                "claude-opus-4-7": {"input": 15.0, "output": 75.0},
                "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
                "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
            }

        total_cost = 0.0

        for records in self._daily_records.values():
            for record in records:
                model_pricing = pricing.get(record.model, {"input": 3.0, "output": 15.0})
                input_cost = (record.input_tokens / 1_000_000) * model_pricing["input"]
                output_cost = (record.output_tokens / 1_000_000) * model_pricing["output"]
                total_cost += input_cost + output_cost

        return total_cost


# Global rate limiter
_limiter: Optional[RateLimiter] = None
_tracker: Optional[UsageTracker] = None


def get_rate_limiter(config: Optional[LimitConfig] = None) -> RateLimiter:
    """Get global rate limiter."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(config)
    return _limiter


def get_usage_tracker() -> UsageTracker:
    """Get global usage tracker."""
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker


__all__ = [
    "LimitType",
    "LimitConfig",
    "UsageRecord",
    "LimitStatus",
    "RateLimiter",
    "UsageTracker",
    "get_rate_limiter",
    "get_usage_tracker",
]