"""OAuth GitHub - Async GitHub OAuth flow."""

from __future__ import annotations
import asyncio
import secrets
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass
class GitHubOAuthConfig:
    """GitHub OAuth configuration."""
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = "repo,user,read:org"
    authorize_url: str = "https://github.com/login/oauth/authorize"
    token_url: str = "https://github.com/login/oauth/access_token"
    api_url: str = "https://api.github.com"


@dataclass
class GitHubToken:
    """GitHub OAuth token."""
    access_token: str
    token_type: str = "bearer"
    scope: str = ""
    expires_at: Optional[float] = None
    refresh_token: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class GitHubUser:
    """GitHub user info."""
    id: int
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None


class GitHubOAuthClient:
    """Async GitHub OAuth client."""

    def __init__(self, config: GitHubOAuthConfig):
        self.config = config
        self._http_client = None
        self._state: Optional[str] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}

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
        }

        return f"{self.config.authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str, state: str) -> GitHubToken:
        """Exchange authorization code for token."""
        # Verify state
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
                "state": state,
            },
            headers={"Accept": "application/json"},
        )

        data = response.json()

        if "error" in data:
            raise ValueError(f"OAuth error: {data['error']}")

        return GitHubToken(
            access_token=data.get("access_token", ""),
            token_type=data.get("token_type", "bearer"),
            scope=data.get("scope", ""),
        )

    async def get_user_info(self, token: GitHubToken) -> GitHubUser:
        """Get user info using token."""
        client = await self._get_http_client()

        response = await client.get(
            f"{self.config.api_url}/user",
            headers={
                "Authorization": f"token {token.access_token}",
                "Accept": "application/json",
            },
        )

        data = response.json()

        return GitHubUser(
            id=data.get("id", 0),
            login=data.get("login", ""),
            name=data.get("name"),
            email=data.get("email"),
            avatar_url=data.get("avatar_url"),
            html_url=data.get("html_url"),
        )

    async def validate_token(self, token: GitHubToken) -> bool:
        """Validate token is still valid."""
        try:
            user = await self.get_user_info(token)
            return user.id > 0
        except Exception:
            return False

    async def revoke_token(self, token: GitHubToken) -> bool:
        """Revoke token."""
        client = await self._get_http_client()

        response = await client.delete(
            f"{self.config.api_url}/applications/{self.config.client_id}/token",
            headers={
                "Authorization": f"token {token.access_token}",
                "Accept": "application/json",
            },
            json={"access_token": token.access_token},
        )

        return response.status_code == 204

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class GitHubAppAuth:
    """GitHub App authentication."""

    def __init__(self, app_id: str, private_key: str):
        self.app_id = app_id
        self.private_key = private_key
        self._jwt_cache: Optional[Dict[str, Any]] = None

    def generate_jwt(self, expiration: int = 600) -> str:
        """Generate JWT for GitHub App."""
        import jwt  # PyJWT library

        now = int(time.time())

        payload = {
            "iat": now,
            "exp": now + expiration,
            "iss": self.app_id,
        }

        token = jwt.encode(payload, self.private_key, algorithm="RS256")

        self._jwt_cache = {
            "token": token,
            "expires_at": now + expiration,
        }

        return token

    async def get_installation_token(self, installation_id: int) -> str:
        """Get installation access token."""
        import httpx

        jwt_token = self.generate_jwt()

        client = httpx.AsyncClient()

        response = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/json",
            },
        )

        data = response.json()
        await client.aclose()

        return data.get("token", "")


class GitHubDeviceFlow:
    """GitHub device authorization flow."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self._device_code: Optional[str] = None
        self._user_code: Optional[str] = None

    async def start_device_flow(self) -> Dict[str, str]:
        """Start device authorization flow."""
        import httpx

        client = httpx.AsyncClient()

        response = await client.post(
            "https://github.com/login/device/code",
            data={
                "client_id": self.client_id,
                "scope": "repo,user",
            },
            headers={"Accept": "application/json"},
        )

        data = response.json()
        await client.aclose()

        self._device_code = data.get("device_code")
        self._user_code = data.get("user_code")

        return {
            "device_code": self._device_code,
            "user_code": self._user_code,
            "verification_uri": data.get("verification_uri", "https://github.com/login/device"),
            "expires_in": data.get("expires_in", 900),
            "interval": data.get("interval", 5),
        }

    async def poll_for_token(
        self,
        client_secret: str,
        interval: int = 5,
        timeout: int = 900,
    ) -> Optional[str]:
        """Poll for access token."""
        import httpx

        client = httpx.AsyncClient()
        start_time = time.time()

        while time.time() - start_time < timeout:
            await asyncio.sleep(interval)

            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": client_secret,
                    "device_code": self._device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )

            data = response.json()

            if "access_token" in data:
                await client.aclose()
                return data["access_token"]

            if data.get("error") == "authorization_pending":
                continue

            if data.get("error") in ["expired_token", "access_denied"]:
                await client.aclose()
                return None

        await client.aclose()
        return None


__all__ = [
    "GitHubOAuthConfig",
    "GitHubToken",
    "GitHubUser",
    "GitHubOAuthClient",
    "GitHubAppAuth",
    "GitHubDeviceFlow",
]