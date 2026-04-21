"""Services API - Complete API services."""

from __future__ import annotations
from .client import (
    APIClient,
    APIProvider,
    APIError,
    StreamEvent,
    UsageStats,
    get_client,
)
from .streaming import (
    StreamEventType,
    SSEParser,
    MessageAccumulator,
    StreamingResponseHandler,
)
from .retry import (
    RetryReason,
    RetryConfig,
    RetryHandler,
    AdaptiveRetry,
    retry_with_backoff,
)
from .errors import (
    ErrorType,
    APIError as ClassifiedAPIError,
    ErrorClassifier,
    ErrorHandler,
    classify_error,
)
from .limits import (
    LimitType,
    LimitConfig,
    RateLimiter,
    UsageTracker,
    get_rate_limiter,
    get_usage_tracker,
)

__all__ = [
    # Client
    "APIClient",
    "APIProvider",
    "APIError",
    "StreamEvent",
    "UsageStats",
    "get_client",
    # Streaming
    "StreamEventType",
    "SSEParser",
    "MessageAccumulator",
    "StreamingResponseHandler",
    # Retry
    "RetryReason",
    "RetryConfig",
    "RetryHandler",
    "AdaptiveRetry",
    "retry_with_backoff",
    # Errors
    "ErrorType",
    "ClassifiedAPIError",
    "ErrorClassifier",
    "ErrorHandler",
    "classify_error",
    # Limits
    "LimitType",
    "LimitConfig",
    "RateLimiter",
    "UsageTracker",
    "get_rate_limiter",
    "get_usage_tracker",
]