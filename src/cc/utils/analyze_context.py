"""Analyze Context - Analyze conversation context."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..utils.log import get_logger

logger = get_logger(__name__)


class ContextType(Enum):
    """Context types."""
    CODE = "code"
    CONVERSATION = "conversation"
    PROJECT = "project"
    TASK = "task"


class ContextPriority(Enum):
    """Context priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ContextItem:
    """Context item."""
    key: str
    value: Any
    type: ContextType
    priority: ContextPriority
    timestamp: float
    relevance: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextAnalysis:
    """Context analysis result."""
    total_items: int
    relevant_items: List[ContextItem]
    key_topics: List[str]
    complexity_score: float
    context_health: float


class ContextAnalyzer:
    """Analyze conversation context."""

    def __init__(self):
        self._context: Dict[str, ContextItem] = {}
        self._history: List[ContextAnalysis] = []

    def add_item(
        self,
        key: str,
        value: Any,
        type: ContextType = ContextType.CONVERSATION,
        priority: ContextPriority = ContextPriority.MEDIUM
    ) -> None:
        """Add context item."""
        import time

        self._context[key] = ContextItem(
            key=key,
            value=value,
            type=type,
            priority=priority,
            timestamp=time.time(),
        )

    def get_item(self, key: str) -> Optional[ContextItem]:
        """Get context item."""
        return self._context.get(key)

    def remove_item(self, key: str) -> bool:
        """Remove context item."""
        if key in self._context:
            del self._context[key]
            return True
        return False

    async def analyze(self) -> ContextAnalysis:
        """Analyze current context."""
        items = list(self._context.values())

        # Calculate relevance scores
        for item in items:
            item.relevance = self._calculate_relevance(item)

        # Sort by relevance
        sorted_items = sorted(items, key=lambda x: x.relevance, reverse=True)

        # Extract key topics
        topics = self._extract_topics(sorted_items)

        # Calculate metrics
        complexity = self._calculate_complexity(sorted_items)
        health = self._calculate_health(sorted_items)

        analysis = ContextAnalysis(
            total_items=len(items),
            relevant_items=sorted_items[:10],
            key_topics=topics,
            complexity_score=complexity,
            context_health=health,
        )

        self._history.append(analysis)
        return analysis

    def _calculate_relevance(self, item: ContextItem) -> float:
        """Calculate relevance score."""
        import time

        # Age factor (older = less relevant)
        age = time.time() - item.timestamp
        age_factor = 1.0 - min(age / 3600, 0.5)  # Max 50% reduction

        # Priority factor
        priority_weights = {
            ContextPriority.HIGH: 1.0,
            ContextPriority.MEDIUM: 0.7,
            ContextPriority.LOW: 0.4,
        }
        priority_factor = priority_weights.get(item.priority, 0.5)

        return age_factor * priority_factor

    def _extract_topics(self, items: List[ContextItem]) -> List[str]:
        """Extract key topics."""
        topics = []

        for item in items:
            if item.type == ContextType.CODE:
                topics.append(f"code:{item.key}")
            elif item.type == ContextType.PROJECT:
                topics.append(f"project:{item.key}")

        return topics[:5]

    def _calculate_complexity(self, items: List[ContextItem]) -> float:
        """Calculate complexity score."""
        if not items:
            return 0.0

        # Count unique keys
        unique_keys = len(set(i.key for i in items))

        # Count types
        type_count = len(set(i.type for i in items))

        return min(unique_keys * 0.1 + type_count * 0.2, 1.0)

    def _calculate_health(self, items: List[ContextItem]) -> float:
        """Calculate context health."""
        if not items:
            return 1.0

        # Check for stale items
        import time
        current = time.time()

        fresh_count = sum(
            1 for i in items
            if current - i.timestamp < 1800  # 30 minutes
        )

        return fresh_count / len(items)

    async def prune(self, max_items: int = 100) -> int:
        """Prune low-priority items."""
        items = list(self._context.values())

        # Sort by relevance
        sorted_items = sorted(items, key=lambda x: x.relevance)

        # Remove lowest relevance
        to_remove = sorted_items[:len(items) - max_items]

        for item in to_remove:
            self.remove_item(item.key)

        return len(to_remove)

    async def summarize(self) -> Dict[str, Any]:
        """Summarize context."""
        analysis = await self.analyze()

        return {
            "total": analysis.total_items,
            "topics": analysis.key_topics,
            "complexity": analysis.complexity_score,
            "health": analysis.context_health,
            "top_items": [
                {"key": i.key, "type": i.type.value}
                for i in analysis.relevant_items[:5]
            ],
        }

    def get_history(self) -> List[ContextAnalysis]:
        """Get analysis history."""
        return self._history

    def clear(self) -> None:
        """Clear all context."""
        self._context.clear()


__all__ = [
    "ContextType",
    "ContextPriority",
    "ContextItem",
    "ContextAnalysis",
    "ContextAnalyzer",
]