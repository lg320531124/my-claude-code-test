"""Billing - Usage and billing tracking."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class BillingTier(Enum):
    """Billing tiers."""
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class UsageType(Enum):
    """Usage types."""
    API_CALL = "api_call"
    TOKEN_INPUT = "token_input"
    TOKEN_OUTPUT = "token_output"
    STORAGE = "storage"
    FEATURE = "feature"


@dataclass
class UsageRecord:
    """Usage record."""
    type: UsageType
    amount: float
    timestamp: datetime
    model: Optional[str] = None
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BillingConfig:
    """Billing configuration."""
    tier: BillingTier = BillingTier.PRO
    budget_limit: Optional[float] = None
    alert_threshold: float = 0.8
    track_detailed: bool = True


@dataclass
class BillingSummary:
    """Billing summary."""
    period_start: datetime
    period_end: datetime
    total_cost: float
    total_tokens: int
    total_calls: int
    by_model: Dict[str, float] = field(default_factory=dict)
    by_type: Dict[str, float] = field(default_factory=dict)


class BillingManager:
    """Manage billing and usage."""

    def __init__(self, config: Optional[BillingConfig] = None):
        self.config = config or BillingConfig()
        self._usage: List[UsageRecord] = []
        self._alerts: List[Dict[str, Any]] = []

    async def record_usage(
        self,
        type: UsageType,
        amount: float,
        model: Optional[str] = None,
        cost: Optional[float] = None
    ) -> UsageRecord:
        """Record usage."""
        # Calculate cost if not provided
        if cost is None:
            cost = await self._calculate_cost(type, amount, model)

        record = UsageRecord(
            type=type,
            amount=amount,
            timestamp=datetime.now(),
            model=model,
            cost=cost,
        )

        self._usage.append(record)

        # Check budget
        if self.config.budget_limit:
            await self._check_budget()

        return record

    async def _calculate_cost(
        self,
        type: UsageType,
        amount: float,
        model: Optional[str]
    ) -> float:
        """Calculate cost."""
        # Pricing per million tokens
        pricing = {
            "claude-opus-4-7": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
            "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
        }

        if model and model in pricing:
            prices = pricing[model]

            if type == UsageType.TOKEN_INPUT:
                return (amount / 1_000_000) * prices["input"]
            elif type == UsageType.TOKEN_OUTPUT:
                return (amount / 1_000_000) * prices["output"]

        return 0.0

    async def _check_budget(self) -> None:
        """Check budget limit."""
        total = await self.get_total_cost()

        if self.config.budget_limit:
            percentage = total / self.config.budget_limit

            if percentage > self.config.alert_threshold:
                alert = {
                    "type": "budget_alert",
                    "percentage": percentage,
                    "total": total,
                    "limit": self.config.budget_limit,
                    "timestamp": datetime.now(),
                }

                self._alerts.append(alert)

                logger.warning(
                    f"Budget alert: {percentage:.1%} used "
                    f"({total:.2f} of {self.config.budget_limit:.2f})"
                )

    async def get_total_cost(self) -> float:
        """Get total cost."""
        return sum(r.cost for r in self._usage)

    async def get_total_tokens(self) -> Dict[str, int]:
        """Get total tokens."""
        input_tokens = sum(
            r.amount for r in self._usage
            if r.type == UsageType.TOKEN_INPUT
        )

        output_tokens = sum(
            r.amount for r in self._usage
            if r.type == UsageType.TOKEN_OUTPUT
        )

        return {"input": int(input_tokens), "output": int(output_tokens)}

    async def get_summary(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> BillingSummary:
        """Get billing summary."""
        use_start = start or datetime.min
        use_end = end or datetime.now()

        # Filter records
        records = [
            r for r in self._usage
            if use_start <= r.timestamp <= use_end
        ]

        # Calculate totals
        total_cost = sum(r.cost for r in records)
        total_tokens = sum(
            r.amount for r in records
            if r.type in [UsageType.TOKEN_INPUT, UsageType.TOKEN_OUTPUT]
        )
        total_calls = sum(
            1 for r in records
            if r.type == UsageType.API_CALL
        )

        # Group by model
        by_model: Dict[str, float] = {}
        for r in records:
            if r.model:
                by_model[r.model] = by_model.get(r.model, 0) + r.cost

        # Group by type
        by_type: Dict[str, float] = {}
        for r in records:
            key = r.type.value
            by_type[key] = by_type.get(key, 0) + r.cost

        return BillingSummary(
            period_start=use_start,
            period_end=use_end,
            total_cost=total_cost,
            total_tokens=int(total_tokens),
            total_calls=total_calls,
            by_model=by_model,
            by_type=by_type,
        )

    async def get_usage_history(
        self,
        limit: int = 100
    ) -> List[UsageRecord]:
        """Get usage history."""
        return self._usage[-limit:]

    async def clear_usage(self) -> int:
        """Clear usage records."""
        count = len(self._usage)
        self._usage.clear()
        return count

    async def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Estimate cost for tokens."""
        input_cost = await self._calculate_cost(
            UsageType.TOKEN_INPUT, input_tokens, model
        )
        output_cost = await self._calculate_cost(
            UsageType.TOKEN_OUTPUT, output_tokens, model
        )

        return input_cost + output_cost

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get budget alerts."""
        return self._alerts

    async def set_budget(self, limit: float) -> None:
        """Set budget limit."""
        self.config.budget_limit = limit

    async def set_tier(self, tier: BillingTier) -> None:
        """Set billing tier."""
        self.config.tier = tier


__all__ = [
    "BillingTier",
    "UsageType",
    "UsageRecord",
    "BillingConfig",
    "BillingSummary",
    "BillingManager",
]