"""Memory Extraction Service - Extract memories from conversations."""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class MemoryType(Enum):
    """Memory types."""
    DECISION = "decision"
    PREFERENCE = "preference"
    FACT = "fact"
    INSTRUCTION = "instruction"
    ERROR_PATTERN = "error_pattern"
    SUCCESS_PATTERN = "success_pattern"
    WORKFLOW = "workflow"
    CONTEXT = "context"


class ExtractionMethod(Enum):
    """Extraction methods."""
    EXPLICIT = "explicit"
    IMPLIED = "implied"
    PATTERN = "pattern"
    TEMPORAL = "temporal"


@dataclass
class ExtractedMemory:
    """Extracted memory."""
    type: MemoryType
    content: str
    method: ExtractionMethod
    confidence: float
    source: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class ExtractionConfig:
    """Extraction configuration."""
    min_confidence: float = 0.5
    max_memories: int = 100
    include_context: bool = True
    deduplicate: bool = True
    temporal_window: float = 3600.0


@dataclass
class ExtractionResult:
    """Extraction result."""
    memories: List[ExtractedMemory]
    total_extracted: int
    filtered: int
    duplicates: int
    processing_time: float


class MemoryExtractor:
    """Extract memories from conversations."""

    # Patterns for explicit memories
    EXPLICIT_PATTERNS = [
        (r"remember (?:that|to) (.+)", MemoryType.INSTRUCTION),
        (r"always (.+) when (.+)", MemoryType.WORKFLOW),
        (r"never (.+)", MemoryType.INSTRUCTION),
        (r"I prefer (.+)", MemoryType.PREFERENCE),
        (r"my preference is (.+)", MemoryType.PREFERENCE),
        (r"we decided (.+)", MemoryType.DECISION),
        (r"the decision was (.+)", MemoryType.DECISION),
        (r"important: (.+)", MemoryType.FACT),
        (r"note: (.+)", MemoryType.FACT),
    ]

    # Patterns for implied memories
    IMPLIED_PATTERNS = [
        (r"this always works: (.+)", MemoryType.SUCCESS_PATTERN),
        (r"this fails when (.+)", MemoryType.ERROR_PATTERN),
        (r"usually (.+)", MemoryType.FACT),
        (r"typically (.+)", MemoryType.FACT),
    ]

    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        self._extracted: List[ExtractedMemory] = []
        self._seen_content: set = set()

    async def extract(
        self,
        content: str,
        source: str = "conversation"
    ) -> ExtractionResult:
        """Extract memories from content."""
        start_time = datetime.now()

        memories: List[ExtractedMemory] = []

        # Extract explicit memories
        explicit = await self._extract_explicit(content, source)
        memories.extend(explicit)

        # Extract implied memories
        implied = await self._extract_implied(content, source)
        memories.extend(implied)

        # Extract patterns
        patterns = await self._extract_patterns(content, source)
        memories.extend(patterns)

        # Filter by confidence
        filtered = 0
        memories = [m for m in memories if m.confidence >= self.config.min_confidence]
        filtered = len(memories) - len(memories)

        # Deduplicate
        duplicates = 0
        if self.config.deduplicate:
            unique_memories = []
            for m in memories:
                key = m.content.lower()
                if key not in self._seen_content:
                    self._seen_content.add(key)
                    unique_memories.append(m)
                else:
                    duplicates += 1
            memories = unique_memories

        # Limit count
        memories = memories[:self.config.max_memories]

        # Store extracted
        self._extracted.extend(memories)

        processing_time = (datetime.now() - start_time).total_seconds()

        return ExtractionResult(
            memories=memories,
            total_extracted=len(memories),
            filtered=filtered,
            duplicates=duplicates,
            processing_time=processing_time,
        )

    async def _extract_explicit(
        self,
        content: str,
        source: str
    ) -> List[ExtractedMemory]:
        """Extract explicit memories using patterns."""
        memories = []

        for pattern, memory_type in self.EXPLICIT_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)

            for match in matches:
                memory = ExtractedMemory(
                    type=memory_type,
                    content=match if isinstance(match, str) else " ".join(match),
                    method=ExtractionMethod.EXPLICIT,
                    confidence=0.9,
                    source=source,
                    timestamp=datetime.now(),
                )
                memories.append(memory)

        return memories

    async def _extract_implied(
        self,
        content: str,
        source: str
    ) -> List[ExtractedMemory]:
        """Extract implied memories using patterns."""
        memories = []

        for pattern, memory_type in self.IMPLIED_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)

            for match in matches:
                memory = ExtractedMemory(
                    type=memory_type,
                    content=match if isinstance(match, str) else " ".join(match),
                    method=ExtractionMethod.IMPLIED,
                    confidence=0.7,
                    source=source,
                    timestamp=datetime.now(),
                )
                memories.append(memory)

        return memories

    async def _extract_patterns(
        self,
        content: str,
        source: str
    ) -> List[ExtractedMemory]:
        """Extract patterns from content."""
        memories = []

        # Look for repeated patterns
        # This is a simplified implementation
        lines = content.split("\n")

        # Check for repeated instructions
        instruction_lines = [
            l for l in lines
            if l.strip().startswith(("Run", "Execute", "Check", "Verify"))
        ]

        if len(instruction_lines) >= 3:
            # Found potential workflow
            memory = ExtractedMemory(
                type=MemoryType.WORKFLOW,
                content=f"Common workflow: {instruction_lines[0]}",
                method=ExtractionMethod.PATTERN,
                confidence=0.6,
                source=source,
                timestamp=datetime.now(),
            )
            memories.append(memory)

        return memories

    async def extract_from_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> ExtractionResult:
        """Extract memories from message list."""
        all_memories: List[ExtractedMemory] = []

        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "unknown")
            source = f"message_{role}"

            result = await self.extract(content, source)
            all_memories.extend(result.memories)

        return ExtractionResult(
            memories=all_memories[:self.config.max_memories],
            total_extracted=len(all_memories),
            filtered=0,
            duplicates=0,
            processing_time=0.0,
        )

    async def get_memories(
        self,
        memory_type: Optional[MemoryType] = None
    ) -> List[ExtractedMemory]:
        """Get extracted memories."""
        if memory_type:
            return [m for m in self._extracted if m.type == memory_type]
        return self._extracted

    async def clear(self) -> int:
        """Clear extracted memories."""
        count = len(self._extracted)
        self._extracted.clear()
        self._seen_content.clear()
        return count

    async def export_memories(self) -> List[Dict[str, Any]]:
        """Export memories as dict."""
        return [
            {
                "type": m.type.value,
                "content": m.content,
                "confidence": m.confidence,
                "source": m.source,
                "timestamp": m.timestamp.isoformat(),
                "tags": m.tags,
            }
            for m in self._extracted
        ]


__all__ = [
    "MemoryType",
    "ExtractionMethod",
    "ExtractedMemory",
    "ExtractionConfig",
    "ExtractionResult",
    "MemoryExtractor",
]