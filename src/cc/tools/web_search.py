"""WebSearchTool - Web search integration."""

from __future__ import annotations
import httpx
from typing import ClassVar, List, Optional

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class WebSearchInput(ToolInput):
    """Input for WebSearchTool."""

    query: str
    allowed_domains: Optional[List[str]] = None
    blocked_domains: Optional[List[str]] = None


class WebSearchTool(ToolDef):
    """Search the web for information."""

    name: ClassVar[str] = "WebSearch"
    description: ClassVar[str] = "Search the web for up-to-date information"
    input_schema: ClassVar[type] = WebSearchInput

    # Default search API (can be overridden)
    search_api_url: str = "https://api.duckduckgo.com/"

    async def execute(self, input: WebSearchInput, ctx: ToolUseContext) -> ToolResult:
        """Execute web search."""
        try:
            # Use DuckDuckGo Instant Answer API (free, no auth needed)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.search_api_url,
                    params={
                        "q": input.query,
                        "format": "json",
                        "no_html": 1,
                        "skip_disambig": 1,
                    },
                )

            if response.status_code != 200:
                return ToolResult(
                    content=f"Search failed: HTTP {response.status_code}",
                    is_error=True,
                )

            data = response.json()

            # Format results
            results = []

            # Abstract
            if data.get("Abstract"):
                results.append(f"Summary: {data['Abstract']}")
                if data.get("AbstractURL"):
                    results.append(f"Source: {data['AbstractURL']}")

            # Related topics
            if data.get("RelatedTopics"):
                for topic in data["RelatedTopics"][:5]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append(f"- {topic['Text']}")
                        if "FirstURL" in topic:
                            results.append(f"  URL: {topic['FirstURL']}")

            # Definition
            if data.get("Definition"):
                results.append(f"Definition: {data['Definition']}")

            if not results:
                return ToolResult(
                    content=f"No results found for: {input.query}",
                    metadata={"query": input.query},
                )

            return ToolResult(
                content=f"Search results for: {input.query}\n\n" + "\n".join(results),
                metadata={"query": input.query, "source": "DuckDuckGo"},
            )

        except Exception as e:
            return ToolResult(
                content=f"Search error: {e}",
                is_error=True,
            )
