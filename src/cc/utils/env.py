"""Environment Utilities - Environment variable handling.

Provides environment variable management, truthy/falsy checks,
Claude config directory resolution, and region configuration.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class EnvironmentInfo:
    """Environment information."""
    key: str
    value: str
    source: str = "system"  # system, user, project, override


def is_env_truthy(env_var: Optional[str | bool]) -> bool:
    """Check if environment variable is truthy."""
    if not env_var:
        return False
    if isinstance(env_var, bool):
        return env_var
    normalized = env_var.lower().strip()
    return normalized in ("1", "true", "yes", "on")


def is_env_defined_falsy(env_var: Optional[str | bool]) -> bool:
    """Check if environment variable is explicitly falsy."""
    if env_var is None:
        return False
    if isinstance(env_var, bool):
        return not env_var
    if not env_var:
        return False
    normalized = env_var.lower().strip()
    return normalized in ("0", "false", "no", "off")


@lru_cache(maxsize=1)
def get_claude_config_home_dir() -> Path:
    """Get Claude config home directory (memoized)."""
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        return Path(config_dir)
    return Path.home() / ".claude"


def get_teams_dir() -> Path:
    """Get teams directory."""
    return get_claude_config_home_dir() / "teams"


def is_bare_mode() -> bool:
    """Check if running in bare/simple mode."""
    return is_env_truthy(os.environ.get("CLAUDE_CODE_SIMPLE")) or "--bare" in sys.argv


def has_node_option(flag: str) -> bool:
    """Check if NODE_OPTIONS contains a specific flag."""
    node_options = os.environ.get("NODE_OPTIONS")
    if not node_options:
        return False
    return flag in node_options.split()


def parse_env_vars(raw_env_args: Optional[List[str]]) -> Dict[str, str]:
    """Parse environment variable strings into key-value object."""
    parsed_env: Dict[str, str] = {}
    if raw_env_args:
        for env_str in raw_env_args:
            if "=" not in env_str:
                raise ValueError(
                    f"Invalid environment variable format: {env_str}, "
                    "environment variables should be added as: -e KEY1=value1 -e KEY2=value2"
                )
            key, value = env_str.split("=", 1)
            parsed_env[key] = value
    return parsed_env


def get_aws_region() -> str:
    """Get AWS region with fallback to default."""
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def get_default_vertex_region() -> str:
    """Get default Vertex AI region."""
    return os.environ.get("CLOUD_ML_REGION") or "us-east5"


# Vertex region overrides for specific models
VERTEX_REGION_OVERRIDES: List[Tuple[str, str]] = [
    ("claude-haiku-4-5", "VERTEX_REGION_CLAUDE_HAIKU_4_5"),
    ("claude-3-5-haiku", "VERTEX_REGION_CLAUDE_3_5_HAIKU"),
    ("claude-3-5-sonnet", "VERTEX_REGION_CLAUDE_3_5_SONNET"),
    ("claude-3-7-sonnet", "VERTEX_REGION_CLAUDE_3_7_SONNET"),
    ("claude-opus-4-1", "VERTEX_REGION_CLAUDE_4_1_OPUS"),
    ("claude-opus-4", "VERTEX_REGION_CLAUDE_4_0_OPUS"),
    ("claude-sonnet-4-6", "VERTEX_REGION_CLAUDE_4_6_SONNET"),
    ("claude-sonnet-4-5", "VERTEX_REGION_CLAUDE_4_5_SONNET"),
    ("claude-sonnet-4", "VERTEX_REGION_CLAUDE_4_0_SONNET"),
]


def get_vertex_region_for_model(model: Optional[str]) -> str:
    """Get Vertex AI region for a specific model."""
    if model:
        for prefix, env_var in VERTEX_REGION_OVERRIDES:
            if model.startswith(prefix):
                return os.environ.get(env_var) or get_default_vertex_region()
    return get_default_vertex_region()


def should_maintain_project_working_dir() -> bool:
    """Check if bash should maintain project working directory."""
    return is_env_truthy(os.environ.get("CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR"))


def is_running_on_homespace() -> bool:
    """Check if running on Homespace."""
    return os.environ.get("USER_TYPE") == "ant" and is_env_truthy(os.environ.get("COO_RUNNING_ON_HOMESPACE"))


class EnvironmentManager:
    """Manage environment variables."""

    def __init__(self):
        self._overrides: Dict[str, str] = {}
        self._project_env: Dict[str, str] = {}
        self._user_env: Dict[str, str] = {}

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable (with overrides)."""
        # Priority: overrides > project > user > system
        if key in self._overrides:
            return self._overrides[key]
        if key in self._project_env:
            return self._project_env[key]
        if key in self._user_env:
            return self._user_env[key]
        return os.environ.get(key, default)

    def set_override(self, key: str, value: str) -> None:
        """Set override value."""
        self._overrides[key] = value

    def set_project_env(self, key: str, value: str) -> None:
        """Set project environment."""
        self._project_env[key] = value

    def set_user_env(self, key: str, value: str) -> None:
        """Set user environment."""
        self._user_env[key] = value

    def clear_override(self, key: str) -> None:
        """Clear override."""
        if key in self._overrides:
            del self._overrides[key]

    def get_all(self) -> Dict[str, EnvironmentInfo]:
        """Get all environment variables."""
        result: Dict[str, EnvironmentInfo] = {}

        # System env
        for key, value in os.environ.items():
            result[key] = EnvironmentInfo(key=key, value=value, source="system")

        # User env (override)
        for key, value in self._user_env.items():
            result[key] = EnvironmentInfo(key=key, value=value, source="user")

        # Project env (override)
        for key, value in self._project_env.items():
            result[key] = EnvironmentInfo(key=key, value=value, source="project")

        # Overrides (highest priority)
        for key, value in self._overrides.items():
            result[key] = EnvironmentInfo(key=key, value=value, source="override")

        return result

    def get_api_key(self) -> Optional[str]:
        """Get Anthropic API key."""
        return self.get("ANTHROPIC_API_KEY")

    def get_base_url(self) -> Optional[str]:
        """Get API base URL."""
        return self.get("ANTHROPIC_BASE_URL")

    def get_model_override(self) -> Optional[str]:
        """Get model override."""
        return self.get("ANTHROPIC_MODEL")

    def is_debug(self) -> bool:
        """Check if debug mode."""
        return is_env_truthy(self.get("CLAUDE_DEBUG"))

    def get_home(self) -> str:
        """Get home directory."""
        return self.get("HOME", os.path.expanduser("~")) or ""

    def get_cwd(self) -> str:
        """Get current working directory."""
        return os.getcwd()

    def load_from_file(self, path: str) -> int:
        """Load environment from file (.env format)."""
        env_file = Path(path)
        if not env_file.exists():
            return 0

        count = 0
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                self.set_project_env(key, value)
                count += 1

        return count


# Global environment manager
_env_manager: Optional[EnvironmentManager] = None


def get_env_manager() -> EnvironmentManager:
    """Get global environment manager."""
    global _env_manager
    if _env_manager is None:
        _env_manager = EnvironmentManager()
    return _env_manager


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable."""
    return get_env_manager().get(key, default)


def reset_env_manager() -> None:
    """Reset environment manager (for tests)."""
    global _env_manager
    _env_manager = None
    get_claude_config_home_dir.cache_clear()


__all__ = [
    "EnvironmentInfo",
    "EnvironmentManager",
    "get_env_manager",
    "get_env",
    "reset_env_manager",
    "is_env_truthy",
    "is_env_defined_falsy",
    "get_claude_config_home_dir",
    "get_teams_dir",
    "is_bare_mode",
    "has_node_option",
    "parse_env_vars",
    "get_aws_region",
    "get_default_vertex_region",
    "get_vertex_region_for_model",
    "VERTEX_REGION_OVERRIDES",
    "should_maintain_project_working_dir",
    "is_running_on_homespace",
]
