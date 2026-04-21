"""LSP Hover - Async hover information."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class HoverKind(Enum):
    """Types of hover information."""
    TYPE = "type"
    DOCUMENTATION = "documentation"
    SIGNATURE = "signature"
    DEFINITION = "definition"
    REFERENCES = "references"


@dataclass
class HoverMarkup:
    """Markup content for hover."""
    kind: str  # "plaintext" or "markdown"
    value: str


@dataclass
class HoverResult:
    """Hover result."""
    file_path: str
    position: Dict[str, int]
    contents: List[HoverMarkup]
    range: Optional[Dict[str, Any]] = None
    kind: HoverKind = HoverKind.TYPE

    def to_display(self) -> str:
        """Convert to display string."""
        parts = []
        for content in self.contents:
            parts.append(content.value)
        return "\n\n".join(parts)


class HoverProvider:
    """Async hover provider."""

    def __init__(self, lsp_client):
        self._client = lsp_client
        self._cache: Dict[str, HoverResult] = {}
        self._cache_ttl: int = 10000  # 10 seconds

    async def get_hover(
        self,
        file_path: str,
        position: Dict[str, int],
        use_cache: bool = True,
    ) -> Optional[HoverResult]:
        """Get hover information at position."""
        cache_key = self._make_cache_key(file_path, position)

        # Check cache
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Request hover
        request = {
            "textDocument": {"uri": self._to_uri(file_path)},
            "position": position,
        }

        response = await self._client.send_request("textDocument/hover", request)

        if response is None:
            return None

        result = self._parse_hover(file_path, position, response)
        self._cache[cache_key] = result

        return result

    def _parse_hover(
        self,
        file_path: str,
        position: Dict[str, int],
        data: Dict[str, Any],
    ) -> HoverResult:
        """Parse hover response."""
        contents = []

        # Handle different content formats
        content_data = data.get("contents")

        if content_data is None:
            pass

        elif isinstance(content_data, str):
            contents.append(HoverMarkup(kind="plaintext", value=content_data))

        elif isinstance(content_data, list):
            for item in content_data:
                if isinstance(item, str):
                    contents.append(HoverMarkup(kind="plaintext", value=item))
                elif isinstance(item, dict):
                    contents.append(HoverMarkup(
                        kind=item.get("kind", "plaintext"),
                        value=item.get("value", ""),
                    ))

        elif isinstance(content_data, dict):
            contents.append(HoverMarkup(
                kind=content_data.get("kind", "plaintext"),
                value=content_data.get("value", ""),
            ))

        return HoverResult(
            file_path=file_path,
            position=position,
            contents=contents,
            range=data.get("range"),
        )

    def _make_cache_key(self, file_path: str, position: Dict[str, int]) -> str:
        """Make cache key."""
        return f"{file_path}:{position.get('line', 0)}:{position.get('character', 0)}"

    def _to_uri(self, path: str) -> str:
        """Convert path to URI."""
        import os
        abs_path = os.path.abspath(path)
        return f"file://{abs_path}"

    def clear_cache(self) -> None:
        """Clear hover cache."""
        self._cache.clear()


class SignatureHelpProvider:
    """Async signature help provider."""

    def __init__(self, lsp_client):
        self._client = lsp_client

    async def get_signature_help(
        self,
        file_path: str,
        position: Dict[str, int],
    ) -> Optional[Dict[str, Any]]:
        """Get signature help at position."""
        request = {
            "textDocument": {"uri": self._to_uri(file_path)},
            "position": position,
        }

        response = await self._client.send_request("textDocument/signatureHelp", request)

        if response is None:
            return None

        return {
            "signatures": response.get("signatures", []),
            "active_signature": response.get("activeSignature", 0),
            "active_parameter": response.get("activeParameter", 0),
        }

    def _to_uri(self, path: str) -> str:
        """Convert path to URI."""
        import os
        abs_path = os.path.abspath(path)
        return f"file://{abs_path}"


class DefinitionProvider:
    """Async definition provider."""

    def __init__(self, lsp_client):
        self._client = lsp_client

    async def get_definition(
        self,
        file_path: str,
        position: Dict[str, int],
    ) -> Optional[Dict[str, Any]]:
        """Get definition location."""
        request = {
            "textDocument": {"uri": self._to_uri(file_path)},
            "position": position,
        }

        response = await self._client.send_request("textDocument/definition", request)

        if response is None:
            return None

        # Handle single or multiple locations
        if isinstance(response, list):
            return {"locations": response}
        else:
            return {"location": response}

    async def get_type_definition(
        self,
        file_path: str,
        position: Dict[str, int],
    ) -> Optional[Dict[str, Any]]:
        """Get type definition location."""
        request = {
            "textDocument": {"uri": self._to_uri(file_path)},
            "position": position,
        }

        response = await self._client.send_request("textDocument/typeDefinition", request)

        if response is None:
            return None

        if isinstance(response, list):
            return {"locations": response}
        else:
            return {"location": response}

    def _to_uri(self, path: str) -> str:
        """Convert path to URI."""
        import os
        abs_path = os.path.abspath(path)
        return f"file://{abs_path}"


__all__ = [
    "HoverKind",
    "HoverMarkup",
    "HoverResult",
    "HoverProvider",
    "SignatureHelpProvider",
    "DefinitionProvider",
]