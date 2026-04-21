"""Token Estimation - Async token counting."""

from __future__ import annotations
import asyncio
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class TokenEstimate:
    """Token estimation result."""
    text_tokens: int
    image_tokens: int = 0
    tool_tokens: int = 0
    system_tokens: int = 0
    total: int = 0
    confidence: float = 0.8


# Approximate token ratios (based on empirical data)
TOKEN_RATIOS = {
    "english": 4,       # ~4 chars per token
    "code": 3.5,        # ~3.5 chars per token for code
    "chinese": 1.5,     # ~1.5 chars per token for Chinese
    "japanese": 2,      # ~2 chars per token
    "mixed": 3,         # Average for mixed content
}


async def estimate_tokens(text: str, content_type: str = "mixed") -> int:
    """Estimate tokens for text."""
    if not text:
        return 0

    # Run estimation in thread to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _estimate_sync, text, content_type)


def _estimate_sync(text: str, content_type: str) -> int:
    """Synchronous token estimation."""
    # Count characters
    char_count = len(text)

    # Detect language/content type if not specified
    if content_type == "mixed":
        content_type = _detect_content_type(text)

    # Get ratio
    ratio = TOKEN_RATIOS.get(content_type, 4)

    # Basic estimation
    base_estimate = char_count / ratio

    # Adjust for whitespace and structure
    # Whitespace often creates separate tokens
    whitespace_count = len(re.findall(r"\s+", text))
    base_estimate += whitespace_count * 0.5

    # Adjust for punctuation
    punctuation_count = len(re.findall(r"[^\w\s]", text))
    base_estimate += punctuation_count * 0.3

    # Adjust for special tokens (like in code)
    special_token_patterns = [
        r"\b(if|else|for|while|def|class|import|return)\b",
        r"[\{\}\[\]\(\)]",
        r"[\.\,\;\:]",
    ]

    for pattern in special_token_patterns:
        matches = len(re.findall(pattern, text))
        base_estimate += matches * 0.2

    return int(base_estimate) + 1


def _detect_content_type(text: str) -> str:
    """Detect content type from text."""
    # Check for Chinese/Japanese characters
    cjk_count = len(re.findall(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]", text))

    if cjk_count > len(text) * 0.3:
        # Check if it's primarily Chinese or Japanese
        chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
        japanese_count = len(re.findall(r"[\u3040-\u30ff]", text))

        if chinese_count > japanese_count:
            return "chinese"
        else:
            return "japanese"

    # Check for code patterns
    code_patterns = [
        r"\bdef\s+\w+",           # Python function
        r"\bfunction\s+\w+",      # JS function
        r"\bclass\s+\w+",         # Class definition
        r"\bimport\s+\w+",        # Import statement
        r"[\{\}\[\]\(\)]",        # Brackets
        r"[\=\>\<\!]",            # Operators
    ]

    code_matches = sum(len(re.findall(p, text)) for p in code_patterns)

    if code_matches > len(text) * 0.05:
        return "code"

    return "english"


async def estimate_messages_tokens(messages: List[Dict[str, Any]]) -> TokenEstimate:
    """Estimate tokens for messages."""
    text_tokens = 0
    image_tokens = 0
    tool_tokens = 0
    system_tokens = 0

    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")

        # Role overhead (~4 tokens)
        role_tokens = 4

        if isinstance(content, str):
            content_tokens = await estimate_tokens(content)

            if role == "system":
                system_tokens += content_tokens + role_tokens
            else:
                text_tokens += content_tokens + role_tokens

        elif isinstance(content, list):
            for block in content:
                block_type = block.get("type", "text")

                if block_type == "text":
                    block_tokens = await estimate_tokens(block.get("text", ""))
                    text_tokens += block_tokens

                elif block_type == "image":
                    # Images have fixed token cost based on size
                    source = block.get("source", {})
                    if source.get("type") == "base64":
                        # Estimate based on image dimensions
                        image_tokens += 1000  # Placeholder
                    else:
                        image_tokens += 1000

                elif block_type == "tool_use":
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})
                    tool_tokens += await estimate_tokens(tool_name)
                    tool_tokens += await estimate_tokens(str(tool_input))
                    tool_tokens += 10  # Tool overhead

                elif block_type == "tool_result":
                    result_content = block.get("content", "")
                    tool_tokens += await estimate_tokens(str(result_content))
                    tool_tokens += 5  # Result overhead

    total = text_tokens + image_tokens + tool_tokens + system_tokens

    return TokenEstimate(
        text_tokens=text_tokens,
        image_tokens=image_tokens,
        tool_tokens=tool_tokens,
        system_tokens=system_tokens,
        total=total,
    )


async def estimate_context_size(
    system_prompt: str,
    messages: List[Dict[str, Any]],
    tools: List[Dict] = None,
) -> int:
    """Estimate total context size."""
    total = 0

    # System prompt
    total += await estimate_tokens(system_prompt)

    # Messages
    msg_estimate = await estimate_messages_tokens(messages)
    total += msg_estimate.total

    # Tools definition
    if tools:
        for tool in tools:
            tool_def_tokens = await estimate_tokens(tool.get("name", ""))
            tool_def_tokens += await estimate_tokens(str(tool.get("input_schema", {})))
            total += tool_def_tokens + 5

    return total


async def check_context_limit(
    context_tokens: int,
    model_max_tokens: int,
    reserve_output: int = 4096,
) -> Dict[str, Any]:
    """Check if context is within limits."""
    available_for_context = model_max_tokens - reserve_output

    is_within_limit = context_tokens <= available_for_context
    tokens_remaining = available_for_context - context_tokens

    return {
        "is_within_limit": is_within_limit,
        "context_tokens": context_tokens,
        "max_context": available_for_context,
        "tokens_remaining": tokens_remaining,
        "percentage_used": context_tokens / available_for_context if available_for_context > 0 else 1.0,
        "needs_compaction": context_tokens > available_for_context * 0.8,
    }


class TokenCounter:
    """Token counting service."""

    def __init__(self):
        self._cache: Dict[str, int] = field(default_factory=dict)
        self._total_input: int = 0
        self._total_output: int = 0

    async def count(self, text: str) -> int:
        """Count tokens with caching."""
        cache_key = f"{len(text)}:{hash(text) % 10000}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        count = await estimate_tokens(text)
        self._cache[cache_key] = count

        return count

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Record token usage."""
        self._total_input += input_tokens
        self._total_output += output_tokens

    def get_usage(self) -> Dict[str, int]:
        """Get total usage."""
        return {
            "total_input": self._total_input,
            "total_output": self._total_output,
            "total": self._total_input + self._total_output,
        }

    def clear_cache(self) -> None:
        """Clear token cache."""
        self._cache.clear()


# Global counter
_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """Get global token counter."""
    global _counter
    if _counter is None:
        _counter = TokenCounter()
    return _counter


__all__ = [
    "TokenEstimate",
    "estimate_tokens",
    "estimate_messages_tokens",
    "estimate_context_size",
    "check_context_limit",
    "TokenCounter",
    "get_token_counter",
]