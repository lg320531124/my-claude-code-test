"""OAuth Service - OAuth authentication providers."""

from __future__ import annotations
from .oauth import OAuthService, OAuthProvider, OAuthToken, OAuthState
from .flow import OAuthFlow, OAuthTokens, OAuthStateManager, PKCEHelper, TokenStorage
from .github import GitHubOAuthClient, GitHubOAuthConfig, GitHubToken, GitHubUser, GitHubDeviceFlow
from .anthropic import AnthropicOAuthClient, AnthropicOAuthConfig, AnthropicToken, AnthropicAPIKeyAuth

__all__ = [
    # Base OAuth
    "OAuthService",
    "OAuthProvider",
    "OAuthToken",
    "OAuthState",
    # Flow
    "OAuthFlow",
    "OAuthTokens",
    "OAuthStateManager",
    "PKCEHelper",
    "TokenStorage",
    # GitHub
    "GitHubOAuthClient",
    "GitHubOAuthConfig",
    "GitHubToken",
    "GitHubUser",
    "GitHubDeviceFlow",
    # Anthropic
    "AnthropicOAuthClient",
    "AnthropicOAuthConfig",
    "AnthropicToken",
    "AnthropicAPIKeyAuth",
]
