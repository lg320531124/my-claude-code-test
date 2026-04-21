"""Search Hook - Async search operations."""

from __future__ import annotations
import asyncio
import re
from typing import Any, Dict, List, Optional, Callable, AsyncIterator, Pattern
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SearchType(Enum):
    """Search types."""
    TEXT = "text"
    REGEX = "regex"
    FUZZY = "fuzzy"
    FILE = "file"
    CODE = "code"


@dataclass
class SearchMatch:
    """Search match."""
    file_path: str
    line_number: int
    column: int = 0
    matched_text: str = ""
    context_before: str = ""
    context_after: str = ""
    match_type: SearchType = SearchType.TEXT


@dataclass
class SearchResult:
    """Search result."""
    query: str
    matches: List[SearchMatch] = field(default_factory=list)
    total_matches: int = 0
    files_matched: int = 0
    search_time: float = 0.0


class SearchHook:
    """Async search operations hook."""

    def __init__(self):
        self._search_history: List[str] = []
        self._file_cache: Dict[str, str] = {}

    async def search_text(
        self,
        query: str,
        paths: List[str],
        case_sensitive: bool = False,
        max_results: int = 100,
    ) -> SearchResult:
        """Search for text in files.

        Args:
            query: Search query
            paths: Paths to search
            case_sensitive: Case sensitive search
            max_results: Maximum results

        Returns:
            SearchResult
        """
        import time
        start_time = time.time()

        result = SearchResult(query=query)

        if not case_sensitive:
            query_lower = query.lower()

        for path in paths:
            path_obj = Path(path)
            if not path_obj.exists():
                continue

            if path_obj.is_file():
                await self._search_in_file(
                    path_obj,
                    query,
                    case_sensitive,
                    result,
                    max_results,
                )
            elif path_obj.is_dir():
                await self._search_in_dir(
                    path_obj,
                    query,
                    case_sensitive,
                    result,
                    max_results,
                )

            if len(result.matches) >= max_results:
                break

        result.total_matches = len(result.matches)
        result.files_matched = len(set(m.file_path for m in result.matches))
        result.search_time = time.time() - start_time

        self._search_history.append(query)
        return result

    async def search_regex(
        self,
        pattern: str,
        paths: List[str],
        flags: int = 0,
        max_results: int = 100,
    ) -> SearchResult:
        """Search with regex pattern.

        Args:
            pattern: Regex pattern
            paths: Paths to search
            flags: Regex flags
            max_results: Maximum results

        Returns:
            SearchResult
        """
        import time
        start_time = time.time()

        try:
            regex = re.compile(pattern, flags)
        except re.error:
            return SearchResult(query=pattern)

        result = SearchResult(query=pattern)

        for path in paths:
            path_obj = Path(path)
            if not path_obj.exists():
                continue

            if path_obj.is_file():
                await self._search_regex_in_file(
                    path_obj,
                    regex,
                    result,
                    max_results,
                )
            elif path_obj.is_dir():
                await self._search_regex_in_dir(
                    path_obj,
                    regex,
                    result,
                    max_results,
                )

            if len(result.matches) >= max_results:
                break

        result.total_matches = len(result.matches)
        result.files_matched = len(set(m.file_path for m in result.matches))
        result.search_time = time.time() - start_time

        return result

    async def search_fuzzy(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.6,
    ) -> List[Tuple[str, float]]:
        """Fuzzy search in candidates.

        Args:
            query: Search query
            candidates: Candidates to search
            threshold: Match threshold

        Returns:
            List of (candidate, score) tuples
        """
        from difflib import SequenceMatcher

        results = []
        query_lower = query.lower()

        for candidate in candidates:
            candidate_lower = candidate.lower()
            score = SequenceMatcher(None, query_lower, candidate_lower).ratio()

            if score >= threshold:
                results.append((candidate, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    async def search_code(
        self,
        query: str,
        paths: List[str],
        language: Optional[str] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search for code patterns.

        Args:
            query: Code query
            paths: Paths to search
            language: Optional language filter
            max_results: Maximum results

        Returns:
            SearchResult
        """
        # Language-specific patterns
        lang_patterns = {
            "python": ["*.py"],
            "javascript": ["*.js", "*.jsx", "*.ts", "*.tsx"],
            "go": ["*.go"],
            "rust": ["*.rs"],
            "java": ["*.java"],
            "c": ["*.c", "*.h"],
            "cpp": ["*.cpp", "*.hpp", "*.cc"],
            "ruby": ["*.rb"],
            "php": ["*.php"],
        }

        patterns = lang_patterns.get(language, ["*"]) if language else ["*"]

        result = SearchResult(query=query)

        for path in paths:
            path_obj = Path(path)
            if not path_obj.exists():
                continue

            for pattern in patterns:
                for file_path in path_obj.rglob(pattern):
                    if not file_path.is_file():
                        continue

                    await self._search_in_file(
                        file_path,
                        query,
                        False,  # Case insensitive for code
                        result,
                        max_results,
                    )

                    if len(result.matches) >= max_results:
                        break

        result.total_matches = len(result.matches)
        result.files_matched = len(set(m.file_path for m in result.matches))

        return result

    async def _search_in_file(
        self,
        file_path: Path,
        query: str,
        case_sensitive: bool,
        result: SearchResult,
        max_results: int,
    ) -> None:
        """Search in single file."""
        try:
            from ..utils.async_io import read_file_async
            content = await read_file_async(str(file_path))

            lines = content.splitlines()
            query_to_match = query if case_sensitive else query.lower()

            for i, line in enumerate(lines):
                line_to_match = line if case_sensitive else line.lower()

                if query_to_match in line_to_match:
                    match = SearchMatch(
                        file_path=str(file_path),
                        line_number=i + 1,
                        column=line_to_match.index(query_to_match),
                        matched_text=line,
                        context_before=lines[i - 1] if i > 0 else "",
                        context_after=lines[i + 1] if i < len(lines) - 1 else "",
                        match_type=SearchType.TEXT,
                    )
                    result.matches.append(match)

                    if len(result.matches) >= max_results:
                        return

        except Exception:
            pass

    async def _search_in_dir(
        self,
        dir_path: Path,
        query: str,
        case_sensitive: bool,
        result: SearchResult,
        max_results: int,
    ) -> None:
        """Search in directory."""
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip binary files
            if self._is_binary_file(file_path):
                continue

            await self._search_in_file(
                file_path,
                query,
                case_sensitive,
                result,
                max_results,
            )

            if len(result.matches) >= max_results:
                return

    async def _search_regex_in_file(
        self,
        file_path: Path,
        regex: Pattern,
        result: SearchResult,
        max_results: int,
    ) -> None:
        """Search regex in file."""
        try:
            from ..utils.async_io import read_file_async
            content = await read_file_async(str(file_path))

            lines = content.splitlines()

            for i, line in enumerate(lines):
                for match in regex.finditer(line):
                    search_match = SearchMatch(
                        file_path=str(file_path),
                        line_number=i + 1,
                        column=match.start(),
                        matched_text=match.group(),
                        context_before=lines[i - 1] if i > 0 else "",
                        context_after=lines[i + 1] if i < len(lines) - 1 else "",
                        match_type=SearchType.REGEX,
                    )
                    result.matches.append(search_match)

                    if len(result.matches) >= max_results:
                        return

        except Exception:
            pass

    async def _search_regex_in_dir(
        self,
        dir_path: Path,
        regex: Pattern,
        result: SearchResult,
        max_results: int,
    ) -> None:
        """Search regex in directory."""
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue

            if self._is_binary_file(file_path):
                continue

            await self._search_regex_in_file(
                file_path,
                regex,
                result,
                max_results,
            )

            if len(result.matches) >= max_results:
                return

    def _is_binary_file(self, path: Path) -> bool:
        """Check if file is binary."""
        binary_extensions = {
            ".exe", ".dll", ".so", ".dylib", ".bin",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
            ".pdf", ".zip", ".tar", ".gz", ".bz2",
            ".mp3", ".mp4", ".avi", ".mov", ".wav",
            ".pyc", ".pyd", ".class",
        }
        return path.suffix.lower() in binary_extensions

    def get_history(self, limit: int = 10) -> List[str]:
        """Get search history.

        Args:
            limit: Maximum items

        Returns:
            Search history
        """
        return self._search_history[-limit:]

    def clear_history(self) -> None:
        """Clear search history."""
        self._search_history.clear()

    def clear_cache(self) -> None:
        """Clear file cache."""
        self._file_cache.clear()


# Global search hook
_search_hook: Optional[SearchHook] = None


def get_search_hook() -> SearchHook:
    """Get global search hook."""
    global _search_hook
    if _search_hook is None:
        _search_hook = SearchHook()
    return _search_hook


async def use_search() -> Dict[str, Any]:
    """Search hook for hooks module.

    Returns search functions.
    """
    hook = get_search_hook()

    return {
        "search_text": hook.search_text,
        "search_regex": hook.search_regex,
        "search_fuzzy": hook.search_fuzzy,
        "search_code": hook.search_code,
        "get_history": hook.get_history,
        "clear_history": hook.clear_history,
    }


# Type alias for fuzzy search result
from typing import Tuple


__all__ = [
    "SearchType",
    "SearchMatch",
    "SearchResult",
    "SearchHook",
    "get_search_hook",
    "use_search",
]