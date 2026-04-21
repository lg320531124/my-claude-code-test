"""Tests for error recovery."""

import pytest
import asyncio
from src.cc.core.error_recovery import (
    ErrorRecovery,
    RecoveryConfig,
    ErrorType,
    RecoveryStrategy,
    ErrorInfo,
    RecoveryState,
)


@pytest.mark.asyncio
async def test_error_recovery_init():
    """Test error recovery initialization."""
    recovery = ErrorRecovery()
    assert recovery.config is not None
    assert recovery._state is not None


@pytest.mark.asyncio
async def test_handle_error():
    """Test handle error."""
    recovery = ErrorRecovery()

    error = TimeoutError("Request timed out")
    info = await recovery.handle_error(error)

    assert info.type == ErrorType.TIMEOUT
    assert info.retryable is True
    assert recovery._state.consecutive_failures == 1


@pytest.mark.asyncio
async def test_classify_network_error():
    """Test classify network error."""
    recovery = ErrorRecovery()

    class NetworkError(Exception):
        pass

    error = NetworkError("Connection failed")
    info = await recovery.handle_error(error)

    assert info.type == ErrorType.NETWORK


@pytest.mark.asyncio
async def test_classify_rate_limit_error():
    """Test classify rate limit error."""
    recovery = ErrorRecovery()

    class RateLimitError(Exception):
        pass

    error = RateLimitError("Too many requests")
    info = await recovery.handle_error(error)

    assert info.type == ErrorType.RATE_LIMIT
    assert info.retryable is True


@pytest.mark.asyncio
async def test_classify_auth_error():
    """Test classify auth error."""
    recovery = ErrorRecovery()

    class UnauthorizedError(Exception):
        pass

    error = UnauthorizedError("Invalid credentials")
    info = await recovery.handle_error(error)

    assert info.type == ErrorType.AUTH
    assert info.retryable is False


@pytest.mark.asyncio
async def test_retry_success():
    """Test retry with success."""
    recovery = ErrorRecovery()

    call_count = {"count": 0}

    async def succeed_on_second():
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise TimeoutError("First attempt failed")
        return "success"

    result = await recovery.retry(succeed_on_second)

    assert result == "success"
    assert call_count["count"] == 2
    assert recovery._state.consecutive_failures == 0


@pytest.mark.asyncio
async def test_retry_all_fail():
    """Test retry all attempts fail."""
    config = RecoveryConfig(max_retries=3)
    recovery = ErrorRecovery(config)

    async def always_fail():
        raise TimeoutError("Always fails")

    with pytest.raises(TimeoutError):
        await recovery.retry(always_fail)


@pytest.mark.asyncio
async def test_retry_non_retryable():
    """Test retry non-retryable error."""
    recovery = ErrorRecovery()

    class ValidationError(Exception):
        pass

    async def validation_fail():
        raise ValidationError("Invalid input")

    with pytest.raises(ValidationError):
        await recovery.retry(validation_fail)


@pytest.mark.asyncio
async def test_fallback():
    """Test fallback."""
    recovery = ErrorRecovery()

    async def fallback_func():
        return "fallback result"

    recovery.register_fallback("test_func", fallback_func)

    result = await recovery.fallback("test_func")
    assert result == "fallback result"


@pytest.mark.asyncio
async def test_fallback_not_registered():
    """Test fallback not registered."""
    recovery = ErrorRecovery()

    with pytest.raises(Exception):
        await recovery.fallback("nonexistent_func")


@pytest.mark.asyncio
async def test_circuit_breaker():
    """Test circuit breaker."""
    config = RecoveryConfig(
        max_retries=1,
        retry_delay=0.1,  # Faster retries
        circuit_break_threshold=2,
        circuit_break_timeout=10.0,  # Longer timeout so it stays open
    )
    recovery = ErrorRecovery(config)

    async def always_fail():
        raise TimeoutError("Always fails")

    # Trigger failures to open circuit
    try:
        await recovery.retry(always_fail)
    except:
        pass

    try:
        await recovery.retry(always_fail)
    except:
        pass

    # Circuit should be open
    assert recovery.is_circuit_open() is True


@pytest.mark.asyncio
async def test_close_circuit_breaker():
    """Test close circuit breaker."""
    recovery = ErrorRecovery()

    # Manually open circuit
    recovery._state.circuit_open = True
    recovery._state.circuit_open_until = 999999.0

    await recovery.close_circuit_breaker()

    assert recovery._state.circuit_open is False


@pytest.mark.asyncio
async def test_register_handler():
    """Test register error handler."""
    recovery = ErrorRecovery()

    async def timeout_handler(info):
        pass

    recovery.register_handler(ErrorType.TIMEOUT, timeout_handler)

    assert ErrorType.TIMEOUT in recovery._error_handlers


@pytest.mark.asyncio
async def test_reset():
    """Test reset."""
    recovery = ErrorRecovery()

    # Trigger some errors
    await recovery.handle_error(TimeoutError("Error"))

    await recovery.reset()

    assert recovery._state.consecutive_failures == 0
    assert recovery._state.total_retries == 0


@pytest.mark.asyncio
async def test_get_state():
    """Test get state."""
    recovery = ErrorRecovery()

    state = recovery.get_state()

    assert state.consecutive_failures == 0
    assert state.circuit_open is False


@pytest.mark.asyncio
async def test_recovery_config():
    """Test recovery config."""
    config = RecoveryConfig(
        max_retries=5,
        retry_delay=2.0,
        backoff_factor=3.0,
        max_delay=120.0,
        circuit_break_threshold=10,
    )

    assert config.max_retries == 5
    assert config.retry_delay == 2.0
    assert config.backoff_factor == 3.0


@pytest.mark.asyncio
async def test_error_info():
    """Test error info."""
    info = ErrorInfo(
        type=ErrorType.NETWORK,
        message="Connection failed",
        retryable=True,
    )

    assert info.type == ErrorType.NETWORK
    assert info.retryable is True


@pytest.mark.asyncio
async def test_recovery_strategy():
    """Test recovery strategy enum."""
    assert RecoveryStrategy.RETRY.value == "retry"
    assert RecoveryStrategy.FALLBACK.value == "fallback"
    assert RecoveryStrategy.ABORT.value == "abort"
    assert RecoveryStrategy.CIRCUIT_BREAK.value == "circuit_break"