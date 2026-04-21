"""Permission Bar Widget - Permission prompt display."""

from __future__ import annotations
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ...types.permission import PermissionDecision


class PermissionBarStyle(Enum):
    """Permission bar styles."""
    COMPACT = "compact"
    DETAILED = "detailed"
    MINIMAL = "minimal"


@dataclass
class PermissionPrompt:
    """Permission prompt info."""
    tool_name: str
    decision: PermissionDecision = PermissionDecision.ASK
    reason: str = ""
    input_preview: str = ""
    risk_level: str = "medium"
    options: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.options:
            self.options = ["Allow", "Deny", "Ask"]


@dataclass
class PermissionBarConfig:
    """Permission bar configuration."""
    style: PermissionBarStyle = PermissionBarStyle.COMPACT
    show_preview: bool = True
    show_risk: bool = True
    max_preview_length: int = 50


class PermissionBarWidget:
    """Widget to display permission prompts."""
    
    def __init__(self, config: PermissionBarConfig = None):
        self.config = config or PermissionBarConfig()
        self._prompt: Optional[PermissionPrompt] = None
        self._history: List[PermissionPrompt] = []
    
    def show_prompt(self, prompt: PermissionPrompt) -> None:
        """Show permission prompt."""
        self._prompt = prompt
    
    def hide_prompt(self) -> None:
        """Hide current prompt."""
        if self._prompt:
            self._history.append(self._prompt)
            self._prompt = None
    
    def render(self) -> str:
        """Render permission bar."""
        if not self._prompt:
            return ""
        
        prompt = self._prompt
        
        lines = []
        
        # Header
        lines.append(f"🔒 Permission Required: {prompt.tool_name}")
        
        if self.config.style == PermissionBarStyle.DETAILED:
            # Detailed view
            if self.config.show_risk:
                risk_color = self._get_risk_color(prompt.risk_level)
                lines.append(f"   Risk: {risk_color}{prompt.risk_level}\033[0m")
            
            if prompt.reason:
                lines.append(f"   Reason: {prompt.reason}")
            
            if self.config.show_preview and prompt.input_preview:
                preview = prompt.input_preview[:self.config.max_preview_length]
                lines.append(f"   Preview: {preview}")
        
        elif self.config.style == PermissionBarStyle.COMPACT:
            # Compact view
            parts = [f"[{prompt.risk_level}]"]
            if prompt.input_preview:
                preview = prompt.input_preview[:30]
                parts.append(f"{preview}")
            lines.append(" ".join(parts))
        
        # Options
        options_str = " / ".join(prompt.options)
        lines.append(f"   Options: {options_str}")
        
        return "\n".join(lines)
    
    def _get_risk_color(self, risk: str) -> str:
        """Get color for risk level."""
        colors = {
            "low": "\033[32m",
            "medium": "\033[33m",
            "high": "\033[31m",
            "critical": "\033[35m",
        }
        return colors.get(risk, "\033[0m")
    
    def get_prompt(self) -> Optional[PermissionPrompt]:
        """Get current prompt."""
        return self._prompt
    
    def has_prompt(self) -> bool:
        """Check if there's an active prompt."""
        return self._prompt is not None
    
    def get_history(self, limit: int = 10) -> List[PermissionPrompt]:
        """Get permission history."""
        return self._history[-limit:]


# Global permission bar
_permission_bar: Optional[PermissionBarWidget] = None


def get_permission_bar() -> PermissionBarWidget:
    """Get global permission bar widget."""
    global _permission_bar
    if _permission_bar is None:
        _permission_bar = PermissionBarWidget()
    return _permission_bar


__all__ = [
    "PermissionBarStyle",
    "PermissionPrompt",
    "PermissionBarConfig",
    "PermissionBarWidget",
    "get_permission_bar",
]
