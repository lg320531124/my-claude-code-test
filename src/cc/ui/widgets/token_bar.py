"""Token Bar Widget - Token usage progress bar."""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class TokenBarStyle(Enum):
    """Token bar styles."""
    SIMPLE = "simple"
    DETAILED = "detailed"
    MINIMAL = "minimal"


@dataclass
class TokenUsage:
    """Token usage info."""
    used: int = 0
    total: int = 200000
    percentage: float = 0.0
    
    def __post_init__(self):
        if self.total > 0:
            self.percentage = (self.used / self.total) * 100


@dataclass
class TokenBarConfig:
    """Token bar configuration."""
    style: TokenBarStyle = TokenBarStyle.SIMPLE
    show_percentage: bool = True
    show_numbers: bool = True
    warn_threshold: float = 80.0
    critical_threshold: float = 95.0
    width: int = 30


class TokenBarWidget:
    """Widget to display token usage as progress bar."""
    
    def __init__(self, config: TokenBarConfig = None):
        self.config = config or TokenBarConfig()
        self._usage = TokenUsage()
    
    def set_usage(self, used: int, total: int = 200000) -> None:
        """Set token usage."""
        self._usage = TokenUsage(used=used, total=total)
    
    def render(self) -> str:
        """Render token bar."""
        usage = self._usage
        
        # Determine color based on threshold
        if usage.percentage >= self.config.critical_threshold:
            color = "\033[31m"  # Red
        elif usage.percentage >= self.config.warn_threshold:
            color = "\033[33m"  # Yellow
        else:
            color = "\033[32m"  # Green
        
        # Build bar
        filled = int((usage.percentage / 100) * self.config.width)
        empty = self.config.width - filled
        
        bar = color + "█" * filled + "\033[0m" + "░" * empty
        
        if self.config.style == TokenBarStyle.MINIMAL:
            return bar
        
        elif self.config.style == TokenBarStyle.DETAILED:
            return f"Tokens: {bar} {usage.used}/{usage.total} ({usage.percentage:.1f}%)"
        
        else:  # SIMPLE
            if self.config.show_percentage:
                return f"{bar} {usage.percentage:.1f}%"
            return bar
    
    def get_status(self) -> str:
        """Get token status."""
        if self._usage.percentage >= self.config.critical_threshold:
            return "critical"
        elif self._usage.percentage >= self.config.warn_threshold:
            return "warning"
        return "normal"
    
    def is_warning(self) -> bool:
        """Check if at warning level."""
        return self._usage.percentage >= self.config.warn_threshold
    
    def is_critical(self) -> bool:
        """Check if at critical level."""
        return self._usage.percentage >= self.config.critical_threshold


# Global token bar
_token_bar: Optional[TokenBarWidget] = None


def get_token_bar() -> TokenBarWidget:
    """Get global token bar widget."""
    global _token_bar
    if _token_bar is None:
        _token_bar = TokenBarWidget()
    return _token_bar


def update_token_usage(used: int, total: int = 200000) -> None:
    """Update global token usage."""
    get_token_bar().set_usage(used, total)


__all__ = [
    "TokenBarStyle",
    "TokenUsage",
    "TokenBarConfig",
    "TokenBarWidget",
    "get_token_bar",
    "update_token_usage",
]
