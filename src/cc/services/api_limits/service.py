"""API Limits Service - Handle API usage limits."""

from __future__ import annotations
import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class LimitType(Enum):
    """Limit types."""
    REQUESTS = "requests"
    TOKENS = "tokens"
    CONCURRENT = "concurrent"
    COST = "cost"


class LimitStatus(Enum):
    """Limit status."""
    OK = "ok"
    WARNING = "warning"
    LIMIT = "limit"
    BLOCKED = "blocked"


@dataclass
class UsageLimit:
    """Usage limit configuration."""
    type: LimitType
    max_value: int
    current_value: int = 0
    warning_threshold: float = 0.8
    unit: str = ""


@dataclass
class LimitConfig:
    """Limits configuration."""
    limits: List[UsageLimit] = field(default_factory=list)
    notify_on_warning: bool = True
    notify_on_limit: bool = True
    auto_reset: bool = True
    reset_interval: float = 3600.0


@dataclass
class LimitState:
    """Limit tracking state."""
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    concurrent: int = 0
    last_reset: float = 0.0


class APILimitsService:
    """Service for tracking and managing API limits."""

    def __init__(self, config: Optional[LimitConfig] = None):
        self.config = config or LimitConfig()
        self._state = LimitState(last_reset=time.time())
        self._limits: Dict[LimitType, UsageLimit] = {}
        self._warnings_sent: set = set()
        self._callbacks: Dict[LimitStatus, List[callable]] = {}

        # Initialize default limits
        self._init_limits()

    def _init_limits(self) -> None:
        """Initialize default limits."""
        defaults = [
            UsageLimit(LimitType.REQUESTS, 1000),
            UsageLimit(LimitType.TOKENS, 200000, unit="tokens"),
            UsageLimit(LimitType.CONCURRENT, 10),
            UsageLimit(LimitType.COST, 100, unit="USD"),
        ]

        for limit in defaults:
            self._limits[limit.type] = limit

    async def check_limits(self) -> Dict[LimitType, LimitStatus]:
        """Check all limits status."""
        status: Dict[LimitType, LimitStatus] = {}

        for limit_type, limit in self._limits.items():
            current = self._get_current_value(limit_type)
            limit.current_value = current

            ratio = current / limit.max_value

            if ratio >= 1.0:
                status[limit_type] = LimitStatus.BLOCKED
            elif ratio >= limit.warning_threshold:
                status[limit_type] = LimitStatus.WARNING
            else:
                status[limit_type] = LimitStatus.OK

            # Send notifications
            if status[limit_type] == LimitStatus.WARNING:
                if limit_type not in self._warnings_sent:
                    await self._notify_warning(limit_type, current, limit.max_value)
                    self._warnings_sent.add(limit_type)

            elif status[limit_type] == LimitStatus.BLOCKED:
                await self._notify_blocked(limit_type, current, limit.max_value)

        return status

    def _get_current_value(self, limit_type: LimitType) -> int:
        """Get current value for limit type."""
        if limit_type == LimitType.REQUESTS:
            return self._state.requests
        elif limit_type == LimitType.TOKENS:
            return self._state.input_tokens + self._state.output_tokens
        elif limit_type == LimitType.CONCURRENT:
            return self._state.concurrent
        elif limit_type == LimitType.COST:
            return int(self._state.total_cost)
        return 0

    async def record_usage(
        self,
        requests: int = 1,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0
    ) -> Dict[LimitType, LimitStatus]:
        """Record API usage."""
        self._state.requests += requests
        self._state.input_tokens += input_tokens
        self._state.output_tokens += output_tokens
        self._state.total_cost += cost

        return await self.check_limits()

    async def record_concurrent_start(self) -> bool:
        """Record start of concurrent request."""
        self._state.concurrent += 1
        status = await self.check_limits()

        if status.get(LimitType.CONCURRENT) == LimitStatus.BLOCKED:
            self._state.concurrent -= 1
            return False

        return True

    async def record_concurrent_end(self) -> None:
        """Record end of concurrent request."""
        self._state.concurrent = max(0, self._state.concurrent - 1)

    async def _notify_warning(
        self,
        limit_type: LimitType,
        current: int,
        max_value: int
    ) -> None:
        """Send warning notification."""
        if self.config.notify_on_warning:
            logger.warning(
                f"Limit warning: {limit_type.value} at {current}/{max_value}"
            )

            await self._call_callbacks(LimitStatus.WARNING, {
                "type": limit_type,
                "current": current,
                "max": max_value,
            })

    async def _notify_blocked(
        self,
        limit_type: LimitType,
        current: int,
        max_value: int
    ) -> None:
        """Send blocked notification."""
        if self.config.notify_on_limit:
            logger.error(
                f"Limit reached: {limit_type.value} at {current}/{max_value}"
            )

            await self._call_callbacks(LimitStatus.BLOCKED, {
                "type": limit_type,
                "current": current,
                "max": max_value,
            })

    async def _call_callbacks(
        self,
        status: LimitStatus,
        data: Dict[str, Any]
    ) -> None:
        """Call registered callbacks."""
        callbacks = self._callbacks.get(status, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def reset(self) -> None:
        """Reset all counters."""
        self._state = LimitState(last_reset=time.time())
        self._warnings_sent.clear()

        logger.info("Limits reset")

    async def _check_auto_reset(self) -> None:
        """Check if auto reset is needed."""
        if not self.config.auto_reset:
            return

        elapsed = time.time() - self._state.last_reset

        if elapsed >= self.config.reset_interval:
            await self.reset()

    async def get_usage_report(self) -> Dict[str, Any]:
        """Get usage report."""
        status = await self.check_limits()

        return {
            "requests": {
                "used": self._state.requests,
                "limit": self._limits.get(LimitType.REQUESTS).max_value,
                "status": status.get(LimitType.REQUESTS).value,
            },
            "tokens": {
                "input": self._state.input_tokens,
                "output": self._state.output_tokens,
                "total": self._state.input_tokens + self._state.output_tokens,
                "limit": self._limits.get(LimitType.TOKENS).max_value,
                "status": status.get(LimitType.TOKENS).value,
            },
            "cost": {
                "total": self._state.total_cost,
                "limit": self._limits.get(LimitType.COST).max_value,
                "status": status.get(LimitType.COST).value,
            },
            "concurrent": {
                "current": self._state.concurrent,
                "limit": self._limits.get(LimitType.CONCURRENT).max_value,
            },
        }

    def register_callback(
        self,
        status: LimitStatus,
        callback: callable
    ) -> None:
        """Register callback for limit status."""
        if status not in self._callbacks:
            self._callbacks[status] = []

        self._callbacks[status].append(callback)

    def set_limit(
        self,
        limit_type: LimitType,
        max_value: int
    ) -> None:
        """Set limit value."""
        if limit_type in self._limits:
            self._limits[limit_type].max_value = max_value
        else:
            self._limits[limit_type] = UsageLimit(limit_type, max_value)

    async def is_allowed(self) -> bool:
        """Check if API calls are allowed."""
        status = await self.check_limits()

        return all(
            s != LimitStatus.BLOCKED
            for s in status.values()
        )


__all__ = [
    "LimitType",
    "LimitStatus",
    "UsageLimit",
    "LimitConfig",
    "LimitState",
    "APILimitsService",
]