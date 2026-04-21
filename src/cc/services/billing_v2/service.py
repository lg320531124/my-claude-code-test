"""Billing Service - Track and manage billing."""

from __future__ import annotations
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


class PricingModel(Enum):
    """Pricing models."""
    PER_REQUEST = "per_request"
    PER_TOKEN = "per_token"
    PER_MONTH = "per_month"
    HYBRID = "hybrid"


@dataclass
class PricingInfo:
    """Pricing information."""
    input_token_price: float = 0.003  # per 1K tokens
    output_token_price: float = 0.015  # per 1K tokens
    request_price: float = 0.0
    monthly_price: float = 0.0
    included_tokens: int = 0
    included_requests: int = 0


@dataclass
class UsageRecord:
    """Usage record."""
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    requests: int
    model: str
    cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BillingConfig:
    """Billing configuration."""
    tier: BillingTier = BillingTier.PRO
    pricing: PricingModel = PricingModel.PER_TOKEN
    track_usage: bool = True
    alert_threshold: float = 100.0
    budget_limit: Optional[float] = None


@dataclass
class BillingState:
    """Billing state."""
    total_cost: float = 0.0
    total_tokens: int = 0
    total_requests: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class BillingService:
    """Service for billing management."""

    # Pricing by model
    MODEL_PRICING: Dict[str, PricingInfo] = {
        "claude-opus-4-7": PricingInfo(
            input_token_price=0.015,
            output_token_price=0.075,
        ),
        "claude-sonnet-4-6": PricingInfo(
            input_token_price=0.003,
            output_token_price=0.015,
        ),
        "claude-haiku-4-5": PricingInfo(
            input_token_price=0.001,
            output_token_price=0.005,
        ),
    }

    def __init__(self, config: Optional[BillingConfig] = None):
        self.config = config or BillingConfig()
        self._state = BillingState(period_start=datetime.now())
        self._records: List[UsageRecord] = []
        self._alerts_sent: set = set()

    async def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for usage."""
        pricing = self.MODEL_PRICING.get(model, PricingInfo())

        input_cost = (input_tokens / 1000) * pricing.input_token_price
        output_cost = (output_tokens / 1000) * pricing.output_token_price

        return input_cost + output_cost

    async def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        requests: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """Record usage."""
        # Calculate cost
        cost = await self.calculate_cost(model, input_tokens, output_tokens)

        # Create record
        record = UsageRecord(
            timestamp=datetime.now(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            requests=requests,
            model=model,
            cost=cost,
            metadata=metadata or {},
        )

        # Update state
        self._state.total_cost += cost
        self._state.total_tokens += input_tokens + output_tokens
        self._state.total_requests += requests

        # Store record
        if self.config.track_usage:
            self._records.append(record)

        # Check alerts
        await self._check_alerts()

        logger.debug(f"Recorded usage: {cost:.4f} USD")
        return record

    async def _check_alerts(self) -> None:
        """Check for billing alerts."""
        # Budget alert
        if self.config.budget_limit:
            if self._state.total_cost >= self.config.budget_limit:
                if "budget" not in self._alerts_sent:
                    logger.warning(f"Budget limit reached: ${self._state.total_cost:.2f}")
                    self._alerts_sent.add("budget")

        # Threshold alert
        if self._state.total_cost >= self.config.alert_threshold:
            threshold_key = f"threshold_{int(self._state.total_cost)}"
            if threshold_key not in self._alerts_sent:
                logger.warning(f"Cost threshold: ${self._state.total_cost:.2f}")
                self._alerts_sent.add(threshold_key)

    async def get_current_cost(self) -> float:
        """Get current period cost."""
        return self._state.total_cost

    async def get_usage_report(self) -> Dict[str, Any]:
        """Get usage report."""
        # Calculate by model
        by_model: Dict[str, Dict[str, Any]] = {}
        for record in self._records:
            if record.model not in by_model:
                by_model[record.model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "requests": 0,
                    "cost": 0.0,
                }

            by_model[record.model]["input_tokens"] += record.input_tokens
            by_model[record.model]["output_tokens"] += record.output_tokens
            by_model[record.model]["requests"] += record.requests
            by_model[record.model]["cost"] += record.cost

        return {
            "tier": self.config.tier.value,
            "total_cost": self._state.total_cost,
            "total_tokens": self._state.total_tokens,
            "total_requests": self._state.total_requests,
            "period_start": self._state.period_start.isoformat() if self._state.period_start else None,
            "by_model": by_model,
            "budget_limit": self.config.budget_limit,
            "budget_remaining": (
                self.config.budget_limit - self._state.total_cost
                if self.config.budget_limit else None
            ),
        }

    async def estimate_cost(
        self,
        model: str,
        input_tokens_estimate: int,
        output_tokens_estimate: int
    ) -> Dict[str, float]:
        """Estimate cost for planned usage."""
        pricing = self.MODEL_PRICING.get(model, PricingInfo())

        input_cost = (input_tokens_estimate / 1000) * pricing.input_token_price
        output_cost = (output_tokens_estimate / 1000) * pricing.output_token_price
        total_cost = input_cost + output_cost

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
        }

    async def reset_period(self) -> None:
        """Reset billing period."""
        self._state = BillingState(period_start=datetime.now())
        self._alerts_sent.clear()
        logger.info("Billing period reset")

    async def get_records(
        self,
        limit: int = 100
    ) -> List[UsageRecord]:
        """Get usage records."""
        return self._records[-limit:]

    async def clear_records(self) -> int:
        """Clear old records."""
        count = len(self._records)
        self._records.clear()
        return count

    async def set_budget(self, limit: float) -> None:
        """Set budget limit."""
        self.config.budget_limit = limit
        logger.info(f"Budget limit set to ${limit:.2f}")

    async def get_pricing(self, model: str) -> PricingInfo:
        """Get pricing for model."""
        return self.MODEL_PRICING.get(model, PricingInfo())


__all__ = [
    "BillingTier",
    "PricingModel",
    "PricingInfo",
    "UsageRecord",
    "BillingConfig",
    "BillingState",
    "BillingService",
]