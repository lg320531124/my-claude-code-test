"""Session Memory Service - Persistent memory across sessions."""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum


class MemoryType(Enum):
    """Memory type classification."""
    USER = "user"
    PROJECT = "project"
    FEEDBACK = "feedback"
    REFERENCE = "reference"
    DISCOVERY = "discovery"


@dataclass
class MemoryEntry:
    """Single memory entry."""
    content: str
    memory_type: MemoryType
    created_at: float
    importance: int = 0  # 0-10 scale
    source: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    last_used: Optional[float] = None
    use_count: int = 0


@dataclass
class MemorySearchResult:
    """Result from memory search."""
    entry: MemoryEntry
    relevance_score: float
    matched_tags: List[str] = field(default_factory=list)


class MemoryStore:
    """Storage for memories."""

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or Path.home() / ".claude" / "memory" / "store.json"
        self.memories: Dict[str, MemoryEntry] = {}
        self._by_type: Dict[MemoryType, List[str]] = {}
        self._by_tag: Dict[str, List[str]] = {}

        self._load()

    def _load(self) -> None:
        """Load memories from store."""
        if not self.store_path.exists():
            return

        try:
            data = json.loads(self.store_path.read_text())
            for id_str, entry_data in data.items():
                entry = MemoryEntry(
                    content=entry_data.get("content", ""),
                    memory_type=MemoryType(entry_data.get("memory_type", "user")),
                    created_at=entry_data.get("created_at", time.time()),
                    importance=entry_data.get("importance", 0),
                    source=entry_data.get("source", ""),
                    tags=entry_data.get("tags", []),
                    metadata=entry_data.get("metadata", {}),
                    last_used=entry_data.get("last_used"),
                    use_count=entry_data.get("use_count", 0),
                )
                self.memories[id_str] = entry
                self._index_entry(id_str, entry)
        except Exception:
            pass

    def _save(self) -> None:
        """Save memories to store."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for id_str, entry in self.memories.items():
            data[id_str] = {
                "content": entry.content,
                "memory_type": entry.memory_type.value,
                "created_at": entry.created_at,
                "importance": entry.importance,
                "source": entry.source,
                "tags": entry.tags,
                "metadata": entry.metadata,
                "last_used": entry.last_used,
                "use_count": entry.use_count,
            }

        self.store_path.write_text(json.dumps(data, indent=2))

    def _index_entry(self, id_str: str, entry: MemoryEntry) -> None:
        """Index entry for fast lookup."""
        # By type
        if entry.memory_type not in self._by_type:
            self._by_type[entry.memory_type] = []
        self._by_type[entry.memory_type].append(id_str)

        # By tag
        for tag in entry.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            self._by_tag[tag].append(id_str)

    def add(self, entry: MemoryEntry) -> str:
        """Add new memory."""
        id_str = f"mem_{len(self.memories)}_{int(time.time())}"
        self.memories[id_str] = entry
        self._index_entry(id_str, entry)
        self._save()
        return id_str

    def get(self, id_str: str) -> MemoryEntry | None:
        """Get memory by ID."""
        return self.memories.get(id_str)

    def update(self, id_str: str, updates: dict) -> bool:
        """Update memory."""
        entry = self.memories.get(id_str)
        if not entry:
            return False

        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        self._save()
        return True

    def delete(self, id_str: str) -> bool:
        """Delete memory."""
        if id_str not in self.memories:
            return False

        entry = self.memories[id_str]
        del self.memories[id_str]

        # Remove from indices
        if entry.memory_type in self._by_type:
            self._by_type[entry.memory_type] = [
                i for i in self._by_type[entry.memory_type] if i != id_str
            ]

        for tag in entry.tags:
            if tag in self._by_tag:
                self._by_tag[tag] = [
                    i for i in self._by_tag[tag] if i != id_str
                ]

        self._save()
        return True

    def search(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[MemorySearchResult]:
        """Search memories."""
        results = []

        # Get candidate IDs
        candidate_ids = set(self.memories.keys())

        if memory_type:
            candidate_ids &= set(self._by_type.get(memory_type, []))

        if tags:
            for tag in tags:
                candidate_ids &= set(self._by_tag.get(tag, []))

        # Score by relevance
        for id_str in candidate_ids:
            entry = self.memories[id_str]

            # Simple relevance scoring
            score = 0.0

            # Content match
            if query.lower() in entry.content.lower():
                score += 0.5

            # Tag match
            matched_tags = []
            query_words = query.lower().split()
            for tag in entry.tags:
                if tag.lower() in query_words:
                    score += 0.1
                    matched_tags.append(tag)

            # Importance boost
            score += entry.importance / 20

            # Usage boost
            score += min(entry.use_count * 0.05, 0.2)

            if score > 0:
                results.append(MemorySearchResult(
                    entry=entry,
                    relevance_score=score,
                    matched_tags=matched_tags,
                ))

        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results[:limit]

    def get_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        """Get all memories of type."""
        ids = self._by_type.get(memory_type, [])
        return [self.memories[i] for i in ids if i in self.memories]

    def mark_used(self, id_str: str) -> None:
        """Mark memory as used."""
        entry = self.memories.get(id_str)
        if entry:
            entry.last_used = time.time()
            entry.use_count += 1
            self._save()

    def get_stats(self) -> dict:
        """Get memory statistics."""
        return {
            "total_memories": len(self.memories),
            "by_type": {
                t.value: len(ids) for t, ids in self._by_type.items()
            },
            "total_tags": len(self._by_tag),
            "avg_importance": sum(e.importance for e in self.memories.values()) / len(self.memories) if self.memories else 0,
        }


class MemoryExtractor:
    """Extract memories from conversation."""

    def __init__(self, store: MemoryStore):
        self.store = store
        self._patterns = self._setup_patterns()

    def _setup_patterns(self) -> dict:
        """Setup extraction patterns."""
        return {
            "decision": [
                r"let's use (.+)",
                r"we'll go with (.+)",
                r"I decided to (.+)",
            ],
            "preference": [
                r"I prefer (.+)",
                r"I like (.+)",
                r"please use (.+)",
            ],
            "constraint": [
                r"don't (.+)",
                r"never (.+)",
                r"avoid (.+)",
            ],
            "fact": [
                r"the (.+) is (.+)",
                r"we're using (.+)",
            ],
        }

    def extract_from_message(self, message: dict) -> List[MemoryEntry]:
        """Extract memories from a message."""
        if message.get("role") != "user":
            return []

        content = message.get("content", "")
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
            content = " ".join(texts)

        memories = []

        # Look for explicit memory requests
        if "remember" in content.lower():
            memories.append(MemoryEntry(
                content=content,
                memory_type=MemoryType.USER,
                created_at=time.time(),
                importance=7,
                source="explicit_request",
                tags=["user_request", "remember"],
            ))

        # Look for decisions
        if any(p in content.lower() for p in ["let's", "we'll", "i decided", "going to use"]):
            memories.append(MemoryEntry(
                content=content,
                memory_type=MemoryType.PROJECT,
                created_at=time.time(),
                importance=5,
                source="decision",
                tags=["decision", "project"],
            ))

        # Look for preferences
        if any(p in content.lower() for p in ["i prefer", "i like", "please use"]):
            memories.append(MemoryEntry(
                content=content,
                memory_type=MemoryType.USER,
                created_at=time.time(),
                importance=6,
                source="preference",
                tags=["preference", "user"],
            ))

        return memories

    def extract_from_conversation(self, messages: List[dict]) -> List[MemoryEntry]:
        """Extract memories from full conversation."""
        all_memories = []

        for message in messages:
            memories = self.extract_from_message(message)
            all_memories.extend(memories)

        return all_memories


class SessionMemory:
    """Session-scoped memory."""

    def __init__(self, session_id: str, store: MemoryStore):
        self.session_id = session_id
        self.store = store
        self._session_memories: List[str] = []

    def add(self, content: str, memory_type: MemoryType = MemoryType.USER) -> str:
        """Add session memory."""
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            created_at=time.time(),
            source=f"session_{self.session_id}",
        )
        id_str = self.store.add(entry)
        self._session_memories.append(id_str)
        return id_str

    def get_relevant(self, query: str) -> List[MemoryEntry]:
        """Get relevant session memories."""
        results = self.store.search(query, limit=10)
        return [r.entry for r in results]

    def clear(self) -> int:
        """Clear session memories."""
        count = len(self._session_memories)
        for id_str in self._session_memories:
            self.store.delete(id_str)
        self._session_memories.clear()
        return count


# Global store
_memory_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Get global memory store."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store


def remember(content: str, memory_type: MemoryType = MemoryType.USER) -> str:
    """Add a memory."""
    store = get_memory_store()
    entry = MemoryEntry(
        content=content,
        memory_type=memory_type,
        created_at=time.time(),
    )
    return store.add(entry)


def recall(query: str, limit: int = 10) -> List[MemoryEntry]:
    """Recall memories matching query."""
    store = get_memory_store()
    results = store.search(query, limit=limit)
    return [r.entry for r in results]


__all__ = [
    "MemoryType",
    "MemoryEntry",
    "MemorySearchResult",
    "MemoryStore",
    "MemoryExtractor",
    "SessionMemory",
    "get_memory_store",
    "remember",
    "recall",
]
