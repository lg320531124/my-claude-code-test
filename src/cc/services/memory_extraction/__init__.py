"""Memory Extraction - Extract memories from conversations."""

from __future__ import annotations
import asyncio
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

from ...utils.log import get_logger

logger = get_logger(__name__)


class MemoryType(Enum):
    """Memory types."""
    DECISION = "decision"
    INSIGHT = "insight"
    LEARNING = "learning"
    PREFERENCE = "preference"
    CONTEXT = "context"
    RELATIONSHIP = "relationship"
    FEEDBACK = "feedback"


class MemoryPriority(Enum):
    """Memory priority."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ExtractedMemory:
    """Extracted memory."""
    type: MemoryType
    content: str
    priority: MemoryPriority
    context: str
    timestamp: datetime
    confidence: float = 0.8
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionConfig:
    """Extraction configuration."""
    max_memories: int = 50
    min_confidence: float = 0.5
    include_timestamps: bool = True
    deduplicate: bool = True


class MemoryExtractor:
    """Extract memories from conversations."""

    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        self._patterns: Dict[MemoryType, List[str]] = {
            MemoryType.DECISION: [
                r"decided to",
                r"we will use",
                r"the approach is",
                r"going with",
            ],
            MemoryType.INSIGHT: [
                r"found that",
                r"discovered",
                r"realized",
                r"important to note",
            ],
            MemoryType.LEARNING: [
                r"learned",
                r"understood",
                r"grasped",
                r"figured out",
            ],
            MemoryType.PREFERENCE: [
                r"prefer",
                r"like to",
                r"would rather",
                r"favor",
            ],
            MemoryType.FEEDBACK: [
                r"don't",
                r"should",
                r"needs to",
                r"fix",
            ],
        }

    async def extract(
        self,
        conversation: str,
        context: Optional[str] = None
    ) -> List[ExtractedMemory]:
        """Extract memories from conversation."""
        memories = []

        # Extract by patterns
        for type, patterns in self._patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, conversation, re.IGNORECASE)

                for match in matches:
                    # Get surrounding context
                    start = max(0, match.start() - 50)
                    end = min(len(conversation), match.end() + 100)

                    content = conversation[start:end].strip()

                    memory = ExtractedMemory(
                        type=type,
                        content=content,
                        priority=self._determine_priority(type),
                        context=context or "",
                        timestamp=datetime.now(),
                        confidence=self._calculate_confidence(match, conversation),
                    )

                    memories.append(memory)

        # Deduplicate
        if self.config.deduplicate:
            memories = self._deduplicate(memories)

        # Filter by confidence
        memories = [
            m for m in memories
            if m.confidence >= self.config.min_confidence
        ]

        # Limit
        memories = memories[:self.config.max_memories]

        return memories

    def _determine_priority(self, type: MemoryType) -> MemoryPriority:
        """Determine memory priority."""
        high_priority = [MemoryType.DECISION, MemoryType.FEEDBACK]

        if type in high_priority:
            return MemoryPriority.HIGH

        return MemoryPriority.MEDIUM

    def _calculate_confidence(
        self,
        match: re.Match,
        conversation: str
    ) -> float:
        """Calculate confidence score."""
        # Base confidence
        confidence = 0.7

        # Adjust based on context length
        context_length = len(match.group(0))
        confidence += min(context_length / 100, 0.2)

        # Adjust based on position (earlier = higher)
        position_weight = match.start() / len(conversation)
        confidence -= position_weight * 0.1

        return min(max(confidence, 0.5), 1.0)

    def _deduplicate(
        self,
        memories: List[ExtractedMemory]
    ) -> List[ExtractedMemory]:
        """Remove duplicate memories."""
        seen_content = set()
        unique = []

        for memory in memories:
            # Normalize content for comparison
            normalized = memory.content.lower().strip()

            if normalized not in seen_content:
                seen_content.add(normalized)
                unique.append(memory)

        return unique

    async def extract_from_file(
        self,
        path: Path
    ) -> List[ExtractedMemory]:
        """Extract from conversation file."""
        if not path.exists():
            return []

        content = path.read_text()
        return await self.extract(content, context=str(path))

    async def categorize(
        self,
        memories: List[ExtractedMemory]
    ) -> Dict[MemoryType, List[ExtractedMemory]]:
        """Categorize memories."""
        categorized: Dict[MemoryType, List[ExtractedMemory]] = {}

        for memory in memories:
            if memory.type not in categorized:
                categorized[memory.type] = []

            categorized[memory.type].append(memory)

        return categorized

    async def summarize(
        self,
        memories: List[ExtractedMemory]
    ) -> str:
        """Summarize extracted memories."""
        if not memories:
            return "No memories extracted."

        # Group by type
        categorized = await self.categorize(memories)

        lines = []

        for type, type_memories in categorized.items():
            lines.append(f"\n{type.value.upper()} ({len(type_memories)}):")

            for memory in type_memories[:5]:
                lines.append(f"  - {memory.content[:100]}")

        return "\n".join(lines)

    async def export(
        self,
        memories: List[ExtractedMemory],
        format: str = "json"
    ) -> str:
        """Export memories."""
        if format == "json":
            import json

            data = [
                {
                    "type": m.type.value,
                    "content": m.content,
                    "priority": m.priority.value,
                    "confidence": m.confidence,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in memories
            ]

            return json.dumps(data, indent=2)

        # Simple text format
        lines = []

        for m in memories:
            lines.append(f"[{m.type.value}] {m.content}")

        return "\n".join(lines)


__all__ = [
    "MemoryType",
    "MemoryPriority",
    "ExtractedMemory",
    "ExtractionConfig",
    "MemoryExtractor",
]