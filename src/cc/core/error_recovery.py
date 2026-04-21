"""Error Recovery - Error recovery and retry logic."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, Callable, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..utils.log import get_logger

logger = get_logger(__name__)


T = TypeVar("T")


class ErrorType(Enum):
    """Error types."""
    NETWORK = "network"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    VALIDATION = "validation"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    CIRCUIT_BREAK = "circuit_break"


@dataclass
class ErrorInfo:
    """Error information."""
    type: ErrorType
    message: str
    code: Optional[str] = None
    retryable: bool = True
    timestamp: datetime = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryConfig:
    """Recovery configuration."""
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0
    circuit_break_threshold: int = 5
    circuit_break_timeout: float = 30.0
    fallback_enabled: bool = True


@dataclass
class RecoveryState:
    """Recovery state."""
    consecutive_failures: int = 0
    circuit_open: bool = False
    circuit_open_until: float = 0.0
    last_error: Optional[ErrorInfo] = None
    total_retries: int = 0


class ErrorRecovery:
    """Error recovery handler."""

    def __init__(self, config: Optional[RecoveryConfig] = None):
        self.config = config or RecoveryConfig()
        self._state = RecoveryState()
        self._fallbacks: Dict[str, Callable] = {}
        self._error_handlers: Dict[ErrorType, Callable] = {}

    async def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorInfo:
        """Handle error."""
        # Classify error
        error_type = self._classify_error(error)

        # Create error info
        info = ErrorInfo(
            type=error_type,
            message=str(error),
            retryable=self._is_retryable(error_type),
            timestamp=datetime.now(),
            context=context or {},
        )

        # Update state
        self._state.last_error = info
        self._state.consecutive_failures += 1

        # Check circuit breaker
        if self._state.consecutive_failures >= self.config.circuit_break_threshold:
            self._open_circuit_breaker()

        # Call error handler if registered
        if error_type in self._error_handlers:
            try:
                await self._error_handlers[error_type](info)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")

        logger.error(f"Error: {error_type.value} - {error}")
        return info

    def _classify_error(
        self,
        error: Exception
    ) -> ErrorType:
        """Classify error type."""
        error_name = type(error).__name__

        if "Timeout" in error_name:
            return ErrorType.TIMEOUT
        elif "Network" in error_name or "Connection" in error_name:
            return ErrorType.NETWORK
        elif "RateLimit" in error_name or "TooManyRequests" in error_name:
            return ErrorType.RATE_LIMIT
        elif "Auth" in error_name or "Unauthorized" in error_name:
            return ErrorType.AUTH
        elif "Validation" in error_name or "Invalid" in error_name:
            return ErrorType.VALIDATION
        else:
            return ErrorType.UNKNOWN

    def _is_retryable(
        self,
        error_type: ErrorType
    ) -> bool:
        """Check if error is retryable."""
        retryable_types = [
            ErrorType.NETWORK,
            ErrorType.TIMEOUT,
            ErrorType.RATE_LIMIT,
        ]

        return error_type in retryable_types

    async def retry(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Retry function with backoff."""
        # Check circuit breaker
        if self._state.circuit_open:
            if asyncio.get_event_loop().time() < self._state.circuit_open_until:
                raise Exception("Circuit breaker open")

            # Half-open state
            self._state.circuit_open = False

        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                result = await func(*args, **kwargs)

                # Success - reset state
                self._state.consecutive_failures = 0
                self._state.total_retries += attempt

                return result

            except Exception as e:
                last_error = e
                info = await self.handle_error(e)

                if not info.retryable:
                    raise

                # Calculate delay
                delay = min(
                    self.config.retry_delay * (self.config.backoff_factor ** attempt),
                    self.config.max_delay
                )

                logger.info(f"Retry attempt {attempt + 1} after {delay}s")

                await asyncio.sleep(delay)

        # All retries failed
        raise last_error or Exception("Max retries exceeded")

    async def fallback(
        self,
        func_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute fallback function."""
        if not self.config.fallback_enabled:
            raise Exception("Fallback disabled")

        fallback_func = self._fallbacks.get(func_name)

        if not fallback_func:
            raise Exception(f"No fallback for {func_name}")

        try:
            return await fallback_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fallback failed: {e}")
            raise

    def register_fallback(
        self,
        func_name: str,
        fallback: Callable
    ) -> None:
        """Register fallback function."""
        self._fallbacks[func_name] = fallback

    def register_handler(
        self,
        error_type: ErrorType,
        handler: Callable
    ) -> None:
        """Register error handler."""
        self._error_handlers[error_type] = handler

    def _open_circuit_breaker(self) -> None:
        """Open circuit breaker."""
        self._state.circuit_open = True
        self._state.circuit_open_until = (
            asyncio.get_event_loop().time() + self.config.circuit_break_timeout
        )

        logger.warning("Circuit breaker opened")

    async def close_circuit_breaker(self) -> None:
        """Close circuit breaker."""
        self._state.circuit_open = False
        self._state.circuit_open_until = 0.0
        self._state.consecutive_failures = 0

        logger.info("Circuit breaker closed")

    def get_state(self) -> RecoveryState:
        """Get current state."""
        return self._state

    async def reset(self) -> None:
        """Reset state."""
        self._state = RecoveryState()

    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self._state.circuit_open:
            return False

        return asyncio.get_event_loop().time() < self._state.circuit_open_until


__all__ = [
    "ErrorType",
    "RecoveryStrategy",
    "ErrorInfo",
    "RecoveryConfig",
    "RecoveryState",
    "ErrorRecovery",
]