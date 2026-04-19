"""Compact Service - Context compression for managing conversation length."""

from __future__ import annotations
import asyncio
import time
from pathlib import Path
from typing import Any, Callable, ClassVar, Optional
from dataclasses import dataclass, field
from enum import Enum


class CompactStrategy(Enum):
    """Compact strategy types."""
    SUMMARY = "summary"
    MICRO = "micro"
    TIME_BASED = "time_based"
    GROUPED = "grouped"


@dataclass
class CompactConfig:
    """Configuration for compacting."""
    max_tokens: int = 8000
    strategy: CompactStrategy = CompactStrategy.SUMMARY
    keep_system: bool = True
    keep_recent: int = 5
    min_messages_to_compact: int = 20
    auto_compact: bool = False
    auto_compact_threshold: int = 100000


@dataclass
class CompactResult:
    """Result of compacting."""
    original_messages: int
    compacted_messages: int
    original_tokens: int
    compacted_tokens: int
    saved_tokens: int
    strategy_used: CompactStrategy
    summary: Optional[str] = None
    compacted_at: float = field(default_factory=time.time)


class MessageGroup:
    """Group of related messages."""

    def __init__(self, messages: List[dict], topic: str = ""):
        self.messages = messages
        self.topic = topic
        self.start_index = 0
        self.end_index = len(messages) - 1

    def get_token_count(self) -> int:
        """Estimate token count."""
        total = 0
        for msg in self.messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        total += len(block["text"]) // 4
        return total

    def create_summary(self) -> str:
        """Create summary of group."""
        parts = []
        for msg in self.messages:
            role = msg.get("role", "unknown")
            content_preview = self._get_content_preview(msg)
            parts.append(f"[{role}] {content_preview}")

        return f"Group ({self.topic}): " + " | ".join(parts[:3])

    def _get_content_preview(self, msg: dict) -> str:
        """Get content preview."""
        content = msg.get("content", "")
        if isinstance(content, str):
            return content[:100]
        elif isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"][:50])
            return " ".join(texts)[:100]
        return str(content)[:100]


