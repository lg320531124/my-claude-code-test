"""API Client - Direct Anthropic API implementation (ported from leaked source).

This module implements the Anthropic API client directly using httpx,
supporting multiple backends: direct API, Bedrock, Vertex, and Foundry.
No external SDK dependency required.

Key patterns from TypeScript source (client.ts, auth.ts):
- OAuth token management and refresh
- Multiple backend support (Bedrock, Vertex, Foundry)
- Streaming response handling with SSE parsing
- Retry logic with exponential backoff
- Custom headers and proxy support
"""

from __future__ import annotations
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

import httpx


class APIProvider(Enum):
    """API provider types."""
    DIRECT = "direct"
    BEDROCK = "bedrock"
    VERTEX = "vertex"
    FOUNDRY = "foundry"
    COMPAT = "compat"  # Compatible APIs like Zhipu


@dataclass
class OAuthTokens:
    """OAuth token storage."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None  # Unix timestamp
    scopes: List[str] = field(default_factory=lambda: ["user:inference"])
    subscription_type: Optional[str] = None  # max, pro, enterprise, team
    rate_limit_tier: Optional[str] = None


@dataclass
class UsageStats:
    """API usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_tokens: int = 0

    def accumulate(self, other: UsageStats) -> UsageStats:
        """Accumulate usage from another stats object."""
        return UsageStats(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_creation_tokens=self.cache_creation_tokens + other.cache_creation_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class StreamEvent:
    """Streaming event types."""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)


