"""Tests for billing service."""

import pytest
from src.cc.services.billing_v2 import (
    BillingService,
    BillingConfig,
    BillingTier,
    PricingModel,
    PricingInfo,
    UsageRecord,
)


@pytest.mark.asyncio
async def test_billing_service_init():
    """Test billing service initialization."""
    service = BillingService()
    assert service.config is not None
    assert service._state is not None


@pytest.mark.asyncio
async def test_calculate_cost():
    """Test cost calculation."""
    service = BillingService()

    cost = await service.calculate_cost(
        "claude-sonnet-4-6",
        input_tokens=1000,
        output_tokens=500
    )

    # 1000 * 0.003/1000 + 500 * 0.015/1000 = 0.003 + 0.0075 = 0.0105
    assert cost == pytest.approx(0.0105)


@pytest.mark.asyncio
async def test_record_usage():
    """Test recording usage."""
    service = BillingService()

    record = await service.record_usage(
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=50,
    )

    assert record.model == "claude-sonnet-4-6"
    assert record.input_tokens == 100
    assert record.output_tokens == 50


@pytest.mark.asyncio
async def test_get_current_cost():
    """Test getting current cost."""
    service = BillingService()

    await service.record_usage(
        model="claude-sonnet-4-6",
        input_tokens=1000,
        output_tokens=500,
    )

    cost = await service.get_current_cost()
    assert cost > 0


@pytest.mark.asyncio
async def test_get_usage_report():
    """Test getting usage report."""
    service = BillingService()

    await service.record_usage("claude-sonnet-4-6", 100, 50)
    await service.record_usage("claude-haiku-4-5", 200, 100)

    report = await service.get_usage_report()

    assert report["total_requests"] == 2
    assert "by_model" in report


@pytest.mark.asyncio
async def test_estimate_cost():
    """Test cost estimation."""
    service = BillingService()

    estimate = await service.estimate_cost(
        "claude-sonnet-4-6",
        input_tokens_estimate=10000,
        output_tokens_estimate=5000,
    )

    assert "total_cost" in estimate
    assert estimate["total_cost"] > 0


@pytest.mark.asyncio
async def test_budget_limit():
    """Test budget limit."""
    config = BillingConfig(budget_limit=1.0)
    service = BillingService(config)

    await service.set_budget(0.5)

    assert service.config.budget_limit == 0.5


@pytest.mark.asyncio
async def test_billing_config():
    """Test billing config."""
    config = BillingConfig(
        tier=BillingTier.PRO,
        pricing=PricingModel.PER_TOKEN,
        track_usage=True,
        budget_limit=100.0,
    )

    assert config.tier == BillingTier.PRO
    assert config.pricing == PricingModel.PER_TOKEN


@pytest.mark.asyncio
async def test_pricing_info():
    """Test pricing info."""
    pricing = PricingInfo(
        input_token_price=0.005,
        output_token_price=0.025,
    )

    assert pricing.input_token_price == 0.005
    assert pricing.output_token_price == 0.025


@pytest.mark.asyncio
async def test_reset_period():
    """Test resetting billing period."""
    service = BillingService()

    await service.record_usage("claude-sonnet-4-6", 100, 50)
    assert service._state.total_requests > 0

    await service.reset_period()
    assert service._state.total_requests == 0


@pytest.mark.asyncio
async def test_get_pricing():
    """Test getting pricing."""
    service = BillingService()

    pricing = await service.get_pricing("claude-sonnet-4-6")
    assert pricing is not None

    pricing = await service.get_pricing("unknown-model")
    assert pricing is not None  # Returns default


@pytest.mark.asyncio
async def test_billing_tier():
    """Test billing tier enum."""
    assert BillingTier.FREE.value == "free"
    assert BillingTier.PRO.value == "pro"
    assert BillingTier.ENTERPRISE.value == "enterprise"


@pytest.mark.asyncio
async def test_pricing_model():
    """Test pricing model enum."""
    assert PricingModel.PER_TOKEN.value == "per_token"
    assert PricingModel.PER_REQUEST.value == "per_request"