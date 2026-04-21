"""Environment Utilities - Environment variable handling."""

from __future__ import annotations
import os
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class EnvironmentInfo:
    """Environment information."""
    key: str
    value: str
    source: str = "system"  # system, user, project, override


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
        return self.get("CLAUDE_DEBUG", "false").lower() == "true"
    
    def get_home(self) -> str:
        """Get home directory."""
        return self.get("HOME", os.path.expanduser("~"))
    
    def get_cwd(self) -> str:
        """Get current working directory."""
        return os.getcwd()
    
    def load_from_file(self, path: str) -> int:
        """Load environment from file (.env format)."""
        import pathlib
        env_file = pathlib.Path(path)
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


__all__ = [
    "EnvironmentInfo",
    "EnvironmentManager",
    "get_env_manager",
    "get_env",
]