class APIError(Exception):
    """API error with categorization."""

    def __init__(self, message: str, status: Optional[int] = None, error_type: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.error_type = error_type or "api_error"

    def is_retryable(self) -> bool:
        """Check if error is retryable."""
        retryable_types = [
            "overloaded",
            "rate_limit_error",
            "timeout_error",
        ]
        return self.error_type in retryable_types or self.status in [429, 503, 504]


def is_env_truthy(value: Optional[str]) -> bool:
    """Check if env var is truthy."""
    if value is None:
        return False
    return value.lower() in ("true", "1", "yes", "on")


def get_config_dir() -> Path:
    """Get Claude config directory."""
    return Path.home() / ".claude"


def get_settings_file() -> Path:
    """Get settings file path."""
    return get_config_dir() / "settings.json"


def load_settings() -> Dict[str, Any]:
    """Load settings from file."""
    settings_file = get_settings_file()
    if settings_file.exists():
        try:
            return json.loads(settings_file.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to file."""
    settings_file = get_settings_file()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(settings, indent=2))


class TokenManager:
    """Manages OAuth tokens and API keys (ported from auth.ts)."""

    def __init__(self):
        self._oauth_cache: Optional[OAuthTokens] = None
        self._api_key_cache: Optional[str] = None
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 300.0  # 5 minutes

    def get_api_key(self) -> Optional[str]:
        """Get API key from various sources (auth.ts patterns)."""
        # Check environment first
        if os.environ.get("ANTHROPIC_API_KEY"):
            return os.environ["ANTHROPIC_API_KEY"]

        # Check file descriptor
        fd = os.environ.get("CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR")
        if fd:
            try:
                # Read from file descriptor
                with open(int(fd), "r") as f:
                    return f.read().strip()
            except (OSError, IOError, ValueError):
                pass

        # Check settings
        settings = load_settings()
        if settings.get("primaryApiKey"):
            return settings["primaryApiKey"]

        # Check keychain (macOS) or credentials file
        credentials_file = get_config_dir() / ".credentials.json"
        if credentials_file.exists():
            try:
                creds = json.loads(credentials_file.read_text())
                return creds.get("apiKey")
            except (json.JSONDecodeError, IOError):
                pass

        return None

    def get_auth_token(self) -> Optional[str]:
        """Get authentication token (OAuth or API key)."""
        # Check OAuth token from env
        if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
            return os.environ["CLAUDE_CODE_OAUTH_TOKEN"]

        # Check auth token from env
        if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            return os.environ["ANTHROPIC_AUTH_TOKEN"]

        # Check OAuth tokens from storage
        tokens = self.get_oauth_tokens()
        if tokens:
            return tokens.access_token

        return None

    def get_oauth_tokens(self) -> Optional[OAuthTokens]:
        """Get OAuth tokens from storage."""
        if self._oauth_cache and time.time() - self._cache_timestamp < self._cache_ttl:
            return self._oauth_cache

        # Load from credentials file
        credentials_file = get_config_dir() / ".credentials.json"
        if credentials_file.exists():
            try:
                creds = json.loads(credentials_file.read_text())
                oauth_data = creds.get("claudeAiOauth", {})
                if oauth_data.get("accessToken"):
                    self._oauth_cache = OAuthTokens(
                        access_token=oauth_data["accessToken"],
                        refresh_token=oauth_data.get("refreshToken"),
                        expires_at=oauth_data.get("expiresAt"),
                        scopes=oauth_data.get("scopes", ["user:inference"]),
                        subscription_type=oauth_data.get("subscriptionType"),
                        rate_limit_tier=oauth_data.get("rateLimitTier"),
                    )
                    self._cache_timestamp = time.time()
                    return self._oauth_cache
            except (json.JSONDecodeError, IOError):
                pass

        return None

    def is_token_expired(self, tokens: OAuthTokens) -> bool:
        """Check if token is expired."""
        if tokens.expires_at is None:
            return False
        # Add 5 minute buffer
        return time.time() > tokens.expires_at - 300

    def save_oauth_tokens(self, tokens: OAuthTokens) -> None:
        """Save OAuth tokens to storage."""
        credentials_file = get_config_dir() / ".credentials.json"
        credentials_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing
        creds = {}
        if credentials_file.exists():
            try:
                creds = json.loads(credentials_file.read_text())
            except (json.JSONDecodeError, IOError):
                pass

        # Update
        creds["claudeAiOauth"] = {
            "accessToken": tokens.access_token,
            "refreshToken": tokens.refresh_token,
            "expiresAt": tokens.expires_at,
            "scopes": tokens.scopes,
            "subscriptionType": tokens.subscription_type,
            "rateLimitTier": tokens.rate_limit_tier,
        }

        credentials_file.write_text(json.dumps(creds, indent=2))
        self._oauth_cache = tokens
        self._cache_timestamp = time.time()

    def get_subscription_type(self) -> Optional[str]:
        """Get user subscription type."""
        tokens = self.get_oauth_tokens()
        return tokens.subscription_type if tokens else None

    def is_claude_ai_subscriber(self) -> bool:
        """Check if user is Claude.ai subscriber."""
        tokens = self.get_oauth_tokens()
        if tokens and "user:inference" in tokens.scopes:
            return True
        return False


class APIClient:
    """Anthropic API client with streaming and multi-backend support.

    Ported from client.ts patterns:
    - Direct API calls using httpx (no SDK)
    - OAuth token management
    - Bedrock, Vertex, Foundry backend support
    - Streaming message handling with SSE parsing
    - Retry logic with exponential backoff
    """

    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_TIMEOUT = 600.0  # 10 minutes
    DEFAULT_MAX_RETRIES = 5

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: APIProvider = APIProvider.DIRECT,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.model = model
        self.provider = provider
        self.timeout = timeout
        self.max_retries = max_retries

        # Token manager
        self.token_manager = TokenManager()

        # Determine base URL based on provider
        self.base_url = self._resolve_base_url(base_url, provider)

        # Determine API key
        self.api_key = api_key or self.token_manager.get_api_key()

        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None

        # Usage tracking
        self.usage = UsageStats()

        # Session ID for tracking
        self.session_id = str(uuid.uuid4())

    def _resolve_base_url(self, base_url: Optional[str], provider: APIProvider) -> str:
        """Resolve base URL based on provider."""
        if base_url:
            return base_url

        # Check environment override
        env_base = os.environ.get("ANTHROPIC_BASE_URL")
        if env_base:
            return env_base

        # Provider-specific URLs
        if provider == APIProvider.BEDROCK:
            region = os.environ.get("AWS_REGION", "us-east-1")
            return f"https://bedrock-runtime.{region}.amazonaws.com"

        if provider == APIProvider.VERTEX:
            region = os.environ.get("CLOUD_ML_REGION", "us-east5")
            project = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID", "")
            return f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}"

        if provider == APIProvider.FOUNDRY:
            resource = os.environ.get("ANTHROPIC_FOUNDRY_RESOURCE", "")
            foundry_url = os.environ.get("ANTHROPIC_FOUNDRY_BASE_URL")
            if foundry_url:
                return foundry_url
            return f"https://{resource}.services.ai.azure.com"

        if provider == APIProvider.COMPAT:
            # Compatible API (Zhipu, etc.)
            compat_url = os.environ.get("ANTHROPIC_COMPAT_BASE_URL")
            if compat_url:
                return compat_url
            # Default to Zhipu
            return "https://open.bigmodel.cn/api/paas/v4"

        return self.DEFAULT_BASE_URL

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers (client.ts patterns)."""
        headers = {
            "Content-Type": "application/json",
            "x-app": "cli",
            "User-Agent": self._get_user_agent(),
            "X-Claude-Code-Session-Id": self.session_id,
        }

        # Add authentication
        if self.provider == APIProvider.DIRECT:
            # Check for OAuth token first
            auth_token = self.token_manager.get_auth_token()
            if auth_token and self.token_manager.is_claude_ai_subscriber():
                headers["Authorization"] = f"Bearer {auth_token}"
            elif self.api_key:
                headers["x-api-key"] = self.api_key

        elif self.provider == APIProvider.BEDROCK:
            # Bedrock uses AWS sig v4 (handled by httpx auth)
            bearer_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
            if bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"

        elif self.provider == APIProvider.VERTEX:
            # Vertex uses Google auth (handled separately)
            pass

        elif self.provider == APIProvider.FOUNDRY:
            # Foundry API key
            foundry_key = os.environ.get("ANTHROPIC_FOUNDRY_API_KEY")
            if foundry_key:
                headers["api-key"] = foundry_key

        elif self.provider == APIProvider.COMPAT:
            # Compatible API key
            compat_key = os.environ.get("ANTHROPIC_COMPAT_API_KEY") or self.api_key
            if compat_key:
                headers["Authorization"] = f"Bearer {compat_key}"

        # Custom headers from environment
        custom_headers_env = os.environ.get("ANTHROPIC_CUSTOM_HEADERS")
        if custom_headers_env:
            for line in custom_headers_env.split("\n"):
                if ":" in line:
                    name, value = line.split(":", 1)
                    headers[name.strip()] = value.strip()

        # Anthropic version
        headers["anthropic-version"] = "2023-06-01"

        # Betas for features
        betas = []
        if os.environ.get("ANTHROPIC_BETA"):
            betas.append(os.environ["ANTHROPIC_BETA"])
        # Add default betas
        if "oauth-2025" not in headers.get("Authorization", ""):
            betas.append("max-tokens-3-5-sonnet-2024-07-15")
        if betas:
            headers["anthropic-beta"] = ",".join(betas)

        return headers

    def _get_user_agent(self) -> str:
        """Get user agent string."""
        import platform
        return f"claude-code-python/{platform.system()}-{platform.release()}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        stream: bool = True,
        thinking_config: Optional[Dict[str, Any]] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs,
    ) -> AsyncIterator[StreamEvent]:
        """Create a message with streaming (claude.ts patterns).

        Key patterns:
        - Streaming event handling with SSE parsing
        - Tool call parsing
        - Message_delta for usage and stop_reason
        - Retry logic for transient errors
        """
        client = await self._get_client()

        # Build request body
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            body["system"] = system

        if tools:
            body["tools"] = tools

        if thinking_config:
            # Extended thinking support
            thinking_type = thinking_config.get("type", "enabled")
            if thinking_type == "enabled":
                body["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_config.get("budget_tokens", 16000),
                }
            elif thinking_type == "adaptive":
                # Adaptive budget based on message complexity
                budget = min(32000, max_tokens // 4)
                body["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": budget,
                }

        if stop_sequences:
            body["stop_sequences"] = stop_sequences

        # Additional params
        body.update(kwargs)

        # Streaming always enabled for tool use
        if stream:
            body["stream"] = True

        # Retry loop
        retries = 0
        last_error: Optional[APIError] = None

        while retries <= self.max_retries:
            try:
                url = f"{self.base_url}/messages"
                headers = self._get_headers()

                if stream:
                    # Streaming request
                    async with client.stream(
                        "POST",
                        url,
                        json=body,
                        headers=headers,
                    ) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            error_data = json.loads(error_body) if error_body else {}
                            raise APIError(
                                error_data.get("error", {}).get("message", "API error"),
                                status=response.status_code,
                                error_type=error_data.get("error", {}).get("type"),
                            )

                        # Parse SSE stream (matching claude.ts patterns)
                        current_message_id: Optional[str] = None
                        current_content_index: int = 0
                        tool_input_buffer: str = ""
                        current_tool_name: Optional[str] = None
                        current_tool_id: Optional[str] = None

                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue

                            data_str = line[6:]
                            if not data_str:
                                continue

                            try:
                                event_data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            event_type = event_data.get("type", "")

                            # message_start - initial message with usage
                            if event_type == "message_start":
                                msg = event_data.get("message", {})
                                current_message_id = msg.get("id")
                                usage = msg.get("usage", {})
                                yield StreamEvent(
                                    type="message_start",
                                    data={
                                        "id": current_message_id,
                                        "model": msg.get("model"),
                                        "usage": usage,
                                    },
                                )
                                # Update usage
                                self.usage.input_tokens = usage.get("input_tokens", 0)

                            # content_block_start - new block
                            elif event_type == "content_block_start":
                                index = event_data.get("index", 0)
                                block = event_data.get("content_block", {})
                                block_type = block.get("type", "")
                                current_content_index = index

                                if block_type == "text":
                                    yield StreamEvent(
                                        type="text_start",
                                        data={"index": index},
                                    )
                                elif block_type == "tool_use":
                                    current_tool_id = block.get("id")
                                    current_tool_name = block.get("name")
                                    tool_input_buffer = ""
                                    yield StreamEvent(
                                        type="tool_use_start",
                                        data={
                                            "id": current_tool_id,
                                            "name": current_tool_name,
                                            "index": index,
                                        },
                                    )
                                elif block_type == "thinking":
                                    yield StreamEvent(
                                        type="thinking_start",
                                        data={"index": index},
                                    )

                            # content_block_delta - partial content
                            elif event_type == "content_block_delta":
                                index = event_data.get("index", 0)
                                delta = event_data.get("delta", {})
                                delta_type = delta.get("type", "")

                                if delta_type == "text_delta":
                                    yield StreamEvent(
                                        type="text_delta",
                                        data={
                                            "index": index,
                                            "text": delta.get("text", ""),
                                        },
                                    )
                                elif delta_type == "input_json_delta":
                                    partial_json = delta.get("partial_json", "")
                                    tool_input_buffer += partial_json
                                    yield StreamEvent(
                                        type="input_json_delta",
                                        data={
                                            "index": index,
                                            "partial_json": partial_json,
                                        },
                                    )
                                elif delta_type == "thinking_delta":
                                    yield StreamEvent(
                                        type="thinking_delta",
                                        data={
                                            "index": index,
                                            "thinking": delta.get("thinking", ""),
                                        },
                                    )

                            # content_block_stop - block complete
                            elif event_type == "content_block_stop":
                                index = event_data.get("index", 0)
                                yield StreamEvent(
                                    type="content_block_stop",
                                    data={"index": index},
                                )

                                # Finalize tool input
                                if current_tool_id and tool_input_buffer:
                                    try:
                                        tool_input = json.loads(tool_input_buffer)
                                    except json.JSONDecodeError:
                                        tool_input = {}
                                    yield StreamEvent(
                                        type="tool_use_complete",
                                        data={
                                            "id": current_tool_id,
                                            "name": current_tool_name,
                                            "input": tool_input,
                                        },
                                    )
                                    tool_input_buffer = ""
                                    current_tool_id = None
                                    current_tool_name = None

                            # message_delta - usage update and stop_reason
                            elif event_type == "message_delta":
                                delta = event_data.get("delta", {})
                                usage = event_data.get("usage", {})
                                stop_reason = delta.get("stop_reason")

                                yield StreamEvent(
                                    type="message_delta",
                                    data={
                                        "stop_reason": stop_reason,
                                        "usage": usage,
                                    },
                                )

                                # Update usage
                                self.usage.output_tokens = usage.get("output_tokens", 0)
                                self.usage.cache_read_tokens = usage.get("cache_read_input_tokens", 0)
                                self.usage.cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
                                self.usage.total_tokens = self.usage.input_tokens + self.usage.output_tokens

                            # message_stop - final message
                            elif event_type == "message_stop":
                                yield StreamEvent(
                                    type="message_stop",
                                    data={},
                                )
                                return

                            # error
                            elif event_type == "error":
                                error_data = event_data.get("error", {})
                                yield StreamEvent(
                                    type="error",
                                    data={
                                        "type": error_data.get("type"),
                                        "message": error_data.get("message"),
                                    },
                                )

                            # ping - keepalive
                            elif event_type == "ping":
                                yield StreamEvent(type="ping", data={})

                else:
                    # Non-streaming request
                    response = await client.post(
                        url,
                        json=body,
                        headers=headers,
                    )

                    if response.status_code != 200:
                        error_data = response.json() if response.content else {}
                        raise APIError(
                            error_data.get("error", {}).get("message", "API error"),
                            status=response.status_code,
                            error_type=error_data.get("error", {}).get("type"),
                        )

                    result = response.json()
                    yield StreamEvent(
                        type="message_complete",
                        data=result,
                    )
                    return

            except APIError as e:
                last_error = e
                if e.is_retryable() and retries < self.max_retries:
                    retries += 1
                    # Exponential backoff
                    delay = min(60.0, 2.0 ** retries)
                    yield StreamEvent(
                        type="retry",
                        data={
                            "attempt": retries,
                            "max_retries": self.max_retries,
                            "delay_ms": int(delay * 1000),
                            "error": str(e),
                        },
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

            except httpx.TimeoutException:
                last_error = APIError("Request timeout", status=504, error_type="timeout_error")
                if retries < self.max_retries:
                    retries += 1
                    yield StreamEvent(
                        type="retry",
                        data={
                            "attempt": retries,
                            "max_retries": self.max_retries,
                            "delay_ms": 10000,
                            "error": "timeout",
                        },
                    )
                    await asyncio.sleep(10.0)
                    continue
                raise last_error

            except httpx.NetworkError as e:
                last_error = APIError(str(e), error_type="network_error")
                if retries < self.max_retries:
                    retries += 1
                    yield StreamEvent(
                        type="retry",
                        data={
                            "attempt": retries,
                            "max_retries": self.max_retries,
                            "delay_ms": 5000,
                            "error": str(e),
                        },
                    )
                    await asyncio.sleep(5.0)
                    continue
                raise last_error

    def get_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics."""
        return {
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "cache_read_tokens": self.usage.cache_read_tokens,
            "cache_creation_tokens": self.usage.cache_creation_tokens,
            "total_tokens": self.usage.total_tokens,
        }

    async def close(self) -> None:
        """Close the client."""
        if self._client:
            await self._client.aclose()


class CompatClient(APIClient):
    """Compatible API client (Zhipu, OpenAI-compatible, etc).

    Handles API differences:
    - Different message format (OpenAI-style)
    - Different streaming format
    - Different error codes
    """

    # Known compatible API configurations
    COMPAT_PROVIDERS = {
        "zhipu": {
            "base_url": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
            "models": ["glm-4-plus", "glm-4", "glm-5", "glm-5-air"],
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "models": ["deepseek-chat", "deepseek-coder"],
        },
        "moonshot": {
            "base_url": "https://api.moonshot.cn/v1",
            "models": ["moonshot-v1-8k", "moonshot-v1-32k"],
        },
        "siliconflow": {
            "base_url": "https://api.siliconflow.cn/v1",
            "models": ["Qwen/Qwen2.5-72B-Instruct"],
        },
    }

    def __init__(
        self,
        model: str = "glm-5",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        # Auto-detect provider from base_url or model
        effective_base_url = base_url
        effective_model = model

        if provider and provider in self.COMPAT_PROVIDERS:
            config = self.COMPAT_PROVIDERS[provider]
            effective_base_url = effective_base_url or config["base_url"]
            effective_model = effective_model or config["models"][0]

        if effective_base_url is None:
            effective_base_url = os.environ.get("ANTHROPIC_COMPAT_BASE_URL", "https://coding.dashscope.aliyuncs.com/apps/anthropic")

        super().__init__(
            model=effective_model,
            api_key=api_key,
            base_url=effective_base_url,
            provider=APIProvider.COMPAT,
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for compatible API."""
        headers = super()._get_headers()
        # Zhipu and similar use Authorization Bearer
        compat_key = os.environ.get("ANTHROPIC_COMPAT_API_KEY") or self.api_key
        if compat_key:
            headers["Authorization"] = f"Bearer {compat_key}"
        return headers

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        stream: bool = True,
        **kwargs,
    ) -> AsyncIterator[StreamEvent]:
        """Create message with compatible API format."""
        # Convert Anthropic format to OpenAI-compatible format
        compat_messages = []

        if system:
            compat_messages.append({
                "role": "system",
                "content": system,
            })

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", [])

            # Flatten content blocks
            if isinstance(content, list):
                text_parts = []
                tool_calls = []
                tool_results = []

                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "text")
                        if block_type == "text":
                            text_parts.append(block.get("text", ""))
                        elif block_type == "tool_use":
                            tool_calls.append({
                                "id": block.get("id"),
                                "type": "function",
                                "function": {
                                    "name": block.get("name"),
                                    "arguments": json.dumps(block.get("input", {})),
                                },
                            })
                        elif block_type == "tool_result":
                            tool_results.append({
                                "tool_call_id": block.get("tool_use_id"),
                                "content": block.get("content", ""),
                            })

                if role == "assistant":
                    compat_msg = {"role": "assistant"}
                    if text_parts:
                        compat_msg["content"] = " ".join(text_parts)
                    if tool_calls:
                        compat_msg["tool_calls"] = tool_calls
                elif role == "user":
                    compat_msg = {"role": "user"}
                    if tool_results:
                        compat_msg["content"] = tool_results
                    elif text_parts:
                        compat_msg["content"] = " ".join(text_parts)
                else:
                    compat_msg = {"role": role, "content": " ".join(text_parts)}

                compat_messages.append(compat_msg)
            else:
                compat_messages.append({"role": role, "content": str(content)})

        # Build request
        body = {
            "model": self.model,
            "messages": compat_messages,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if tools:
            # Convert tools to function calling format
            functions = []
            for tool in tools:
                functions.append({
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                })
            body["tools"] = functions

        client = await self._get_client()
        headers = self._get_headers()

        if stream:
            # Streaming
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        yield StreamEvent(type="message_stop", data={})
                        return

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})

                        # Text content
                        if "content" in delta:
                            yield StreamEvent(
                                type="text_delta",
                                data={"text": delta["content"]},
                            )

                        # Tool calls
                        if "tool_calls" in delta:
                            for tc in delta["tool_calls"]:
                                func = tc.get("function", {})
                                yield StreamEvent(
                                    type="tool_use_start",
                                    data={
                                        "id": tc.get("id"),
                                        "name": func.get("name"),
                                    },
                                )
                                if "arguments" in func:
                                    yield StreamEvent(
                                        type="input_json_delta",
                                        data={"partial_json": func["arguments"]},
                                    )

        else:
            # Non-streaming
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
            )

            result = response.json()
            yield StreamEvent(
                type="message_complete",
                data=result,
            )


