"""Compact Services - Context compression modes."""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class CompactMode(Enum):
    """Compaction modes."""
    SUMMARY = "summary"
    MICRO = "micro"
    GROUPED = "grouped"
    TIME_BASED = "time_based"


@dataclass
class CompactConfig:
    """Compact configuration."""
    mode: CompactMode = CompactMode.SUMMARY
    max_tokens: int = 5000
    preserve_recent: int = 5
    group_size: int = 10


@dataclass
class CompactResult:
    """Compact result."""
    original_tokens: int
    compacted_tokens: int
    compression_ratio: float
    messages_removed: int
    messages_preserved: int
    summary: str


class SummaryCompactor:
    """SUMMARY mode compactor."""

    async def compact(
        self,
        messages: List[Dict[str, Any]],
        config: CompactConfig,
    ) -> CompactResult:
        """Compact messages into summary."""
        original_tokens = sum(len(str(m)) // 4 for m in messages)

        # Preserve recent messages
        recent = messages[-config.preserve_recent:]
        older = messages[:-config.preserve_recent]

        # Generate summary for older messages
        summary = await self._generate_summary(older)

        compacted_tokens = len(summary) // 4 + sum(len(str(m)) // 4 for m in recent)

        return CompactResult(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            compression_ratio=compacted_tokens / original_tokens if original_tokens > 0 else 0,
            messages_removed=len(older),
            messages_preserved=len(recent),
            summary=summary,
        )

    async def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Generate summary from messages."""
        if not messages:
            return ""

        # Extract key information
        decisions = []
        actions = []

        for msg in messages:
            content = str(msg.get("content", ""))
            role = msg.get("role", "")

            if role == "assistant":
                # Find decisions
                decision_matches = re.findall(r"decided to (.+)|we should (.+)|let's (.+)", content.lower())
                for match in decision_matches:
                    decisions.append(match)

                # Find actions
                action_matches = re.findall(r"created|modified|deleted|ran|executed", content.lower())
                for match in action_matches:
                    actions.append(match)

        summary_parts = []

        if decisions:
            summary_parts.append(f"Key decisions: {', '.join(decisions[:5])}")

        if actions:
            summary_parts.append(f"Actions taken: {', '.join(actions[:5])}")

        summary_parts.append(f"Messages summarized: {len(messages)}")

        return "\n".join(summary_parts)


class MicroCompactor:
    """MICRO mode compactor."""

    async def compact(
        self,
        messages: List[Dict[str, Any]],
        config: CompactConfig,
    ) -> CompactResult:
        """Compact each message into micro form."""
        original_tokens = sum(len(str(m)) // 4 for m in messages)

        compacted = []

        for msg in messages:
            micro = self._compact_message(msg)
            compacted.append(micro)

        compacted_tokens = sum(len(str(m)) // 4 for m in compacted)

        return CompactResult(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            compression_ratio=compacted_tokens / original_tokens if original_tokens > 0 else 0,
            messages_removed=0,
            messages_preserved=len(messages),
            summary="",
        )

    def _compact_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Compact single message."""
        content = str(message.get("content", ""))

        # Truncate to first sentence or 50 chars
        first_sentence = re.split(r"[.!?\n]", content)[0]
        if len(first_sentence) > 50:
            first_sentence = first_sentence[:50] + "..."

        return {
            "role": message.get("role", ""),
            "content": first_sentence,
            "type": "micro",
        }


class GroupedCompactor:
    """GROUPED mode compactor."""

    async def compact(
        self,
        messages: List[Dict[str, Any]],
        config: CompactConfig,
    ) -> CompactResult:
        """Compact messages into groups."""
        original_tokens = sum(len(str(m)) // 4 for m in messages)

        # Group messages
        groups = []
        for i in range(0, len(messages), config.group_size):
            group = messages[i:i + config.group_size]
            groups.append(group)

        # Compact each group
        compacted = []
        for group in groups:
            group_summary = await self._summarize_group(group)
            compacted.append(group_summary)

        compacted_tokens = sum(len(str(m)) // 4 for m in compacted)

        return CompactResult(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            compression_ratio=compacted_tokens / original_tokens if original_tokens > 0 else 0,
            messages_removed=len(messages) - len(compacted),
            messages_preserved=len(compacted),
            summary="",
        )

    async def _summarize_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize message group."""
        content_parts = []

        for msg in group:
            role = msg.get("role", "")
            content = str(msg.get("content", ""))

            if role == "user":
                # Extract first 30 chars
                content_parts.append(f"User: {content[:30]}...")
            elif role == "assistant":
                # Extract key action
                content_parts.append(f"Assistant: {content[:30]}...")

        return {
            "role": "summary",
            "content": "\n".join(content_parts),
            "messages_count": len(group),
            "type": "group",
        }


class TimeBasedCompactor:
    """TIME_BASED mode compactor."""

    async def compact(
        self,
        messages: List[Dict[str, Any]],
        config: CompactConfig,
    ) -> CompactResult:
        """Compact based on time thresholds."""
        original_tokens = sum(len(str(m)) // 4 for m in messages)

        # Time thresholds
        thresholds = {
            "recent": 5 * 60,      # 5 minutes - full
            "medium": 30 * 60,     # 30 minutes - summary
            "old": 2 * 60 * 60,    # 2 hours - micro
        }

        import time
        now = time.time()

        compacted = []

        for msg in messages:
            timestamp = msg.get("timestamp", now)

            age = now - timestamp if isinstance(timestamp, (int, float)) else 0

            if age < thresholds["recent"]:
                # Keep full
                compacted.append(msg)
            elif age < thresholds["medium"]:
                # Summarize
                compacted.append(self._to_summary(msg))
            else:
                # Micro
                compacted.append(self._to_micro(msg))

        compacted_tokens = sum(len(str(m)) // 4 for m in compacted)

        return CompactResult(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            compression_ratio=compacted_tokens / original_tokens if original_tokens > 0 else 0,
            messages_removed=len(messages) - len(compacted),
            messages_preserved=len(compacted),
            summary="",
        )

    def _to_summary(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Convert to summary form."""
        content = str(message.get("content", ""))
        return {
            "role": message.get("role", ""),
            "content": content[:100] + "..." if len(content) > 100 else content,
            "type": "summary",
        }

    def _to_micro(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Convert to micro form."""
        content = str(message.get("content", ""))
        return {
            "role": message.get("role", ""),
            "content": content[:30] + "...",
            "type": "micro",
        }


class CompactService:
    """Main compact service."""

    def __init__(self):
        self._compactors = {
            CompactMode.SUMMARY: SummaryCompactor(),
            CompactMode.MICRO: MicroCompactor(),
            CompactMode.GROUPED: GroupedCompactor(),
            CompactMode.TIME_BASED: TimeBasedCompactor(),
        }

    async def compact(
        self,
        messages: List[Dict[str, Any]],
        config: CompactConfig = None,
    ) -> CompactResult:
        """Compact messages."""
        config = config or CompactConfig()
        compactor = self._compactors.get(config.mode)

        if compactor is None:
            compactor = self._compactors[CompactMode.SUMMARY]

        return await compactor.compact(messages, config)


# Global service
_service: Optional[CompactService] = None


def get_compact_service() -> CompactService:
    """Get global compact service."""
    global _service
    if _service is None:
        _service = CompactService()
    return _service


__all__ = [
    "CompactMode",
    "CompactConfig",
    "CompactResult",
    "SummaryCompactor",
    "MicroCompactor",
    "GroupedCompactor",
    "TimeBasedCompactor",
    "CompactService",
    "get_compact_service",
]