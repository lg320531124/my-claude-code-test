"""WebFetchTool - Fetch URL content."""

from __future__ import annotations
import httpx
from typing import Optional, ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class WebFetchInput(ToolInput):
    """Input for WebFetchTool."""

    url: str
    prompt: Optional[str] = None
    timeout_ms: Optional[int] = None


class WebFetchTool(ToolDef):
    """Fetch content from URLs."""

    name: ClassVar[str] = "WebFetch"
    description: ClassVar[str] = "Fetch and extract content from a URL"
    input_schema: ClassVar[type] = WebFetchInput

    async def execute(self, input: WebFetchInput, ctx: ToolUseContext) -> ToolResult:
        """Fetch the URL."""
        try:
            timeout = (input.timeout_ms or 30000) / 1000

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(input.url, follow_redirects=True)

            if response.status_code != 200:
                return ToolResult(
                    content=f"HTTP {response.status_code}: {input.url}",
                    is_error=True,
                )

            # Get content
            content_type = response.headers.get("content-type", "")

            if "application/json" in content_type:
                # Format JSON
                import json
                data = response.json()
                content = json.dumps(data, indent=2)
            elif "text/html" in content_type:
                # Simple HTML to text conversion
                content = self._html_to_text(response.text)
            else:
                content = response.text

            # Truncate if too long
            max_len = 10000
            if len(content) > max_len:
                content = content[:max_len] + f"\n\n... [truncated, {len(content)} chars total]"

            return ToolResult(
                content=f"URL: {input.url}\n\n{content}",
                metadata={
                    "url": input.url,
                    "content_type": content_type,
                    "size": len(response.content),
                },
            )

        except httpx.TimeoutException:
            return ToolResult(
                content=f"Request timed out after {timeout}s",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"Error fetching URL: {e}",
                is_error=True,
            )

    def _html_to_text(self, html: str) -> str:
        """Simple HTML to text conversion."""
        import re

        # Remove scripts and styles
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove tags
        html = re.sub(r"<[^>]+>", " ", html)

        # Clean up whitespace
        html = re.sub(r"\s+", " ", html)
        html = re.sub(r"\n\s*\n", "\n\n", html)

        return html.strip()
