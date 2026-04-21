"""Tests for rate limiter."""

import pytest
import asyncio
from src.cc.core.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimit,
    LimitState,
    LimitType,
)


@pytest.mark.asyncio
async def test_rate_limiter_init():
    """Test rate limiter initialization."""
    limiter = RateLimiter()
    assert limiter.config is not None
    assert limiter._state is not None


@pytest.mark.asyncio
async def test_acquire_success():
    """Test successful acquire."""
    config = RateLimitConfig(
        limits=RateLimit(
            requests_per_minute=60,
            tokens_per_minute=100000,
            max_concurrent=10,
        )
    )
    limiter = RateLimiter(config)

    result = await limiter.acquire(tokens=100)
    assert result is True
    assert limiter._state.requests == 1
    assert limiter._state.tokens == 100
    assert limiter._state.concurrent == 1


@pytest.mark.asyncio
async def test_acquire_requests_limit():
    """Test requests limit."""
    config = RateLimitConfig(
        limits=RateLimit(requests_per_minute=2, max_concurrent=10)
    )
    limiter = RateLimiter(config)

    # First two should succeed
    assert await limiter.acquire() is True
    assert await limiter.acquire() is True

    # Third should fail
    result = await limiter.acquire()
    assert result is False


@pytest.mark.asyncio
async def test_acquire_concurrent_limit():
    """Test concurrent limit."""
    config = RateLimitConfig(
        limits=RateLimit(max_concurrent=2, requests_per_minute=100)
    )
    limiter = RateLimiter(config)

    # Acquire two slots
    assert await limiter.acquire() is True
    assert await limiter.acquire() is True

    # Third should fail
    result = await limiter.acquire()
    assert result is False


@pytest.mark.asyncio
async def test_release():
    """Test release."""
    limiter = RateLimiter()

    await limiter.acquire()
    assert limiter._state.concurrent == 1

    await limiter.release()
    assert limiter._state.concurrent == 0


@pytest.mark.asyncio
async def test_wait_for_slot():
    """Test wait for slot."""
    config = RateLimitConfig(
        limits=RateLimit(max_concurrent=1, requests_per_minute=100),
        reset_interval=0.1,
    )
    limiter = RateLimiter(config)

    # Acquire first slot
    await limiter.acquire()

    # Wait should eventually succeed after reset
    result = await limiter.wait_for_slot(timeout=1.0)
    assert result is True


@pytest.mark.asyncio
async def test_block():
    """Test block."""
    limiter = RateLimiter()

    await limiter.block(duration=1.0)

    assert limiter.is_blocked() is True

    # Acquire should fail while blocked
    result = await limiter.acquire()
    assert result is False


@pytest.mark.asyncio
async def test_unblock():
    """Test unblock."""
    limiter = RateLimiter()

    await limiter.block(duration=10.0)
    assert limiter.is_blocked() is True

    await limiter.unblock()
    assert limiter.is_blocked() is False


@pytest.mark.asyncio
async def test_get_usage():
    """Test get usage."""
    limiter = RateLimiter()

    await limiter.acquire(tokens=100)

    usage = await limiter.get_usage()

    assert usage["requests"] == 1
    assert usage["tokens"] == 100
    assert usage["concurrent"] == 1
    assert usage["blocked"] is False


@pytest.mark.asyncio
async def test_reset():
    """Test reset."""
    limiter = RateLimiter()

    await limiter.acquire(tokens=100)
    await limiter.block(duration=10.0)

    await limiter.reset()

    assert limiter._state.requests == 0
    assert limiter._state.tokens == 0
    assert limiter._state.concurrent == 0
    assert limiter.is_blocked() is False


@pytest.mark.asyncio
async def test_queue_request():
    """Test queue request."""
    limiter = RateLimiter()

    request = {"data": "test"}
    result = await limiter.queue_request(request)

    assert result is True
    assert limiter.get_queue_size() == 1


@pytest.mark.asyncio
async def test_rate_limit_config():
    """Test rate limit config."""
    config = RateLimitConfig(
        limits=RateLimit(
            requests_per_minute=30,
            tokens_per_minute=50000,
            max_concurrent=5,
        ),
        auto_reset=True,
        reset_interval=30.0,
    )

    assert config.limits.requests_per_minute == 30
    assert config.limits.tokens_per_minute == 50000
    assert config.auto_reset is True


@pytest.mark.asyncio
async def test_limit_state():
    """Test limit state."""
    state = LimitState(
        requests=10,
        tokens=5000,
        concurrent=3,
        last_reset=100.0,
    )

    assert state.requests == 10
    assert state.tokens == 5000
    assert state.concurrent == 3


@pytest.mark.asyncio
async def test_limit_type():
    """Test limit type enum."""
    assert LimitType.REQUESTS.value == "requests"
    assert LimitType.TOKENS.value == "tokens"
    assert LimitType.CONCURRENT.value == "concurrent"