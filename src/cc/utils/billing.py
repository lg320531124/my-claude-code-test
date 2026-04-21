"""Billing Service - Cost calculation and tracking."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


# Pricing per 1M tokens (USD)
MODEL_PRICING = {
    "claude-opus-4-7": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.5},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.3},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0, "cache_write": 1.0, "cache_read": 0.08},
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}


@dataclass
class UsageRecord:
    """Usage record."""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    request_id: str = ""
    cost: float = 0.0


@dataclass
class CostBreakdown:
    """Cost breakdown."""
    input_cost: float
    output_cost: float
    cache_read_cost: float = 0.0
    cache_write_cost: float = 0.0
    total: float


@dataclass
class BillingSummary:
    """Billing summary."""
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    by_model: Dict[str, CostBreakdown]
    by_day: Dict[str, float]
    period_start: datetime
    period_end: datetime


class BillingCalculator:
    """Calculate API costs."""

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> CostBreakdown:
        """Calculate cost for token usage."""
        pricing = MODEL_PRICING.get(model, {"input": 3.0, "output": 15.0})

        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 3.0)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 15.0)

        cache_read_cost = 0.0
        if cache_read_tokens > 0 and "cache_read" in pricing:
            cache_read_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read"]

        cache_write_cost = 0.0
        if cache_write_tokens > 0 and "cache_write" in pricing:
            cache_write_cost = (cache_write_tokens / 1_000_000) * pricing["cache_write"]

        total = input_cost + output_cost + cache_read_cost + cache_write_cost

        return CostBreakdown(
            input_cost=input_cost,
            output_cost=output_cost,
            cache_read_cost=cache_read_cost,
            cache_write_cost=cache_write_cost,
            total=total,
        )

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model."""
        return MODEL_PRICING.get(model, {"input": 3.0, "output": 15.0})


class BillingTracker:
    """Track billing usage."""

    def __init__(self):
        self._records: List[...] = field(default_factory=list)
        self._session_total: Dict[str, int] = {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
        }
        self._calculator = BillingCalculator()

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        request_id: str = "",
    ) -> UsageRecord:
        """Record token usage."""
        cost = self._calculator.calculate_cost(
            model, input_tokens, output_tokens,
            cache_read_tokens, cache_write_tokens,
        )

        record = UsageRecord(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            request_id=request_id,
            cost=cost.total,
        )

        self._records.append(record)

        # Update session totals
        self._session_total["requests"] += 1
        self._session_total["input_tokens"] += input_tokens
        self._session_total["output_tokens"] += output_tokens
        self._session_total["cost"] += cost.total

        return record

    def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        return self._session_total.copy()

    def get_summary(
        self,
        period_start: datetime = None,
        period_end: datetime = None,
    ) -> BillingSummary:
        """Get billing summary."""
        records = self._records

        if period_start:
            records = [r for r in records if r.timestamp >= period_start]
        if period_end:
            records = [r for r in records if r.timestamp <= period_end]

        if not records:
            return BillingSummary(
                total_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_cost=0.0,
                by_model={},
                by_day={},
                period_start=period_start or datetime.min,
                period_end=period_end or datetime.max,
            )

        # Aggregate by model
        by_model: Dict[str, CostBreakdown] = field(default_factory=dict)
        for record in records:
            if record.model not in by_model:
                by_model[record.model] = CostBreakdown(
                    input_cost=0.0,
                    output_cost=0.0,
                    total=0.0,
                )

            cost = self._calculator.calculate_cost(
                record.model,
                record.input_tokens,
                record.output_tokens,
                record.cache_read_tokens,
                record.cache_write_tokens,
            )

            by_model[record.model].input_cost += cost.input_cost
            by_model[record.model].output_cost += cost.output_cost
            by_model[record.model].total += cost.total

        # Aggregate by day
        by_day: Dict[str, float] = field(default_factory=dict)
        for record in records:
            day = record.timestamp.strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0.0) + record.cost

        return BillingSummary(
            total_requests=len(records),
            total_input_tokens=sum(r.input_tokens for r in records),
            total_output_tokens=sum(r.output_tokens for r in records),
            total_cost=sum(r.cost for r in records),
            by_model=by_model,
            by_day=by_day,
            period_start=min(r.timestamp for r in records),
            period_end=max(r.timestamp for r in records),
        )

    def get_records(self) -> List[UsageRecord]:
        """Get all records."""
        return self._records.copy()

    def clear_records(self) -> None:
        """Clear records."""
        self._records.clear()


class BudgetManager:
    """Manage API budget."""

    def __init__(self, budget_limit: float = 100.0):
        self.budget_limit = budget_limit
        self._tracker = BillingTracker()
        self._warnings: List[...] = field(default_factory=list)

    def check_budget(self) -> Dict[str, Any]:
        """Check budget status."""
        summary = self._tracker.get_session_summary()
        used = summary["cost"]
        remaining = self.budget_limit - used

        percentage_used = used / self.budget_limit if self.budget_limit > 0 else 0

        return {
            "budget_limit": self.budget_limit,
            "used": used,
            "remaining": remaining,
            "percentage_used": percentage_used,
            "is_exceeded": used > self.budget_limit,
            "is_near_limit": percentage_used > 0.8,
        }

    def should_warn(self) -> bool:
        """Check if should warn about budget."""
        status = self.check_budget()
        return status["is_near_limit"]

    def get_warning_message(self) -> Optional[str]:
        """Get budget warning message."""
        status = self.check_budget()

        if status["is_exceeded"]:
            return f"Budget exceeded: ${status['used']:.2f} used of ${status['budget_limit']:.2f} limit"

        if status["is_near_limit"]:
            return f"Budget warning: ${status['used']:.2f} used ({status['percentage_used']*100:.0f}%)"

        return None

    def record_usage(self, *args, **kwargs) -> UsageRecord:
        """Record usage."""
        record = self._tracker.record(*args, **kwargs)
        return record


# Global tracker
_tracker: Optional[BillingTracker] = None


def get_billing_tracker() -> BillingTracker:
    """Get global billing tracker."""
    global _tracker
    if _tracker is None:
        _tracker = BillingTracker()
    return _tracker


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for usage."""
    calculator = BillingCalculator()
    breakdown = calculator.calculate_cost(model, input_tokens, output_tokens)
    return breakdown.total


__all__ = [
    "MODEL_PRICING",
    "UsageRecord",
    "CostBreakdown",
    "BillingSummary",
    "BillingCalculator",
    "BillingTracker",
    "BudgetManager",
    "get_billing_tracker",
    "calculate_cost",
]