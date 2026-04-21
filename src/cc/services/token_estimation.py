"""Token Estimation - Async token counting and budgeting.

Async token estimation for API usage management.
"""

from __future__ import annotations
import asyncio
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TokenUsage:
    """Token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def total(self) -> int:
        """Total tokens."""
        return self.input_tokens + self.output_tokens + self.cache_creation_tokens


@dataclass
class TokenBudget:
    """Token budget configuration."""
    max_input_tokens: int = 100000
    max_output_tokens: int = 4096
    max_total_tokens: int = 200000
    reserve_tokens: int = 5000  # Safety buffer


# Approximate token ratios for estimation
TOKEN_CHARS_RATIO = {
    "en": 4.0,    # ~4 chars per token for English
    "zh": 1.5,    # ~1.5 chars per token for Chinese
    "code": 3.0,  # ~3 chars per token for code
    "default": 4.0,
}


def detect_content_type(content: str) -> str:
    """Detect content type for token estimation."""
    # Check for code patterns
    code_patterns = [
        r"^\s*(def|class|function|import|from|var|let|const)",
        r"^\s*#\s*!",
        r"^\s*\/\*",
        r"^\s*<\?php",
        r"^\s*<!DOCTYPE",
    ]

    for pattern in code_patterns:
        if re.search(pattern, content):
            return "code"

    # Check for Chinese characters
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
    if chinese_chars > len(content) * 0.3:
        return "zh"

    return "en"


def estimate_tokens_sync(content: str) -> int:
    """Synchronous token estimation."""
    if not content:
        return 0

    content_type = detect_content_type(content)
    ratio = TOKEN_CHARS_RATIO.get(content_type, TOKEN_CHARS_RATIO["default"])

    # Count characters
    char_count = len(content)

    # Adjust for whitespace (tokens are more efficient with whitespace)
    whitespace_ratio = len(re.findall(r"\s", content)) / char_count if char_count > 0 else 0
    adjusted_chars = char_count * (1 - whitespace_ratio * 0.2)

    return int(adjusted_chars / ratio)


async def estimate_tokens(content: str) -> int:
    """Async token estimation."""
    # Run in thread pool for large content
    if len(content) > 100000:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, estimate_tokens_sync, content)

    return estimate_tokens_sync(content)


async def estimate_message_tokens(message: Dict[str, Any]) -> TokenUsage:
    """Estimate tokens for a message."""
    total_input = 0

    # Estimate content tokens
    content = message.get("content", "")
    if isinstance(content, str):
        total_input += await estimate_tokens(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    total_input += await estimate_tokens(block.get("text", ""))
                elif block.get("type") == "image":
                    # Images have fixed token cost based on size
                    source = block.get("source", {})
                    media_type = source.get("media_type", "")
                    if "png" in media_type or "jpg" in media_type:
                        # Approximate image tokens
                        total_input += 1000  # Placeholder

    return TokenUsage(input_tokens=total_input)


async def estimate_messages_tokens(messages: list[Dict[str, Any]]) -> TokenUsage:
    """Estimate tokens for multiple messages."""
    total = TokenUsage()

    for message in messages:
        usage = await estimate_message_tokens(message)
        total.input_tokens += usage.input_tokens

    return total


class TokenCounter:
    """Async token counter with caching."""

    def __init__(self):
        self._cache: Dict[str, int] = {}
        self._cache_hits: int = 0

    async def count(self, content: str, use_cache: bool = True) -> int:
        """Count tokens with optional caching."""
        # Check cache
        if use_cache and content in self._cache:
            self._cache_hits += 1
            return self._cache[content]

        tokens = await estimate_tokens(content)

        # Cache result
        if use_cache:
            self._cache[content] = tokens

        return tokens

    async def count_messages(self, messages: list) -> int:
        """Count tokens for messages."""
        usage = await estimate_messages_tokens(messages)
        return usage.input_tokens

    def clear_cache(self) -> None:
        """Clear token cache."""
        self._cache.clear()
        self._cache_hits = 0

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
        }


class TokenBudgetManager:
    """Manage token budgets."""

    def __init__(self, budget: TokenBudget = None):
        self.budget = budget or TokenBudget()
        self._current_usage = TokenUsage()

    def can_add_input(self, tokens: int) -> bool:
        """Check if input tokens can be added."""
        projected = self._current_usage.input_tokens + tokens + self.budget.reserve_tokens
        return projected <= self.budget.max_input_tokens

    def can_add_output(self, tokens: int) -> bool:
        """Check if output tokens can be added."""
        projected = self._current_usage.output_tokens + tokens
        return projected <= self.budget.max_output_tokens

    def add_usage(self, usage: TokenUsage) -> None:
        """Add token usage."""
        self._current_usage.input_tokens += usage.input_tokens
        self._current_usage.output_tokens += usage.output_tokens
        self._current_usage.cache_read_tokens += usage.cache_read_tokens
        self._current_usage.cache_creation_tokens += usage.cache_creation_tokens

    def get_remaining_input(self) -> int:
        """Get remaining input tokens."""
        return self.budget.max_input_tokens - self._current_usage.input_tokens - self.budget.reserve_tokens

    def get_remaining_output(self) -> int:
        """Get remaining output tokens."""
        return self.budget.max_output_tokens - self._current_usage.output_tokens

    def get_usage_percent(self) -> float:
        """Get usage percentage."""
        total_used = self._current_usage.total()
        return total_used / self.budget.max_total_tokens * 100

    def reset(self) -> None:
        """Reset usage."""
        self._current_usage = TokenUsage()


__all__ = [
    "TokenUsage",
    "TokenBudget",
    "estimate_tokens",
    "estimate_message_tokens",
    "estimate_messages_tokens",
    "TokenCounter",
    "TokenBudgetManager",
    "detect_content_type",
]