"""Rate Limiter Service - Rate limiting."""

from __future__ import annotations
import time
from typing import Dict, Optional
from pydantic import BaseModel, Field


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""
    requests_per_minute: int = Field(default=60, description="Requests per minute")
    requests_per_hour: int = Field(default=1000, description="Requests per hour")
    burst_size: int = Field(default=10, description="Burst size for token bucket")


class RateLimitResult(BaseModel):
    """Rate limit check result."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None


class RateLimiterService:
    """Rate limiting service."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._requests: Dict[str, list] = {}  # client_id -> timestamps

    def check(self, client_id: str) -> RateLimitResult:
        """Check if request is allowed."""
        now = time.time()

        # Get or create request history
        if client_id not in self._requests:
            self._requests[client_id] = []

        requests = self._requests[client_id]

        # Clean old requests (older than 1 minute)
        requests = [t for t in requests if now - t < 60]
        self._requests[client_id] = requests

        # Check minute limit
        minute_requests = len(requests)
        minute_remaining = self.config.requests_per_minute - minute_requests

        # Check burst
        recent_requests = [t for t in requests if now - t < 1]
        burst_remaining = self.config.burst_size - len(recent_requests)

        # Determine if allowed
        allowed = minute_remaining > 0 and burst_remaining > 0
        remaining = max(0, min(minute_remaining, burst_remaining))

        # Calculate reset time (when minute window resets)
        if requests:
            oldest = min(requests)
            reset_time = oldest + 60
        else:
            reset_time = now + 60

        # Retry after if not allowed
        retry_after = None
        if not allowed:
            retry_after = reset_time - now

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after,
        )

    def record(self, client_id: str) -> None:
        """Record a request."""
        now = time.time()
        if client_id not in self._requests:
            self._requests[client_id] = []
        self._requests[client_id].append(now)

    def reset(self, client_id: str) -> None:
        """Reset rate limit for client."""
        self._requests.pop(client_id, None)

    def get_stats(self, client_id: str) -> Dict:
        """Get rate limit stats."""
        now = time.time()
        requests = self._requests.get(client_id, [])

        minute_requests = len([t for t in requests if now - t < 60])
        hour_requests = len([t for t in requests if now - t < 3600])

        return {
            "client_id": client_id,
            "requests_last_minute": minute_requests,
            "requests_last_hour": hour_requests,
            "minute_limit": self.config.requests_per_minute,
            "hour_limit": self.config.requests_per_hour,
            "minute_remaining": self.config.requests_per_minute - minute_requests,
        }


# Singleton
_rate_limiter: Optional[RateLimiterService] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiterService:
    """Get rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiterService(config)
    return _rate_limiter


def check_rate(client_id: str) -> RateLimitResult:
    """Convenience rate check."""
    return get_rate_limiter().check(client_id)


__all__ = [
    "RateLimitConfig",
    "RateLimitResult",
    "RateLimiterService",
    "get_rate_limiter",
    "check_rate",
]