class CompactService:
    """Service for compacting conversation context."""

    def __init__(self, config: Optional[CompactConfig] = None):
        self.config = config or CompactConfig()
        self._compaction_history: List[CompactResult] = []
        self._on_compact: Optional[Callable] = None

    def estimate_tokens(self, messages: List[dict]) -> int:
        """Estimate total token count."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        total += len(block["text"]) // 4
                    elif isinstance(block, dict) and "tool_use" in block:
                        total += 50  # Tool overhead
                    elif isinstance(block, dict) and "tool_result" in block:
                        result_content = block.get("content", "")
                        total += len(str(result_content)) // 4
        return total

    def should_compact(self, messages: List[dict]) -> bool:
        """Check if compacting is needed."""
        if len(messages) < self.config.min_messages_to_compact:
            return False

        token_count = self.estimate_tokens(messages)
        return token_count > self.config.max_tokens

    def compact(self, messages: List[dict]) -> tuple[List[dict], CompactResult]:
        """Compact messages."""
        original_tokens = self.estimate_tokens(messages)
        original_count = len(messages)

        # Apply strategy
        if self.config.strategy == CompactStrategy.SUMMARY:
            compacted = self._compact_summary(messages)
        elif self.config.strategy == CompactStrategy.MICRO:
            compacted = self._compact_micro(messages)
        elif self.config.strategy == CompactStrategy.GROUPED:
            compacted = self._compact_grouped(messages)
        else:
            compacted = self._compact_time_based(messages)

        compacted_tokens = self.estimate_tokens(compacted)

        result = CompactResult(
            original_messages=original_count,
            compacted_messages=len(compacted),
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            saved_tokens=original_tokens - compacted_tokens,
            strategy_used=self.config.strategy,
        )

        self._compaction_history.append(result)

        if self._on_compact:
            self._on_compact(result)

        return compacted, result

    def _compact_summary(self, messages: List[dict]) -> List[dict]:
        """Compact using summary strategy."""
        # Keep system messages
        system_messages = [
            m for m in messages if m.get("role") == "system"
        ]

        # Keep recent messages
        recent = messages[-self.config.keep_recent:]

        # Summarize older messages
        older = messages[:-self.config.keep_recent]
        older = [m for m in older if m.get("role") != "system"]

        if older:
            summary = self._create_summary(older)
            summary_message = {
                "role": "system",
                "content": f"[Previous conversation summary]\n{summary}",
            }
            return system_messages + [summary_message] + recent

        return system_messages + recent

    def _compact_micro(self, messages: List[dict]) -> List[dict]:
        """Micro-compact: Keep only essential parts."""
        compacted = []

        for msg in messages:
            role = msg.get("role")

            # Keep system messages fully
            if role == "system":
                compacted.append(msg)
                continue

            # Keep user messages
            if role == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > 200:
                    # Truncate long messages
                    msg = {**msg, "content": content[:200] + "... [truncated]"}
                compacted.append(msg)
                continue

            # Summarize assistant/tool messages
            if role == "assistant":
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Keep only text content, truncate
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            texts.append({"text": block["text"][:100]})
                    if texts:
                        msg = {**msg, "content": texts}
                        compacted.append(msg)

        return compacted

    def _compact_grouped(self, messages: List[dict]) -> List[dict]:
        """Compact by grouping related messages."""
        groups = self._group_messages(messages)
        compacted = []

        # Keep system messages
        system = [m for m in messages if m.get("role") == "system"]
        compacted.extend(system)

        # Create summaries for each group
        for group in groups[:-self.config.keep_recent]:
            summary = group.create_summary()
            compacted.append({
                "role": "system",
                "content": summary,
            })

        # Keep recent groups fully
        for group in groups[-self.config.keep_recent:]:
            compacted.extend(group.messages)

        return compacted

    def _compact_time_based(self, messages: List[dict]) -> List[dict]:
        """Compact based on time windows."""
        # Keep messages from last N minutes
        now = time.time()
        window_seconds = 3600  # 1 hour

        compacted = []

        for msg in messages:
            # System messages always kept
            if msg.get("role") == "system":
                compacted.append(msg)
                continue

            # Check timestamp
            timestamp = msg.get("timestamp", now)
            if now - timestamp < window_seconds:
                compacted.append(msg)

        return compacted

    def _group_messages(self, messages: List[dict]) -> List[MessageGroup]:
        """Group related messages."""
        groups = []
        current_group = []
        current_topic = ""

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            # Detect topic change
            if role == "user":
                topic = self._extract_topic(content)
                if topic != current_topic and current_group:
                    groups.append(MessageGroup(current_group, current_topic))
                    current_group = []
                current_topic = topic

            current_group.append(msg)

        if current_group:
            groups.append(MessageGroup(current_group, current_topic))

        return groups

    def _extract_topic(self, content: str | list) -> str:
        """Extract topic from content."""
        if isinstance(content, str):
            # Look for key terms
            words = content.lower().split()
            topics = ["code", "file", "error", "test", "git", "commit", "review"]
            for word in words[:10]:
                if word in topics:
                    return word
            return "general"

        return "mixed"

    def _create_summary(self, messages: List[dict]) -> str:
        """Create summary of messages."""
        parts = []
        for msg in messages:
            role = msg.get("role", "")
            content_preview = self._get_content_preview(msg)
            parts.append(f"[{role}] {content_preview}")

        return "\n".join(parts)

    def _get_content_preview(self, msg: dict) -> str:
        """Get content preview."""
        content = msg.get("content", "")
        if isinstance(content, str):
            return content[:100] + "..." if len(content) > 100 else content
        elif isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"][:50])
            return " ".join(texts)[:100]
        return str(content)[:100]

    def get_compaction_history(self) -> List[CompactResult]:
        """Get history of compactions."""
        return self._compaction_history

    def set_callback(self, callback: Callable) -> None:
        """Set compact callback."""
        self._on_compact = callback

    def get_stats(self) -> dict:
        """Get compact statistics."""
        if not self._compaction_history:
            return {
                "total_compactions": 0,
                "total_saved_tokens": 0,
            }

        return {
            "total_compactions": len(self._compaction_history),
            "total_saved_tokens": sum(r.saved_tokens for r in self._compaction_history),
            "avg_saved": sum(r.saved_tokens for r in self._compaction_history) / len(self._compaction_history),
        }


class AutoCompactHook:
    """Hook for automatic compacting."""

    def __init__(self, service: CompactService):
        self.service = service
        self._enabled = False

    def enable(self) -> None:
        """Enable auto compacting."""
        self._enabled = True

    def disable(self) -> None:
        """Disable auto compacting."""
        self._enabled = False

    async def check_and_compact(self, messages: List[dict]) -> tuple[List[dict], CompactResult | None]:
        """Check and compact if needed."""
        if not self._enabled:
            return messages, None

        if self.service.should_compact(messages):
            return self.service.compact(messages)

        return messages, None


# Global service
_compact_service: Optional[CompactService] = None


def get_compact_service() -> CompactService:
    """Get global compact service."""
    global _compact_service
    if _compact_service is None:
        _compact_service = CompactService()
    return _compact_service


__all__ = [
    "CompactStrategy",
    "CompactConfig",
    "CompactResult",
    "MessageGroup",
    "CompactService",
    "AutoCompactHook",
    "get_compact_service",
]
