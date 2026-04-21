"""Policy Limits - Check and enforce policy limits."""

from __future__ import annotations
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class LimitType(Enum):
    """Limit types."""
    TOKENS = "tokens"
    COST = "cost"
    REQUESTS = "requests"
    FILES = "files"
    TIME = "time"
    CONCURRENT = "concurrent"


@dataclass
class PolicyLimit:
    """Policy limit configuration."""
    type: LimitType
    max_value: float
    current_value: float = 0.0
    period: str = "daily"  # daily, hourly, session, total
    enabled: bool = True


@dataclass
class LimitCheck:
    """Limit check result."""
    type: LimitType
    within_limit: bool
    current: float
    max: float
    remaining: float
    message: str = ""


class PolicyLimitsService:
    """Service for policy limit checking."""
    
    def __init__(self):
        self._limits: Dict[LimitType, PolicyLimit] = {
            LimitType.TOKENS: PolicyLimit(
                type=LimitType.TOKENS,
                max_value=1000000,
                period="daily",
            ),
            LimitType.COST: PolicyLimit(
                type=LimitType.COST,
                max_value=50.0,
                period="daily",
            ),
            LimitType.REQUESTS: PolicyLimit(
                type=LimitType.REQUESTS,
                max_value=1000,
                period="hourly",
            ),
            LimitType.FILES: PolicyLimit(
                type=LimitType.FILES,
                max_value=100,
                period="session",
            ),
            LimitType.CONCURRENT: PolicyLimit(
                type=LimitType.CONCURRENT,
                max_value=5,
                period="session",
            ),
        }
    
    def set_limit(self, limit: PolicyLimit) -> None:
        """Set limit."""
        self._limits[limit.type] = limit
    
    def get_limit(self, type: LimitType) -> Optional[PolicyLimit]:
        """Get limit."""
        return self._limits.get(type)
    
    def check(self, type: LimitType, current: float = None) -> LimitCheck:
        """Check if within limit."""
        limit = self._limits.get(type)
        
        if not limit or not limit.enabled:
            return LimitCheck(
                type=type,
                within_limit=True,
                current=current or 0,
                max=float('inf'),
                remaining=float('inf'),
                message="No limit configured",
            )
        
        current_value = current if current is not None else limit.current_value
        within = current_value <= limit.max_value
        remaining = limit.max_value - current_value
        
        if within:
            message = f"Within limit ({remaining:.1f} remaining)"
        else:
            message = f"Exceeded limit by {abs(remaining):.1f}"
        
        return LimitCheck(
            type=type,
            within_limit=within,
            current=current_value,
            max=limit.max_value,
            remaining=remaining,
            message=message,
        )
    
    def update_usage(self, type: LimitType, value: float) -> None:
        """Update usage."""
        if type in self._limits:
            self._limits[type].current_value += value
    
    def reset(self, type: LimitType) -> None:
        """Reset limit."""
        if type in self._limits:
            self._limits[type].current_value = 0
    
    def reset_all(self) -> None:
        """Reset all limits."""
        for limit in self._limits.values():
            limit.current_value = 0
    
    def get_all_checks(self) -> Dict[LimitType, LimitCheck]:
        """Get all limit checks."""
        return {
            type: self.check(type)
            for type in self._limits.keys()
        }


# Global service
_policy_limits: Optional[PolicyLimitsService] = None


def get_policy_limits() -> PolicyLimitsService:
    """Get global policy limits service."""
    global _policy_limits
    if _policy_limits is None:
        _policy_limits = PolicyLimitsService()
    return _policy_limits


def check_limit(type: LimitType, current: float = None) -> LimitCheck:
    """Check limit."""
    return get_policy_limits().check(type, current)


__all__ = [
    "LimitType",
    "PolicyLimit",
    "LimitCheck",
    "PolicyLimitsService",
    "get_policy_limits",
    "check_limit",
]
