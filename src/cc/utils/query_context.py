"""Query Context - Query context for answers."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from .analyze_context import ContextAnalyzer, ContextItem, ContextType

from ..utils.log import get_logger

logger = get_logger(__name__)


class QueryType(Enum):
    """Query types."""
    SEARCH = "search"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    EXPLAIN = "explain"


class QueryResultType(Enum):
    """Query result types."""
    ITEMS = "items"
    SUMMARY = "summary"
    EXPLANATION = "explanation"


@dataclass
class Query:
    """Context query."""
    type: QueryType
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 10


@dataclass
class QueryResult:
    """Query result."""
    type: QueryResultType
    items: List[ContextItem] = field(default_factory=list)
    summary: Optional[str] = None
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryContext:
    """Query context for answers."""

    def __init__(self, analyzer: Optional[ContextAnalyzer] = None):
        self.analyzer = analyzer or ContextAnalyzer()
        self._handlers: Dict[QueryType, Callable] = {}

    def register_handler(
        self,
        query_type: QueryType,
        handler: Callable
    ) -> None:
        """Register query handler."""
        self._handlers[query_type] = handler

    async def query(
        self,
        query: Query
    ) -> QueryResult:
        """Execute query."""
        handler = self._handlers.get(query.type)

        if handler:
            return await handler(query)

        # Default handlers
        if query.type == QueryType.SEARCH:
            return await self._search(query)
        elif query.type == QueryType.FILTER:
            return await self._filter(query)
        elif query.type == QueryType.AGGREGATE:
            return await self._aggregate(query)
        elif query.type == QueryType.EXPLAIN:
            return await self._explain(query)

        return QueryResult(type=QueryResultType.ITEMS)

    async def _search(self, query: Query) -> QueryResult:
        """Search context."""
        items = []

        for key, item in self.analyzer._context.items():
            # Match query
            if query.query.lower() in key.lower():
                items.append(item)
            elif query.query.lower() in str(item.value).lower():
                items.append(item)

        # Apply limit
        items = items[:query.limit]

        return QueryResult(
            type=QueryResultType.ITEMS,
            items=items,
        )

    async def _filter(self, query: Query) -> QueryResult:
        """Filter context."""
        items = []

        for key, item in self.analyzer._context.items():
            # Apply filters
            match = True

            for filter_key, filter_value in query.filters.items():
                if filter_key == "type":
                    if item.type.value != filter_value:
                        match = False
                elif filter_key == "priority":
                    if item.priority.value != filter_value:
                        match = False
                elif filter_key == "min_relevance":
                    if item.relevance < float(filter_value):
                        match = False

            if match:
                items.append(item)

        return QueryResult(
            type=QueryResultType.ITEMS,
            items=items[:query.limit],
        )

    async def _aggregate(self, query: Query) -> QueryResult:
        """Aggregate context."""
        analysis = await self.analyzer.analyze()

        return QueryResult(
            type=QueryResultType.SUMMARY,
            summary=f"Total: {analysis.total_items}, Topics: {analysis.key_topics}",
            metadata={
                "total": analysis.total_items,
                "complexity": analysis.complexity_score,
                "health": analysis.context_health,
            },
        )

    async def _explain(self, query: Query) -> QueryResult:
        """Explain context."""
        items = list(self.analyzer._context.items())

        # Find matching items
        matching = []
        for key, item in items:
            if query.query.lower() in key.lower():
                matching.append((key, item))

        # Generate explanation
        explanation = f"Found {len(matching)} items matching '{query.query}'"

        for key, item in matching[:3]:
            explanation += f"\n- {key}: {item.type.value}"

        return QueryResult(
            type=QueryResultType.EXPLANATION,
            explanation=explanation,
            items=[item for _, item in matching[:query.limit]],
        )

    async def find_by_key(self, key: str) -> Optional[ContextItem]:
        """Find item by key."""
        return self.analyzer.get_item(key)

    async def find_by_type(
        self,
        type: ContextType,
        limit: int = 10
    ) -> List[ContextItem]:
        """Find items by type."""
        query = Query(
            type=QueryType.FILTER,
            query="",
            filters={"type": type.value},
            limit=limit,
        )

        result = await self.query(query)
        return result.items

    async def get_top_items(self, limit: int = 10) -> List[ContextItem]:
        """Get top relevant items."""
        analysis = await self.analyzer.analyze()
        return analysis.relevant_items[:limit]

    async def explain_item(self, key: str) -> str:
        """Explain single item."""
        item = self.analyzer.get_item(key)

        if not item:
            return f"No item found with key '{key}'"

        return f"Key: {key}\nType: {item.type.value}\nPriority: {item.priority.value}\nRelevance: {item.relevance}"


__all__ = [
    "QueryType",
    "QueryResultType",
    "Query",
    "QueryResult",
    "QueryContext",
]