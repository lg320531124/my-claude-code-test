"""LSP Diagnostics - Async code diagnostics."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class DiagnosticSeverity(Enum):
    """Diagnostic severity levels."""
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


class DiagnosticTag(Enum):
    """Diagnostic tags."""
    UNNECESSARY = 1
    DEPRECATED = 2


@dataclass
class DiagnosticRelatedInfo:
    """Related information for diagnostic."""
    location: Dict[str, Any]
    message: str


@dataclass
class Diagnostic:
    """Code diagnostic."""
    file_path: str
    range: Dict[str, Any]  # start, end positions
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    code: Optional[str] = None
    source: Optional[str] = None
    message: str = ""
    related_info: List[DiagnosticRelatedInfo] = field(default_factory=list)
    tags: List[DiagnosticTag] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_display(self) -> str:
        """Convert to display string."""
        severity_str = {
            DiagnosticSeverity.ERROR: "error",
            DiagnosticSeverity.WARNING: "warning",
            DiagnosticSeverity.INFORMATION: "info",
            DiagnosticSeverity.HINT: "hint",
        }.get(self.severity, "error")

        line = self.range.get("start", {}).get("line", 0) + 1

        return f"{self.file_path}:{line}: [{severity_str}] {self.message}"


@dataclass
class DiagnosticSummary:
    """Summary of diagnostics."""
    total_errors: int = 0
    total_warnings: int = 0
    total_info: int = 0
    total_hints: int = 0
    by_file: Dict[str, int] = field(default_factory=dict)
    by_source: Dict[str, int] = field(default_factory=dict)


class DiagnosticManager:
    """Manage diagnostics from LSP."""

    def __init__(self, lsp_client):
        self._client = lsp_client
        self._diagnostics: Dict[str, List[Diagnostic]] = defaultdict(list)
        self._callbacks: List[Callable] = []
        self._watching: bool = False

    async def get_diagnostics(
        self,
        file_path: str,
    ) -> List[Diagnostic]:
        """Get diagnostics for file."""
        return self._diagnostics.get(file_path, [])

    async def get_all_diagnostics(self) -> Dict[str, List[Diagnostic]]:
        """Get all diagnostics."""
        return dict(self._diagnostics)

    async def get_summary(self) -> DiagnosticSummary:
        """Get diagnostic summary."""
        summary = DiagnosticSummary()

        for file_path, diagnostics in self._diagnostics.items():
            summary.by_file[file_path] = len(diagnostics)

            for diag in diagnostics:
                if diag.severity == DiagnosticSeverity.ERROR:
                    summary.total_errors += 1
                elif diag.severity == DiagnosticSeverity.WARNING:
                    summary.total_warnings += 1
                elif diag.severity == DiagnosticSeverity.INFORMATION:
                    summary.total_info += 1
                elif diag.severity == DiagnosticSeverity.HINT:
                    summary.total_hints += 1

                if diag.source:
                    summary.by_source[diag.source] = summary.by_source.get(diag.source, 0) + 1

        return summary

    async def request_diagnostics(
        self,
        file_path: str,
        content: str = None,
    ) -> List[Diagnostic]:
        """Request diagnostics from LSP."""
        request = {
            "textDocument": {"uri": self._to_uri(file_path)},
        }

        if content:
            request["textDocument"]["text"] = content

        response = await self._client.send_request("textDocument/diagnostic", request)

        diagnostics = []
        for diag_data in response or []:
            diag = self._parse_diagnostic(file_path, diag_data)
            diagnostics.append(diag)

        self._diagnostics[file_path] = diagnostics
        self._notify_callbacks(file_path, diagnostics)

        return diagnostics

    def _parse_diagnostic(
        self,
        file_path: str,
        data: Dict[str, Any],
    ) -> Diagnostic:
        """Parse diagnostic from LSP."""
        severity_value = data.get("severity", 1)
        severity = DiagnosticSeverity(severity_value) if 1 <= severity_value <= 4 else DiagnosticSeverity.ERROR

        tags = []
        for tag_value in data.get("tags", []):
            if tag_value in [1, 2]:
                tags.append(DiagnosticTag(tag_value))

        related_info = []
        for info in data.get("relatedInformation", []):
            related_info.append(DiagnosticRelatedInfo(
                location=info.get("location", {}),
                message=info.get("message", ""),
            ))

        return Diagnostic(
            file_path=file_path,
            range=data.get("range", {}),
            severity=severity,
            code=data.get("code"),
            source=data.get("source"),
            message=data.get("message", ""),
            related_info=related_info,
            tags=tags,
            data=data.get("data", {}),
        )

    def _to_uri(self, path: str) -> str:
        """Convert path to URI."""
        import os
        abs_path = os.path.abspath(path)
        return f"file://{abs_path}"

    def handle_publish(self, params: Dict[str, Any]) -> None:
        """Handle publishDiagnostics notification."""
        uri = params.get("uri", "")
        file_path = self._from_uri(uri)

        diagnostics = []
        for diag_data in params.get("diagnostics", []):
            diag = self._parse_diagnostic(file_path, diag_data)
            diagnostics.append(diag)

        self._diagnostics[file_path] = diagnostics
        self._notify_callbacks(file_path, diagnostics)

    def _from_uri(self, uri: str) -> str:
        """Convert URI to path."""
        if uri.startswith("file://"):
            return uri[7:]
        return uri

    def on_update(self, callback: Callable) -> None:
        """Register callback for diagnostic updates."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, file_path: str, diagnostics: List[Diagnostic]) -> None:
        """Notify callbacks."""
        for callback in self._callbacks:
            try:
                callback(file_path, diagnostics)
            except Exception:
                pass

    def clear_file(self, file_path: str) -> None:
        """Clear diagnostics for file."""
        self._diagnostics[file_path] = []
        self._notify_callbacks(file_path, [])

    def clear_all(self) -> None:
        """Clear all diagnostics."""
        self._diagnostics.clear()


class QuickFixProvider:
    """Provide quick fixes for diagnostics."""

    def __init__(self, diagnostic_manager: DiagnosticManager):
        self._manager = diagnostic_manager
        self._fixes: Dict[str, List[Dict[str, Any]]] = {}

    async def get_fixes(
        self,
        file_path: str,
        diagnostic: Diagnostic,
    ) -> List[Dict[str, Any]]:
        """Get quick fixes for diagnostic."""
        # Check cached fixes
        key = f"{file_path}:{diagnostic.code}"
        if key in self._fixes:
            return self._fixes[key]

        # Request from LSP
        request = {
            "textDocument": {"uri": self._manager._to_uri(file_path)},
            "range": diagnostic.range,
            "context": {
                "diagnostics": [{"code": diagnostic.code}],
            },
        }

        response = await self._manager._client.send_request("textDocument/codeAction", request)

        fixes = []
        for action in response or []:
            if action.get("kind") == "quickfix":
                fixes.append(action)

        self._fixes[key] = fixes
        return fixes

    def clear_cache(self) -> None:
        """Clear fix cache."""
        self._fixes.clear()


__all__ = [
    "DiagnosticSeverity",
    "DiagnosticTag",
    "DiagnosticRelatedInfo",
    "Diagnostic",
    "DiagnosticSummary",
    "DiagnosticManager",
    "QuickFixProvider",
]