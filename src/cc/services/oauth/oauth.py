"""OAuth Service - OAuth authentication."""

from __future__ import annotations
import json
import time
import secrets
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class OAuthProvider(Enum):
    """OAuth providers."""
    GITHUB = "github"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


@dataclass
class OAuthToken:
    """OAuth token data."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    token_type: str = "Bearer"
    scope: str = ""
    provider: OAuthProvider = OAuthProvider.CUSTOM


@dataclass
class OAuthState:
    """OAuth state for tracking."""
    state_id: str
    provider: OAuthProvider
    redirect_uri: str
    created_at: float
    completed: bool = False
    token: Optional[OAuthToken] = None


class OAuthService:
    """Service for OAuth authentication."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".claude" / "oauth" / "tokens.json"
        self._states: Dict[str, OAuthState] = {}
        self._tokens: Dict[OAuthProvider, OAuthToken] = {}
        self._provider_configs: Dict[OAuthProvider, dict] = {
            OAuthProvider.GITHUB: {
                "auth_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "scope": "repo,user",
            },
            OAuthProvider.GOOGLE: {
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scope": "openid,email,profile",
            },
            OAuthProvider.ANTHROPIC: {
                "auth_url": "https://console.anthropic.com/oauth/authorize",
                "token_url": "https://api.anthropic.com/oauth/token",
                "scope": "api",
            },
        }

        self._load_tokens()

    def _load_tokens(self) -> None:
        """Load stored tokens."""
        if not self.storage_path.exists():
            return

        try:
            data = json.loads(self.storage_path.read_text())
            for provider_str, token_data in data.items():
                provider = OAuthProvider(provider_str)
                self._tokens[provider] = OAuthToken(
                    access_token=token_data.get("access_token", ""),
                    refresh_token=token_data.get("refresh_token"),
                    expires_at=token_data.get("expires_at"),
                    token_type=token_data.get("token_type", "Bearer"),
                    scope=token_data.get("scope", ""),
                    provider=provider,
                )
        except Exception:
            pass

    def _save_tokens(self) -> None:
        """Save tokens."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for provider, token in self._tokens.items():
            data[provider.value] = {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "expires_at": token.expires_at,
                "token_type": token.token_type,
                "scope": token.scope,
            }

        self.storage_path.write_text(json.dumps(data, indent=2))

    def create_auth_url(
        self,
        provider: OAuthProvider,
        client_id: str,
        redirect_uri: str,
        scope: Optional[str] = None,
    ) -> tuple[str, str]:
        """Create OAuth authorization URL."""
        state_id = secrets.token_urlsafe(32)

        state = OAuthState(
            state_id=state_id,
            provider=provider,
            redirect_uri=redirect_uri,
            created_at=time.time(),
        )
        self._states[state_id] = state

        config = self._provider_configs.get(provider, {})
        auth_url = config.get("auth_url", "")
        default_scope = config.get("scope", "")
        use_scope = scope or default_scope

        # Build URL
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": use_scope,
            "state": state_id,
            "response_type": "code",
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{auth_url}?{query}"

        return full_url, state_id

    async def complete_auth(
        self,
        state_id: str,
        code: str,
        client_id: str,
        client_secret: str,
    ) -> OAuthToken | None:
        """Complete OAuth authentication."""
        state = self._states.get(state_id)
        if not state:
            return None

        if state.completed:
            return state.token

        config = self._provider_configs.get(state.provider, {})
        config.get("token_url", "")

        # Simulate token exchange (in real implementation, would use httpx)
        # For now, create a mock token
        token = OAuthToken(
            access_token=secrets.token_urlsafe(32),
            refresh_token=secrets.token_urlsafe(32),
            expires_at=time.time() + 3600,  # 1 hour
            token_type="Bearer",
            scope=config.get("scope", ""),
            provider=state.provider,
        )

        state.completed = True
        state.token = token
        self._tokens[state.provider] = token
        self._save_tokens()

        return token

    def get_token(self, provider: OAuthProvider) -> OAuthToken | None:
        """Get token for provider."""
        token = self._tokens.get(provider)

        if token and token.expires_at:
            if time.time() > token.expires_at:
                # Token expired
                return None

        return token

    async def refresh_token(self, provider: OAuthProvider) -> OAuthToken | None:
        """Refresh token."""
        token = self._tokens.get(provider)
        if not token or not token.refresh_token:
            return None

        # Simulate refresh (would call token endpoint in real implementation)
        new_token = OAuthToken(
            access_token=secrets.token_urlsafe(32),
            refresh_token=token.refresh_token,
            expires_at=time.time() + 3600,
            token_type=token.token_type,
            scope=token.scope,
            provider=provider,
        )

        self._tokens[provider] = new_token
        self._save_tokens()

        return new_token

    def revoke_token(self, provider: OAuthProvider) -> bool:
        """Revoke token."""
        if provider in self._tokens:
            del self._tokens[provider]
            self._save_tokens()
            return True
        return False

    def get_valid_providers(self) -> List[OAuthProvider]:
        """Get providers with valid tokens."""
        valid = []
        for provider, token in self._tokens.items():
            if token.expires_at and time.time() > token.expires_at:
                continue
            valid.append(provider)
        return valid

    def cleanup_states(self, max_age_seconds: float = 300) -> int:
        """Cleanup old states."""
        now = time.time()
        to_remove = [
            id for id, state in self._states.items()
            if now - state.created_at > max_age_seconds and not state.completed
        ]

        for id in to_remove:
            del self._states[id]

        return len(to_remove)


__all__ = [
    "OAuthProvider",
    "OAuthToken",
    "OAuthState",
    "OAuthService",
]
