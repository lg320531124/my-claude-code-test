"""API services module."""

from __future__ import annotations

# Import with try/except to avoid SDK dependency requirement
try:
    from .client import (
        APIClient,
        CompatClient,
        APIProvider,
        APIError,
        StreamEvent,
        UsageStats,
        OAuthTokens,
        TokenManager,
        get_client,
        detect_provider_from_url,
        is_env_truthy,
        load_settings,
        save_settings,
    )
except ImportError:
    # SDK not available - use fallback implementations
    APIClient = None
    CompatClient = None
    APIProvider = None
    APIError = Exception
    StreamEvent = None
    UsageStats = None
    OAuthTokens = None
    TokenManager = None
    get_client = None
    detect_provider_from_url = None
    def is_env_truthy(x):
        return False
    def load_settings():
        return {}
    def save_settings(x):
        return None

__all__ = [
    "APIClient",
    "CompatClient",
    "APIProvider",
    "APIError",
    "StreamEvent",
    "UsageStats",
    "OAuthTokens",
    "TokenManager",
    "get_client",
    "detect_provider_from_url",
    "is_env_truthy",
    "load_settings",
    "save_settings",
]