"""Thinking Utilities - Extended thinking support."""

from __future__ import annotations
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ..services.token_estimation import estimate_tokens


class ThinkingBudgetMode(Enum):
    """Thinking budget modes."""
    DEFAULT = "default"  # 31,999 tokens
    MINIMAL = "minimal"  # 1,000 tokens
    MAXIMUM = "maximum"  # Full budget
    DISABLED = "disabled"  # No thinking


@dataclass
class ThinkingConfig:
    """Extended thinking configuration."""
    enabled: bool = True
    budget_tokens: int = 31999
    max_budget: int = 31999
    min_budget: int = 1000
    mode: ThinkingBudgetMode = ThinkingBudgetMode.DEFAULT


@dataclass
class ThinkingBlock:
    """Thinking content block."""
    content: str
    tokens_used: int
    duration_ms: float
    truncated: bool = False


class ThinkingManager:
    """Manage extended thinking."""

    def __init__(self, config: ThinkingConfig = None):
        self.config = config or ThinkingConfig()
        self._current_thinking: Optional[ThinkingBlock] = None
        self._thinking_history: List[...] = field(default_factory=list)

    def is_enabled(self) -> bool:
        """Check if thinking is enabled."""
        return self.config.enabled

    def get_budget_tokens(self) -> int:
        """Get thinking budget."""
        if not self.config.enabled:
            return 0

        return self.config.budget_tokens

    def set_budget(self, budget: int) -> None:
        """Set thinking budget."""
        self.config.budget_tokens = min(budget, self.config.max_budget)
        self.config.budget_tokens = max(self.config.budget_tokens, self.config.min_budget)

    def enable(self) -> None:
        """Enable thinking."""
        self.config.enabled = True
        self.config.mode = ThinkingBudgetMode.DEFAULT

    def disable(self) -> None:
        """Disable thinking."""
        self.config.enabled = False
        self.config.mode = ThinkingBudgetMode.DISABLED

    def set_mode(self, mode: ThinkingBudgetMode) -> None:
        """Set thinking mode."""
        self.config.mode = mode

        if mode == ThinkingBudgetMode.DISABLED:
            self.config.enabled = False
        elif mode == ThinkingBudgetMode.MINIMAL:
            self.config.budget_tokens = self.config.min_budget
        elif mode == ThinkingBudgetMode.MAXIMUM:
            self.config.budget_tokens = self.config.max_budget
        else:
            self.config.budget_tokens = 31999

    async def estimate_thinking_tokens(self, thinking: str) -> int:
        """Estimate tokens for thinking."""
        return await estimate_tokens(thinking)

    def start_thinking(self) -> None:
        """Start thinking session."""
        self._current_thinking = ThinkingBlock(
            content="",
            tokens_used=0,
            duration_ms=0,
        )

    def add_thinking_content(self, content: str, duration_ms: float) -> None:
        """Add thinking content."""
        if self._current_thinking:
            self._current_thinking.content += content
            self._current_thinking.duration_ms = duration_ms

    async def finalize_thinking(self) -> Optional[ThinkingBlock]:
        """Finalize thinking."""
        if self._current_thinking:
            self._current_thinking.tokens_used = await self.estimate_thinking_tokens(
                self._current_thinking.content
            )

            # Check for truncation
            if self._current_thinking.tokens_used > self.config.budget_tokens:
                self._current_thinking.truncated = True
                # Would truncate content

            self._thinking_history.append(self._current_thinking)
            result = self._current_thinking
            self._current_thinking = None
            return result

        return None

    def get_history(self) -> List[ThinkingBlock]:
        """Get thinking history."""
        return self._thinking_history

    def clear_history(self) -> None:
        """Clear thinking history."""
        self._thinking_history.clear()


def parse_thinking_from_response(response: Dict) -> Optional[str]:
    """Parse thinking content from API response."""
    content = response.get("content", [])

    for block in content:
        if block.get("type") == "thinking":
            return block.get("thinking", "")

    return None


def format_thinking_for_api(thinking: str, budget: int) -> Dict:
    """Format thinking for API request."""
    return {
        "type": "thinking",
        "thinking": thinking,
        "budget_tokens": budget,
    }


def should_use_thinking(task_type: str) -> bool:
    """Determine if thinking should be used for task type."""
    # Tasks that benefit from extended thinking
    thinking_tasks = [
        "architecture",
        "planning",
        "debugging",
        "refactoring",
        "complex_logic",
        "security_analysis",
        "code_review",
    ]

    # Tasks that don't need extended thinking
    simple_tasks = [
        "simple_edit",
        "formatting",
        "documentation",
        "quick_fix",
    ]

    if task_type in thinking_tasks:
        return True
    if task_type in simple_tasks:
        return False

    # Default to moderate thinking
    return True


def get_thinking_budget_for_task(task_type: str) -> int:
    """Get appropriate thinking budget for task."""
    if task_type == "architecture":
        return 20000
    elif task_type == "planning":
        return 15000
    elif task_type == "debugging":
        return 10000
    elif task_type in ["simple_edit", "formatting"]:
        return 0
    else:
        return 5000


__all__ = [
    "ThinkingBudgetMode",
    "ThinkingConfig",
    "ThinkingBlock",
    "ThinkingManager",
    "parse_thinking_from_response",
    "format_thinking_for_api",
    "should_use_thinking",
    "get_thinking_budget_for_task",
]