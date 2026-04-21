"""Token Warning Widget - Token limit warnings."""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from .token_bar import TokenUsage


class WarningLevel(Enum):
    """Warning levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class TokenWarningConfig:
    """Token warning configuration."""
    warn_threshold: float = 80.0
    critical_threshold: float = 90.0
    emergency_threshold: float = 95.0
    show_suggestion: bool = True
    show_percentage: bool = True


class TokenWarningWidget:
    """Widget to display token warnings."""
    
    def __init__(self, config: TokenWarningConfig = None):
        self.config = config or TokenWarningConfig()
        self._usage: Optional[TokenUsage] = None
    
    def set_usage(self, usage: TokenUsage) -> None:
        """Set token usage."""
        self._usage = usage
    
    def get_level(self) -> WarningLevel:
        """Get warning level."""
        if not self._usage:
            return WarningLevel.INFO
        
        percentage = self._usage.percentage
        
        if percentage >= self.config.emergency_threshold:
            return WarningLevel.EMERGENCY
        elif percentage >= self.config.critical_threshold:
            return WarningLevel.CRITICAL
        elif percentage >= self.config.warn_threshold:
            return WarningLevel.WARNING
        
        return WarningLevel.INFO
    
    def render(self) -> str:
        """Render warning."""
        if not self._usage:
            return ""
        
        level = self.get_level()
        
        if level == WarningLevel.INFO:
            return ""
        
        lines = []
        
        # Warning header
        header = self._get_warning_header(level)
        lines.append(header)
        
        # Usage info
        if self.config.show_percentage:
            lines.append(f"Token usage: {self._usage.percentage:.1f}%")
            lines.append(f"{self._usage.used} / {self._usage.total} tokens used")
        
        # Suggestion
        if self.config.show_suggestion:
            suggestion = self._get_suggestion(level)
            lines.append(suggestion)
        
        return "\n".join(lines)
    
    def _get_warning_header(self, level: WarningLevel) -> str:
        """Get warning header."""
        headers = {
            WarningLevel.WARNING: "⚠️ Token Usage Warning",
            WarningLevel.CRITICAL: "🚨 Token Usage Critical",
            WarningLevel.EMERGENCY: "🔴 Token Limit Reached",
        }
        return headers.get(level, "")
    
    def _get_suggestion(self, level: WarningLevel) -> str:
        """Get suggestion."""
        suggestions = {
            WarningLevel.WARNING: "Consider using /compact to reduce context.",
            WarningLevel.CRITICAL: "Use /compact now or start a new session.",
            WarningLevel.EMERGENCY: "Start a new session to avoid truncation.",
        }
        return suggestions.get(level, "")
    
    def is_warning(self) -> bool:
        """Check if at warning level."""
        return self.get_level() >= WarningLevel.WARNING
    
    def is_critical(self) -> bool:
        """Check if at critical level."""
        return self.get_level() >= WarningLevel.CRITICAL
    
    def is_emergency(self) -> bool:
        """Check if at emergency level."""
        return self.get_level() == WarningLevel.EMERGENCY
    
    def get_remaining_tokens(self) -> int:
        """Get remaining tokens."""
        if not self._usage:
            return 0
        return self._usage.total - self._usage.used


__all__ = [
    "WarningLevel",
    "TokenWarningConfig",
    "TokenWarningWidget",
]
