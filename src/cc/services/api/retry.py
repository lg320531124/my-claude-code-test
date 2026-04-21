"""API Retry - Async retry logic for API calls."""

from __future__ import annotations
import asyncio
import time
from typing import Callable, Optional, TypeVar, Awaitable, List
from dataclasses import dataclass
from enum import Enum


class RetryReason(Enum):
    """Reasons for retry."""
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    OVERLOAD = "overload"


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: List[RetryReason] = [
        RetryReason.RATE_LIMIT,
        RetryReason.SERVER_ERROR,
        RetryReason.NETWORK_ERROR,
        RetryReason.OVERLOAD,
    ]


@dataclass
class RetryResult:
    """Result of retry attempt."""
    attempt: int
    success: bool
    error: Optional[str] = None
    delay: float = 0.0
    reason: Optional[RetryReason] = None


T = TypeVar("T")


class RetryHandler:
    """Handle retries for async operations."""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._retry_history: List[RetryResult] = []

    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        should_retry: Optional[Callable[[Exception], RetryReason]] = None,
    ) -> T:
        """Execute operation with retry logic."""
        attempt = 0
        last_error = None

        while attempt <= self.config.max_retries:
            try:
                result = await operation()
                self._retry_history.append(RetryResult(
                    attempt=attempt,
                    success=True,
                ))
                return result

            except Exception as e:
                last_error = e

                # Determine retry reason
                reason = None
                if should_retry:
                    reason = should_retry(e)
                else:
                    reason = self._classify_error(e)

                # Check if we should retry
                if reason is None or reason not in self.config.retry_on:
                    self._retry_history.append(RetryResult(
                        attempt=attempt,
                        success=False,
                        error=str(e),
                    ))
                    raise e

                # Calculate delay
                delay = self._calculate_delay(attempt, reason)

                self._retry_history.append(RetryResult(
                    attempt=attempt,
                    success=False,
                    error=str(e),
                    delay=delay,
                    reason=reason,
                ))

                # Wait before retry
                await asyncio.sleep(delay)
                attempt += 1

        # Max retries exceeded
        self._retry_history.append(RetryResult(
            attempt=attempt,
            success=False,
            error=str(last_error),
        ))
        raise last_error

    def _classify_error(self, error: Exception) -> Optional[RetryReason]:
        """Classify error for retry decision."""
        error_str = str(error).lower()

        # Rate limit errors
        if "rate limit" in error_str or "429" in error_str:
            return RetryReason.RATE_LIMIT

        # Server errors
        if "500" in error_str or "502" in error_str or "503" in error_str:
            return RetryReason.SERVER_ERROR

        # Overload
        if "overload" in error_str or "too many requests" in error_str:
            return RetryReason.OVERLOAD

        # Network errors
        if "connection" in error_str or "network" in error_str or "timeout" in error_str:
            return RetryReason.NETWORK_ERROR

        return None

    def _calculate_delay(self, attempt: int, reason: RetryReason) -> float:
        """Calculate delay for retry."""
        # Base exponential delay
        delay = self.config.initial_delay * (self.config.exponential_base ** attempt)

        # Special handling for rate limits
        if reason == RetryReason.RATE_LIMIT:
            # Use longer delay for rate limits
            delay = max(delay, 30.0)

        # Cap at max delay
        delay = min(delay, self.config.max_delay)

        # Add jitter
        if self.config.jitter:
            delay = delay * (0.5 + asyncio.get_event_loop().time() % 0.5)

        return delay

    def get_history(self) -> List[RetryResult]:
        """Get retry history."""
        return self._retry_history.copy()

    def clear_history(self) -> None:
        """Clear retry history."""
        self._retry_history.clear()


class AdaptiveRetry(RetryHandler):
    """Adaptive retry with learning."""

    def __init__(self, config: Optional[RetryConfig] = None):
        super().__init__(config)
        self._success_times: List[float] = []
        self._failure_times: List[float] = []
        self._adaptive_delay: float = self.config.initial_delay

    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        should_retry: Optional[Callable[[Exception], RetryReason]] = None,
    ) -> T:
        """Execute with adaptive retry."""
        start_time = time.time()

        try:
            result = await super().execute_with_retry(operation, should_retry)
            self._success_times.append(time.time() - start_time)
            self._update_adaptive_delay()
            return result

        except Exception:
            self._failure_times.append(time.time() - start_time)
            self._update_adaptive_delay()
            raise

    def _update_adaptive_delay(self) -> None:
        """Update adaptive delay based on history."""
        if len(self._success_times) < 5:
            return

        # Calculate average success time
        sum(self._success_times[-10:]) / len(self._success_times[-10:])

        # Adjust delay based on success rate
        recent_success = len([t for t in self._success_times[-10:] if t < 5])
        recent_failure = len(self._failure_times[-10:]) if self._failure_times else 0

        success_rate = recent_success / (recent_success + recent_failure) if (recent_success + recent_failure) > 0 else 1.0

        if success_rate > 0.8:
            # High success rate, reduce delay
            self._adaptive_delay = max(0.5, self._adaptive_delay * 0.9)
        elif success_rate < 0.5:
            # Low success rate, increase delay
            self._adaptive_delay = min(self.config.max_delay, self._adaptive_delay * 1.5)

    def _calculate_delay(self, attempt: int, reason: RetryReason) -> float:
        """Use adaptive delay."""
        base_delay = super()._calculate_delay(attempt, reason)
        return max(base_delay, self._adaptive_delay)


async def retry_with_backoff(
    operation: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> T:
    """Simple retry with exponential backoff."""
    handler = RetryHandler(RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
    ))
    return await handler.execute_with_retry(operation)


__all__ = [
    "RetryReason",
    "RetryConfig",
    "RetryResult",
    "RetryHandler",
    "AdaptiveRetry",
    "retry_with_backoff",
]