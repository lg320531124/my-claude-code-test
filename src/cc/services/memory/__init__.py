"""Memory Extraction Service - Extract memories from conversations."""

from __future__ import annotations
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class ExtractedMemory:
    """Extracted memory."""
    type: str  # decision, learning, pattern, preference
    content: str
    context: str
    confidence: float
    source_message_id: str
    timestamp: datetime = field(default_factory=datetime.now)


class MemoryExtractionService:
    """Extract memories from conversations."""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path.home() / ".claude" / "extracted_memories.json"
        self._memories: List[ExtractedMemory] = []

    async def extract_from_messages(self, messages: List[Dict[str, Any]]) -> List[ExtractedMemory]:
        """Extract memories from messages."""
        extracted = []

        for msg in messages:
            content = str(msg.get("content", ""))
            role = msg.get("role", "")

            # Look for decision patterns
            decision_patterns = [
                r"let's (use|go with|choose) (.+)",
                r"I decided to (.+)",
                r"we should (.+)",
                r"the best approach is (.+)",
            ]

            for pattern in decision_patterns:
                matches = re.findall(pattern, content.lower())
                for match in matches:
                    memory = ExtractedMemory(
                        type="decision",
                        content=f"Use {match}",
                        context=content[:200],
                        confidence=0.8,
                        source_message_id=msg.get("id", ""),
                    )
                    extracted.append(memory)

            # Look for learning patterns
            learning_patterns = [
                r"I learned that (.+)",
                r"note that (.+)",
                r"remember (.+)",
                r"important: (.+)",
            ]

            for pattern in learning_patterns:
                matches = re.findall(pattern, content.lower())
                for match in matches:
                    memory = ExtractedMemory(
                        type="learning",
                        content=match,
                        context=content[:200],
                        confidence=0.7,
                        source_message_id=msg.get("id", ""),
                    )
                    extracted.append(memory)

            # Look for pattern observations
            pattern_matches = re.findall(r"pattern: (.+)|always (.+)|never (.+)", content.lower())
            for match in pattern_matches:
                if match:
                    memory = ExtractedMemory(
                        type="pattern",
                        content=match,
                        context=content[:200],
                        confidence=0.6,
                        source_message_id=msg.get("id", ""),
                    )
                    extracted.append(memory)

        self._memories.extend(extracted)
        await self.save()

        return extracted

    async def get_memories(self, type: str = None) -> List[ExtractedMemory]:
        """Get extracted memories."""
        if type:
            return [m for m in self._memories if m.type == type]
        return self._memories

    async def clear_memories(self) -> None:
        """Clear memories."""
        self._memories.clear()
        await self.save()

    async def save(self) -> None:
        """Save memories."""
        import aiofiles

        data = {
            "memories": [
                {
                    "type": m.type,
                    "content": m.content,
                    "context": m.context,
                    "confidence": m.confidence,
                    "source": m.source_message_id,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in self._memories
            ],
        }

        async with aiofiles.open(self.storage_path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def load(self) -> None:
        """Load memories."""
        if not self.storage_path.exists():
            return

        import aiofiles
        async with aiofiles.open(self.storage_path, "r") as f:
            content = await f.read()

        data = json.loads(content)
        self._memories = [
            ExtractedMemory(
                type=m["type"],
                content=m["content"],
                context=m["context"],
                confidence=m["confidence"],
                source_message_id=m["source"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
            )
            for m in data.get("memories", [])
        ]


# Global service
_extraction: Optional[MemoryExtractionService] = None


def get_memory_extraction() -> MemoryExtractionService:
    """Get extraction service."""
    if _extraction is None:
        _extraction = MemoryExtractionService()
    return _extraction


__all__ = [
    "ExtractedMemory",
    "MemoryExtractionService",
    "get_memory_extraction",
]