"""OAuth Anthropic - Async Anthropic OAuth flow."""

from __future__ import annotations
import secrets
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass
class AnthropicOAuthConfig:
    """Anthropic OAuth configuration."""
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = "console:read console:write api:read api:write"
    authorize_url: str = "https://console.anthropic.com/oauth/authorize"
    token_url: str = "https://console.anthropic.com/oauth/token"


@dataclass
class AnthropicToken:
    """Anthropic OAuth token."""
    access_token: str
    token_type: str = "bearer"
    scope: str = ""
    expires_at: Optional[float] = None
    refresh_token: Optional[str] = None
    session_key: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class AnthropicAccount:
    """Anthropic account info."""
    account_id: str
    email: str
    name: Optional[str] = None
    plan_type: str = ""
    api_key: Optional[str] = None


class AnthropicOAuthClient:
    """Async Anthropic OAuth client."""

    def __init__(self, config: AnthropicOAuthConfig):
        self.config = config
        self._http_client = None
        self._state: Optional[str] = None

    async def _get_http_client(self):
        """Get HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient()
        return self._http_client

    def generate_authorize_url(self, state: str = None) -> str:
        """Generate authorization URL."""
        self._state = state or secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": self.config.scope,
            "state": self._state,
            "response_type": "code",
        }

        return f"{self.config.authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str, state: str) -> AnthropicToken:
        """Exchange authorization code for token."""
        if state != self._state:
            raise ValueError("Invalid state parameter")

        client = await self._get_http_client()

        response = await client.post(
            self.config.token_url,
            data={
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "code": code,
                "redirect_uri": self.config.redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )

        data = response.json()

        if "error" in data:
            raise ValueError(f"OAuth error: {data['error']}")

        expires_in = data.get("expires_in", 3600)

        return AnthropicToken(
            access_token=data.get("access_token", ""),
            token_type=data.get("token_type", "bearer"),
            scope=data.get("scope", ""),
            expires_at=time.time() + expires_in,
            refresh_token=data.get("refresh_token"),
            session_key=data.get("session_key"),
        )

    async def refresh_token(self, token: AnthropicToken) -> AnthropicToken:
        """Refresh expired token."""
        if not token.refresh_token:
            raise ValueError("No refresh token available")

        client = await self._get_http_client()

        response = await client.post(
            self.config.token_url,
            data={
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": token.refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
        )

        data = response.json()

        if "error" in data:
            raise ValueError(f"Refresh error: {data['error']}")

        expires_in = data.get("expires_in", 3600)

        return AnthropicToken(
            access_token=data.get("access_token", ""),
            token_type=data.get("token_type", "bearer"),
            scope=data.get("scope", ""),
            expires_at=time.time() + expires_in,
            refresh_token=data.get("refresh_token", token.refresh_token),
        )

    async def get_account_info(self, token: AnthropicToken) -> AnthropicAccount:
        """Get account info using token."""
        client = await self._get_http_client()

        response = await client.get(
            "https://api.anthropic.com/v1/users/me",
            headers={
                "Authorization": f"Bearer {token.access_token}",
                "Accept": "application/json",
            },
        )

        data = response.json()

        return AnthropicAccount(
            account_id=data.get("id", ""),
            email=data.get("email", ""),
            name=data.get("name"),
            plan_type=data.get("plan_type", ""),
        )

    async def get_api_key(self, token: AnthropicToken) -> Optional[str]:
        """Get API key from console."""
        if not token.session_key:
            return None

        client = await self._get_http_client()

        response = await client.get(
            "https://console.anthropic.com/api-keys",
            headers={
                "Cookie": f"session_key={token.session_key}",
                "Accept": "application/json",
            },
        )

        data = response.json()

        if "api_keys" in data and data["api_keys"]:
            return data["api_keys"][0].get("key")

        return None

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class AnthropicAPIKeyAuth:
    """Direct API key authentication."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._http_client = None

    async def _get_http_client(self):
        """Get HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient()
        return self._http_client

    async def validate_key(self) -> bool:
        """Validate API key."""
        client = await self._get_http_client()

        try:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )

            return response.status_code == 200

        except Exception:
            return False

    async def get_usage(self) -> Dict[str, Any]:
        """Get API usage info."""
        client = await self._get_http_client()

        response = await client.get(
            "https://api.anthropic.com/v1/usage",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Accept": "application/json",
            },
        )

        return response.json()

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


__all__ = [
    "AnthropicOAuthConfig",
    "AnthropicToken",
    "AnthropicAccount",
    "AnthropicOAuthClient",
    "AnthropicAPIKeyAuth",
]