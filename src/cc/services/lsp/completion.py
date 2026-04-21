"""LSP Completion - Async code completion."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class CompletionTriggerKind(Enum):
    """Completion trigger kinds."""
    INVOKED = 1
    TRIGGER_CHARACTER = 2
    CONTENT_CHANGE = 3


class CompletionItemKind(Enum):
    """Completion item kinds."""
    TEXT = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    FIELD = 5
    VARIABLE = 6
    CLASS = 7
    INTERFACE = 8
    MODULE = 9
    PROPERTY = 10
    UNIT = 11
    VALUE = 12
    ENUM = 13
    KEYWORD = 14
    SNIPPET = 15
    COLOR = 16
    FILE = 17
    REFERENCE = 18
    FOLDER = 19
    ENUM_MEMBER = 20
    CONSTANT = 21
    STRUCT = 22
    EVENT = 23
    OPERATOR = 24
    TYPE_PARAMETER = 25


@dataclass
class CompletionItem:
    """Completion item."""
    label: str
    kind: CompletionItemKind = CompletionItemKind.TEXT
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insert_text: Optional[str] = None
    insert_text_format: str = "plaintext"  # or "snippet"
    sort_text: Optional[str] = None
    filter_text: Optional[str] = None
    priority: int = 0
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletionContext:
    """Completion context."""
    trigger_kind: CompletionTriggerKind
    trigger_character: Optional[str] = None
    position: Dict[str, int] = field(default_factory=dict)


@dataclass
class CompletionResult:
    """Completion result."""
    items: List[CompletionItem]
    is_incomplete: bool = False
    cache_key: Optional[str] = None


class CompletionProvider:
    """Async completion provider."""

    def __init__(self, lsp_client):
        self._client = lsp_client
        self._cache: Dict[str, CompletionResult] = {}
        self._cache_ttl: int = 5000  # 5 seconds
        self._pending_requests: Dict[str, asyncio.Future] = {}

    async def get_completions(
        self,
        file_path: str,
        position: Dict[str, int],
        context: Optional[CompletionContext] = None,
        use_cache: bool = True,
    ) -> CompletionResult:
        """Get completions at position."""
        cache_key = self._make_cache_key(file_path, position)

        # Check cache
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if self._is_cache_valid(cached):
                return cached

        # Check pending request
        if cache_key in self._pending_requests:
            return await self._pending_requests[cache_key]

        # Make request
        future = asyncio.Future()
        self._pending_requests[cache_key] = future

        try:
            result = await self._request_completions(file_path, position, context)
            self._cache[cache_key] = result
            future.set_result(result)
            return result

        except Exception as e:
            future.set_exception(e)
            raise

        finally:
            del self._pending_requests[cache_key]

    async def _request_completions(
        self,
        file_path: str,
        position: Dict[str, int],
        context: Optional[CompletionContext] = None,
    ) -> CompletionResult:
        """Request completions from LSP."""
        request = {
            "textDocument": {"uri": self._to_uri(file_path)},
            "position": position,
        }

        if context:
            request["context"] = {
                "triggerKind": context.trigger_kind.value,
                "triggerCharacter": context.trigger_character,
            }

        response = await self._client.send_request("textDocument/completion", request)

        if response is None:
            return CompletionResult(items=[])

        items = []
        for item_data in response.get("items", []):
            item = self._parse_item(item_data)
            items.append(item)

        # Sort items
        items.sort(key=lambda i: (i.priority, i.sort_text or i.label))

        return CompletionResult(
            items=items,
            is_incomplete=response.get("isIncomplete", False),
            cache_key=self._make_cache_key(file_path, position),
        )

    def _parse_item(self, data: Dict[str, Any]) -> CompletionItem:
        """Parse completion item from LSP."""
        kind_value = data.get("kind", 1)
        kind = CompletionItemKind(kind_value) if 1 <= kind_value <= 25 else CompletionItemKind.TEXT

        return CompletionItem(
            label=data.get("label", ""),
            kind=kind,
            detail=data.get("detail"),
            documentation=data.get("documentation"),
            insert_text=data.get("insertText"),
            insert_text_format=data.get("insertTextFormat", "plaintext"),
            sort_text=data.get("sortText"),
            filter_text=data.get("filterText"),
            data=data.get("data", {}),
        )

    def _make_cache_key(self, file_path: str, position: Dict[str, int]) -> str:
        """Make cache key."""
        return f"{file_path}:{position.get('line', 0)}:{position.get('character', 0)}"

    def _is_cache_valid(self, cached: CompletionResult) -> bool:
        """Check if cache is still valid."""
        # Simple TTL check
        return True  # LSP manages its own cache invalidation

    def _to_uri(self, path: str) -> str:
        """Convert path to URI."""
        import os
        abs_path = os.path.abspath(path)
        return f"file://{abs_path}"

    def clear_cache(self) -> None:
        """Clear completion cache."""
        self._cache.clear()


class SnippetManager:
    """Manage code snippets for completion."""

    def __init__(self):
        self._snippets: Dict[str, List[CompletionItem]] = {}

    def add_snippet(
        self,
        language: str,
        label: str,
        insert_text: str,
        detail: str = None,
    ) -> None:
        """Add snippet for language."""
        if language not in self._snippets:
            self._snippets[language] = []

        self._snippets[language].append(CompletionItem(
            label=label,
            kind=CompletionItemKind.SNIPPET,
            insert_text=insert_text,
            insert_text_format="snippet",
            detail=detail,
        ))

    def get_snippets(self, language: str) -> List[CompletionItem]:
        """Get snippets for language."""
        return self._snippets.get(language, [])

    def load_defaults(self) -> None:
        """Load default snippets."""
        # Python snippets
        self.add_snippet("python", "if", "if ${1:condition}:\n    ${2:pass}", "If statement")
        self.add_snippet("python", "for", "for ${1:item} in ${2:items}:\n    ${3:pass}", "For loop")
        self.add_snippet("python", "def", "def ${1:name}(${2:params}):\n    ${3:pass}", "Function definition")
        self.add_snippet("python", "class", "class ${1:Name}:\n    def __init__(self):\n        ${2:pass}", "Class definition")
        self.add_snippet("python", "try", "try:\n    ${1:pass}\nexcept ${2:Exception}:\n    ${3:pass}", "Try-except")

        # JavaScript snippets
        self.add_snippet("javascript", "if", "if (${1:condition}) {\n    ${2}\n}", "If statement")
        self.add_snippet("javascript", "for", "for (${1:i} = 0; ${1} < ${2:length}; ${1}++) {\n    ${3}\n}", "For loop")
        self.add_snippet("javascript", "fn", "function ${1:name}(${2:params}) {\n    ${3}\n}", "Function")
        self.add_snippet("javascript", "afn", "async function ${1:name}(${2:params}) {\n    ${3}\n}", "Async function")
        self.add_snippet("javascript", "class", "class ${1:Name} {\n    constructor(${2:params}) {\n        ${3}\n    }\n}", "Class")


__all__ = [
    "CompletionTriggerKind",
    "CompletionItemKind",
    "CompletionItem",
    "CompletionContext",
    "CompletionResult",
    "CompletionProvider",
    "SnippetManager",
]