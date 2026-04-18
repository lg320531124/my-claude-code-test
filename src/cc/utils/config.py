"""Configuration management."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..types.permission import PermissionConfig


class APIConfig(BaseModel):
    """API configuration."""

    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    base_url: str | None = None
    max_tokens: int = 8192


class UIConfig(BaseModel):
    """UI configuration."""

    theme: str = "dark"
    output_style: str = "explanatory"


class Config(BaseModel):
    """Main configuration."""

    api: APIConfig = APIConfig()
    permissions: PermissionConfig = PermissionConfig()
    ui: UIConfig = UIConfig()

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load configuration from file."""
        if path is None:
            path = cls.get_default_path()

        if path.exists():
            try:
                data = json.loads(path.read_text())
                return cls.model_validate(data)
            except Exception:
                pass

        return cls()

    @classmethod
    def get_default_path(cls) -> Path:
        """Get default config path."""
        return Path.home() / ".claude-code-py" / "config.json"

    def save(self, path: Path | None = None) -> None:
        """Save configuration to file."""
        if path is None:
            path = self.get_default_path()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.model_dump(), indent=2))

    def get_env_overrides(self) -> dict[str, Any]:
        """Get environment variable overrides."""
        import os

        overrides: dict[str, Any] = {}

        # API key
        if "ANTHROPIC_API_KEY" in os.environ:
            overrides["api_key"] = os.environ["ANTHROPIC_API_KEY"]

        # Base URL (for compatible APIs like 智谱)
        if "ANTHROPIC_BASE_URL" in os.environ:
            overrides["base_url"] = os.environ["ANTHROPIC_BASE_URL"]

        # Model override
        if "ANTHROPIC_MODEL" in os.environ:
            overrides["model"] = os.environ["ANTHROPIC_MODEL"]

        return overrides