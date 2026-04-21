"""Thinking Module - Extended thinking budget management."""

from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ThinkingMode(Enum):
    """Thinking modes."""
    OFF = "off"
    MINIMAL = "minimal"
    MEDIUM = "medium"
    HIGH = "high"
    MAX = "max"


@dataclass
class ThinkingConfig:
    """Thinking configuration."""
    enabled: bool = True
    budget_tokens: int = 10000
    max_budget: int = 31999
    mode: ThinkingMode = ThinkingMode.MEDIUM


@dataclass
class ThinkingResult:
    """Thinking result."""
    thinking: str
    budget_used: int
    budget_remaining: int


class ThinkingBudgetManager:
    """Manage extended thinking budget."""

    DEFAULT_BUDGETS = {
        ThinkingMode.OFF: 0,
        ThinkingMode.MINIMAL: 2000,
        ThinkingMode.MEDIUM: 10000,
        ThinkingMode.HIGH: 20000,
        ThinkingMode.MAX: 31999,
    }

    def __init__(self, config: Optional[ThinkingConfig] = None):
        self.config = config or ThinkingConfig()
        self._current_budget: int = self.DEFAULT_BUDGETS[self.config.mode]
        self._used_budget: int = 0
        self._thinking_enabled: bool = self.config.enabled

    def set_mode(self, mode: ThinkingMode) -> None:
        """Set thinking mode."""
        self.config.mode = mode
        self._current_budget = self.DEFAULT_BUDGETS[mode]
        self._thinking_enabled = mode != ThinkingMode.OFF

    def set_budget(self, budget_tokens: int) -> None:
        """Set explicit budget."""
        self._current_budget = min(budget_tokens, self.config.max_budget)
        self._thinking_enabled = self._current_budget > 0

    def get_budget(self) -> int:
        """Get current budget."""
        if not self._thinking_enabled:
            return 0
        return self._current_budget

    def is_enabled(self) -> bool:
        """Check if thinking is enabled."""
        return self._thinking_enabled

    def get_remaining_budget(self) -> int:
        """Get remaining budget."""
        return self._current_budget - self._used_budget

    def record_usage(self, tokens_used: int) -> None:
        """Record budget usage."""
        self._used_budget += tokens_used

    def reset(self) -> None:
        """Reset budget tracking."""
        self._used_budget = 0

    def get_status(self) -> Dict[str, Any]:
        """Get thinking status."""
        return {
            "enabled": self._thinking_enabled,
            "mode": self.config.mode.value,
            "budget": self._current_budget,
            "used": self._used_budget,
            "remaining": self.get_remaining_budget(),
            "percentage_used": self._used_budget / self._current_budget if self._current_budget > 0 else 0,
        }

    def should_include_thinking(self, context_complexity: float = 0.5) -> bool:
        """Decide if thinking should be included."""
        if not self._thinking_enabled:
            return False

        # Include thinking based on context complexity
        if context_complexity > 0.7 and self.config.mode != ThinkingMode.OFF:
            return True

        return self._thinking_enabled

    def estimate_budget_needed(self, problem_type: str) -> int:
        """Estimate budget needed for problem type."""
        estimates = {
            "simple": 1000,
            "moderate": 5000,
            "complex": 15000,
            "architectural": 25000,
            "debugging": 10000,
            "analysis": 20000,
            "code_review": 5000,
        }

        return min(estimates.get(problem_type, 10000), self.config.max_budget)


class ThinkingProcessor:
    """Process thinking content."""

    def __init__(self):
        self._budget_manager: Optional[ThinkingBudgetManager] = None

    def set_budget_manager(self, manager: ThinkingBudgetManager) -> None:
        """Set budget manager."""
        self._budget_manager = manager

    def extract_thinking(self, content: str) -> str:
        """Extract thinking from content."""
        # Look for thinking blocks
        if "<thinking>" in content and "</thinking>" in content:
            start = content.find("<thinking>") + len("<thinking>")
            end = content.find("</thinking>")
            return content[start:end].strip()

        return ""

    def format_thinking_block(self, thinking: str) -> str:
        """Format thinking block."""
        return f"<thinking>\n{thinking}\n</thinking>"

    def strip_thinking(self, content: str) -> str:
        """Strip thinking from content."""
        if "<thinking>" in content and "</thinking>" in content:
            start = content.find("<thinking>")
            end = content.find("</thinking>") + len("</thinking>")
            return content[:start] + content[end:].strip()

        return content

    def get_budget_for_request(self) -> Dict[str, int]:
        """Get thinking budget for API request."""
        if self._budget_manager is None:
            return {}

        budget = self._budget_manager.get_budget()

        if budget > 0:
            return {"budget_tokens": budget}

        return {}


# Global managers
_budget_manager: Optional[ThinkingBudgetManager] = None
_processor: Optional[ThinkingProcessor] = None


def get_thinking_budget_manager(config: ThinkingConfig = None) -> ThinkingBudgetManager:
    """Get global thinking budget manager."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = ThinkingBudgetManager(config)
    return _budget_manager


def get_thinking_processor() -> ThinkingProcessor:
    """Get global thinking processor."""
    global _processor
    if _processor is None:
        _processor = ThinkingProcessor()
    return _processor


__all__ = [
    "ThinkingMode",
    "ThinkingConfig",
    "ThinkingResult",
    "ThinkingBudgetManager",
    "ThinkingProcessor",
    "get_thinking_budget_manager",
    "get_thinking_processor",
]