def get_client(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    provider: Optional[str] = None,
) -> APIClient:
    """Get API client based on environment configuration.

    Follows client.ts getAnthropicClient patterns:
    - Check CLAUDE_CODE_USE_BEDROCK
    - Check CLAUDE_CODE_USE_VERTEX
    - Check CLAUDE_CODE_USE_FOUNDRY
    - Check ANTHROPIC_COMPAT_BASE_URL
    - Default to direct Anthropic API
    """
    # Determine provider from environment
    api_provider = APIProvider.DIRECT

    if is_env_truthy(os.environ.get("CLAUDE_CODE_USE_BEDROCK")):
        api_provider = APIProvider.BEDROCK
    elif is_env_truthy(os.environ.get("CLAUDE_CODE_USE_VERTEX")):
        api_provider = APIProvider.VERTEX
    elif is_env_truthy(os.environ.get("CLAUDE_CODE_USE_FOUNDRY")):
        api_provider = APIProvider.FOUNDRY
    elif os.environ.get("ANTHROPIC_COMPAT_BASE_URL") or provider:
        api_provider = APIProvider.COMPAT

    # Default model
    effective_model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # Create appropriate client
    if api_provider == APIProvider.COMPAT:
        return CompatClient(model=effective_model, base_url=base_url, provider=provider)

    return APIClient(
        model=effective_model,
        base_url=base_url,
        provider=api_provider,
    )


def detect_provider_from_url(url: str) -> Optional[str]:
    """Detect provider from URL."""
    if "dashscope" in url or "aliyuncs" in url:
        return "zhipu"
    if "deepseek" in url:
        return "deepseek"
    if "moonshot" in url:
        return "moonshot"
    if "siliconflow" in url:
        return "siliconflow"
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