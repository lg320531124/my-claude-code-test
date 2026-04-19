"""URL Tool - URL parsing and manipulation."""

from __future__ import annotations
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from typing import ClassVar, Dict, Optional, List, Any
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class URLInput(ToolInput):
    """Input for URLTool."""
    action: str = Field(description="Action: parse, build, encode, decode, validate")
    url: Optional[str] = Field(default=None, description="URL to process")
    scheme: Optional[str] = Field(default=None, description="URL scheme")
    host: Optional[str] = Field(default=None, description="Host")
    path: Optional[str] = Field(default=None, description="Path")
    query: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")


class URLInfo(BaseModel):
    """Parsed URL info."""
    scheme: str = ""
    netloc: str = ""
    path: str = ""
    params: str = ""
    query: str = ""
    fragment: str = ""
    host: Optional[str] = None
    port: Optional[int] = None


class URLTool(ToolDef):
    """URL parsing and manipulation."""

    name: ClassVar[str] = "URL"
    description: ClassVar[str] = "Parse and manipulate URLs"
    input_schema: ClassVar[type] = URLInput

    async def execute(self, input: URLInput, ctx: ToolUseContext) -> ToolResult:
        """Execute URL operation."""
        action = input.action

        if action == "parse":
            return self._parse_url(input.url)
        elif action == "build":
            return self._build_url(input.scheme, input.host, input.path, input.query)
        elif action == "encode":
            return self._encode(input.url)
        elif action == "decode":
            return self._decode(input.url)
        elif action == "validate":
            return self._validate(input.url)
        else:
            return ToolResult(content=f"Unknown action: {action}", is_error=True)

    def _parse_url(self, url: Optional[str]) -> ToolResult:
        """Parse URL."""
        if not url:
            return ToolResult(content="URL required", is_error=True)

        parsed = urlparse(url)

        # Extract host and port
        host = parsed.hostname
        port = parsed.port

        info = URLInfo(
            scheme=parsed.scheme,
            netloc=parsed.netloc,
            path=parsed.path,
            params=parsed.params,
            query=parsed.query,
            fragment=parsed.fragment,
            host=host,
            port=port,
        )

        # Parse query parameters
        query_params = parse_qs(parsed.query)

        result = f"URL: {url}\n"
        result += f"Scheme: {info.scheme}\n"
        result += f"Host: {info.host or 'none'}\n"
        result += f"Port: {info.port or 'default'}\n"
        result += f"Path: {info.path}\n"
        result += f"Query: {info.query}\n"
        result += f"Fragment: {info.fragment}\n"

        if query_params:
            result += "\nQuery Parameters:\n"
            for key, values in query_params.items():
                result += f"  {key}: {values}\n"

        return ToolResult(
            content=result,
            metadata={"parsed": info.model_dump(), "query_params": query_params},
        )

    def _build_url(
        self,
        scheme: Optional[str],
        host: Optional[str],
        path: Optional[str],
        query: Optional[Dict[str, Any]],
    ) -> ToolResult:
        """Build URL."""
        if not host:
            return ToolResult(content="Host required", is_error=True)

        scheme = scheme or "https"
        path = path or ""

        # Build query string
        query_str = ""
        if query:
            query_str = urlencode(query)

        # Build URL
        url = urlunparse((
            scheme,
            host,
            path,
            "",  # params
            query_str,
            "",  # fragment
        ))

        return ToolResult(
            content=f"Built URL: {url}",
            metadata={"url": url},
        )

    def _encode(self, url: Optional[str]) -> ToolResult:
        """Encode URL."""
        if not url:
            return ToolResult(content="URL required", is_error=True)

        from urllib.parse import quote
        encoded = quote(url, safe=":/?&=")

        return ToolResult(
            content=encoded,
            metadata={"original": url, "encoded": encoded},
        )

    def _decode(self, url: Optional[str]) -> ToolResult:
        """Decode URL."""
        if not url:
            return ToolResult(content="URL required", is_error=True)

        from urllib.parse import unquote
        decoded = unquote(url)

        return ToolResult(
            content=decoded,
            metadata={"original": url, "decoded": decoded},
        )

    def _validate(self, url: Optional[str]) -> ToolResult:
        """Validate URL."""
        if not url:
            return ToolResult(content="URL required", is_error=True)

        try:
            parsed = urlparse(url)

            # Check scheme
            if not parsed.scheme:
                return ToolResult(
                    content="Invalid URL: missing scheme",
                    is_error=True,
                    metadata={"valid": False},
                )

            # Check host
            if not parsed.netloc:
                return ToolResult(
                    content="Invalid URL: missing host",
                    is_error=True,
                    metadata={"valid": False},
                )

            return ToolResult(
                content=f"URL is valid: {url}",
                metadata={"valid": True, "scheme": parsed.scheme, "host": parsed.netloc},
            )
        except Exception as e:
            return ToolResult(
                content=f"URL validation error: {e}",
                is_error=True,
                metadata={"valid": False},
            )


__all__ = ["URLTool", "URLInput", "URLInfo"]