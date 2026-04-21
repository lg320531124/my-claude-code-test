"""LSP Service - Async Language Server Protocol client.

Async LSP client for code intelligence.
"""

from __future__ import annotations
from .client import (
    LSPClient,
    LSPServerConfig,
    LSPDiagnostic,
    LSPCompletion,
    LSPHover,
    LSPManager,
)
from .completion import (
    CompletionTriggerKind,
    CompletionItemKind,
    CompletionItem,
    CompletionProvider,
    SnippetManager,
)
from .diagnostics import (
    DiagnosticSeverity,
    Diagnostic,
    DiagnosticManager,
    QuickFixProvider,
)
from .hover import (
    HoverKind,
    HoverResult,
    HoverProvider,
    SignatureHelpProvider,
    DefinitionProvider,
)

__all__ = [
    # Client
    "LSPClient",
    "LSPServerConfig",
    "LSPDiagnostic",
    "LSPCompletion",
    "LSPHover",
    "LSPManager",
    # Completion
    "CompletionTriggerKind",
    "CompletionItemKind",
    "CompletionItem",
    "CompletionProvider",
    "SnippetManager",
    # Diagnostics
    "DiagnosticSeverity",
    "Diagnostic",
    "DiagnosticManager",
    "QuickFixProvider",
    # Hover
    "HoverKind",
    "HoverResult",
    "HoverProvider",
    "SignatureHelpProvider",
    "DefinitionProvider",
]