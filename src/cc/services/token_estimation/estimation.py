"""Token Estimation - Estimate token counts for messages."""

from __future__ import annotations
import re
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ContentType(Enum):
    """Content types."""
    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"
    JSON = "json"
    IMAGE = "image"
    UNKNOWN = "unknown"


@dataclass
class TokenUsage:
    """Token usage info."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0


@dataclass
class TokenBudget:
    """Token budget configuration."""
    max_input: int = 200000
    max_output: int = 8192
    reserve_for_output: int = 1000
    warning_threshold: float = 0.8
    critical_threshold: float = 0.95


# Approximate token ratios
TOKEN_RATIOS = {
    "english": 4,
    "code": 3,
    "markdown": 4,
    "json": 3,
    "chinese": 2,
}


def estimate_tokens(text: str, content_type: ContentType = ContentType.TEXT) -> int:
    """Estimate token count."""
    if not text:
        return 0
    
    has_cjk = bool(re.search(r'[\u4e00-\u9fff]', text))
    
    if has_cjk:
        ratio = TOKEN_RATIOS["chinese"]
    elif content_type == ContentType.CODE:
        ratio = TOKEN_RATIOS["code"]
    elif content_type == ContentType.JSON:
        ratio = TOKEN_RATIOS["json"]
    else:
        ratio = TOKEN_RATIOS["english"]
    
    return int(len(text) / ratio)


def estimate_message_tokens(message: Dict[str, Any]) -> TokenUsage:
    """Estimate tokens for a message."""
    input_tokens = 1  # Role token
    
    content = message.get("content", "")
    if isinstance(content, str):
        input_tokens += estimate_tokens(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type", "text")
                if block_type == "text":
                    input_tokens += estimate_tokens(block.get("text", ""))
                elif block_type == "image":
                    input_tokens += 1000
    
    return TokenUsage(input_tokens=input_tokens)


def estimate_messages_tokens(messages: List[Dict[str, Any]]) -> TokenUsage:
    """Estimate tokens for multiple messages."""
    total = sum(estimate_message_tokens(msg).input_tokens for msg in messages)
    return TokenUsage(input_tokens=total)


def detect_content_type(text: str) -> ContentType:
    """Detect content type."""
    if not text:
        return ContentType.UNKNOWN
    
    if re.search(r'^\s*(def|class|function|import)', text):
        return ContentType.CODE
    
    if re.search(r'^#+\s+', text) or re.search(r'\[.*\]\(.*\)', text):
        return ContentType.MARKDOWN
    
    return ContentType.TEXT


class TokenCounter:
    """Token counting utility."""
    
    def __init__(self, budget: TokenBudget = None):
        self.budget = budget or TokenBudget()
        self._count = 0
    
    def add_text(self, text: str) -> int:
        tokens = estimate_tokens(text)
        self._count += tokens
        return tokens
    
    def get_count(self) -> int:
        return self._count
    
    def reset(self) -> None:
        self._count = 0


class TokenBudgetManager:
    """Manage token budgets."""
    
    def __init__(self, budget: TokenBudget = None):
        self.budget = budget or TokenBudget()
        self._counters: Dict[str, TokenCounter] = {}
    
    def get_counter(self, id: str) -> TokenCounter:
        if id not in self._counters:
            self._counters[id] = TokenCounter(self.budget)
        return self._counters[id]
