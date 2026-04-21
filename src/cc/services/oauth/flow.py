"""OAuth Flow - General OAuth flow utilities."""

from __future__ import annotations
import secrets
import time
import base64
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass
class OAuthState:
    """OAuth state tracking."""
    state: str
    provider: str
    created_at: float
    redirect_uri: str
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = None

    def is_expired(self) -> bool:
        """Check if state is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class OAuthTokens:
    """OAuth token set."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    scope: str = ""
    expires_in: Optional[int] = None
    expires_at: Optional[float] = None

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return time.time() > (self.expires_at - buffer_seconds)

    def should_refresh(self, threshold_seconds: int = 300) -> bool:
        """Check if token should be refreshed."""
        if self.expires_at is None:
            return False
        return time.time() > (self.expires_at - threshold_seconds)


class OAuthStateManager:
    """Manage OAuth state for CSRF protection."""

    def __init__(self, ttl_seconds: int = 600):
        self._states: Dict[str, OAuthState] = {}
        self._ttl = ttl_seconds

    def create_state(
        self,
        provider: str,
        redirect_uri: str,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """Create new OAuth state."""
        state = secrets.token_urlsafe(32)
        now = time.time()

        oauth_state = OAuthState(
            state=state,
            provider=provider,
            created_at=now,
            redirect_uri=redirect_uri,
            expires_at=now + self._ttl,
            metadata=metadata or {},
        )

        self._states[state] = oauth_state

        # Cleanup expired states
        self._cleanup_expired()

        return state

    def validate_state(self, state: str) -> Optional[OAuthState]:
        """Validate and retrieve OAuth state."""
        oauth_state = self._states.get(state)

        if oauth_state is None:
            return None

        if oauth_state.is_expired():
            del self._states[state]
            return None

        # Remove after use (one-time)
        del self._states[state]

        return oauth_state

    def _cleanup_expired(self) -> None:
        """Remove expired states."""
        expired = [
            s for s, state in self._states.items()
            if state.is_expired()
        ]
        for s in expired:
            del self._states[s]


class PKCEHelper:
    """PKCE (Proof Key for Code Exchange) helper."""

    def __init__(self):
        self._code_verifier: Optional[str] = None
        self._code_challenge: Optional[str] = None

    def generate_verifier(self) -> str:
        """Generate code verifier."""
        # Generate random 32-byte string, base64url encoded
        random_bytes = secrets.token_bytes(32)
        self._code_verifier = base64.urlsafe_b64encode(random_bytes).decode().rstrip("=")
        return self._code_verifier

    def generate_challenge(self, method: str = "S256") -> str:
        """Generate code challenge from verifier."""
        if self._code_verifier is None:
            self.generate_verifier()

        if method == "plain":
            self._code_challenge = self._code_verifier
        elif method == "S256":
            # SHA256 hash, base64url encoded
            digest = hashlib.sha256(self._code_verifier.encode()).digest()
            self._code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        else:
            raise ValueError(f"Unsupported challenge method: {method}")

        return self._code_challenge

    def get_verifier(self) -> Optional[str]:
        """Get stored code verifier."""
        return self._code_verifier


class OAuthFlow:
    """Generic OAuth flow handler."""

    def __init__(self):
        self._state_manager = OAuthStateManager()
        self._pkce_helper = PKCEHelper()
        self._http_client = None

    async def _get_http_client(self):
        """Get HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient()
        return self._http_client

    def build_authorize_url(
        self,
        authorize_url: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        provider: str,
        use_pkce: bool = True,
        extra_params: Dict[str, str] = None,
    ) -> str:
        """Build authorization URL."""
        state = self._state_manager.create_state(
            provider=provider,
            redirect_uri=redirect_uri,
        )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "response_type": "code",
        }

        if use_pkce:
            params["code_challenge"] = self._pkce_helper.generate_challenge()
            params["code_challenge_method"] = "S256"

        if extra_params:
            params.update(extra_params)

        return f"{authorize_url}?{urlencode(params)}"

    async def exchange_code(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        state: str,
        use_pkce: bool = True,
    ) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        # Validate state
        oauth_state = self._state_manager.validate_state(state)
        if oauth_state is None:
            raise ValueError("Invalid or expired OAuth state")

        client = await self._get_http_client()

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        if use_pkce:
            verifier = self._pkce_helper.get_verifier()
            if verifier:
                data["code_verifier"] = verifier

        response = await client.post(
            token_url,
            data=data,
            headers={"Accept": "application/json"},
        )

        result = response.json()

        if "error" in result:
            raise ValueError(f"OAuth error: {result['error']}")

        expires_in = result.get("expires_in")
        expires_at = time.time() + expires_in if expires_in else None

        return OAuthTokens(
            access_token=result.get("access_token", ""),
            refresh_token=result.get("refresh_token"),
            token_type=result.get("token_type", "bearer"),
            scope=result.get("scope", ""),
            expires_in=expires_in,
            expires_at=expires_at,
        )

    async def refresh_tokens(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> OAuthTokens:
        """Refresh access token."""
        client = await self._get_http_client()

        response = await client.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
        )

        result = response.json()

        if "error" in result:
            raise ValueError(f"Refresh error: {result['error']}")

        expires_in = result.get("expires_in")
        expires_at = time.time() + expires_in if expires_in else None

        return OAuthTokens(
            access_token=result.get("access_token", ""),
            refresh_token=result.get("refresh_token", refresh_token),
            token_type=result.get("token_type", "bearer"),
            scope=result.get("scope", ""),
            expires_in=expires_in,
            expires_at=expires_at,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class TokenStorage:
    """Storage for OAuth tokens."""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "~/.claude/oauth_tokens.json"
        self._tokens: Dict[str, OAuthTokens] = {}

    async def load(self) -> None:
        """Load tokens from storage."""
        import aiofiles
        import json
        from pathlib import Path

        path = Path(self.storage_path).expanduser()

        if not path.exists():
            return

        async with aiofiles.open(path, "r") as f:
            content = await f.read()

        data = json.loads(content)

        for provider, token_data in data.items():
            self._tokens[provider] = OAuthTokens(
                access_token=token_data.get("access_token", ""),
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "bearer"),
                scope=token_data.get("scope", ""),
                expires_at=token_data.get("expires_at"),
            )

    async def save(self) -> None:
        """Save tokens to storage."""
        import aiofiles
        import json
        from pathlib import Path

        path = Path(self.storage_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for provider, token in self._tokens.items():
            data[provider] = {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "token_type": token.token_type,
                "scope": token.scope,
                "expires_at": token.expires_at,
            }

        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    def get_token(self, provider: str) -> Optional[OAuthTokens]:
        """Get token for provider."""
        return self._tokens.get(provider)

    def set_token(self, provider: str, token: OAuthTokens) -> None:
        """Set token for provider."""
        self._tokens[provider] = token

    def remove_token(self, provider: str) -> None:
        """Remove token for provider."""
        self._tokens.pop(provider, None)

    def list_providers(self) -> List[str]:
        """List providers with tokens."""
        return list(self._tokens.keys())


__all__ = [
    "OAuthState",
    "OAuthTokens",
    "OAuthStateManager",
    "PKCEHelper",
    "OAuthFlow",
    "TokenStorage",
]