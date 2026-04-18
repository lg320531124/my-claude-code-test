"""LSPTool - Language Server Protocol integration."""

import subprocess
from pathlib import Path
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class LSPInput(ToolInput):
    """Input for LSPTool."""

    action: str  # "goto_definition", "find_references", "hover", "completion"
    file_path: str
    line: int
    character: int


class LSPTool(ToolDef):
    """Language Server Protocol integration."""

    name: ClassVar[str] = "LSP"
    description: ClassVar[str] = "Get code intelligence via LSP (definitions, references, hover)"
    input_schema: ClassVar[type[ToolInput]] = LSPInput

    # Supported language servers
    LANGUAGE_SERVERS = {
        "python": ["pylsp", "pyright"],
        "javascript": ["typescript-language-server"],
        "typescript": ["typescript-language-server"],
        "go": ["gopls"],
        "rust": ["rust-analyzer"],
    }

    async def execute(self, input: LSPInput, ctx: ToolUseContext) -> ToolResult:
        """Execute LSP request."""
        path = Path(input.file_path)
        if not path.is_absolute():
            path = Path(ctx.cwd) / path

        if not path.exists():
            return ToolResult(
                content=f"File not found: {path}",
                is_error=True,
            )

        # Detect language
        lang = self._detect_language(path)
        if not lang:
            return ToolResult(
                content=f"Could not detect language for {path}",
                is_error=True,
            )

        # Find language server
        server = self._find_language_server(lang)
        if not server:
            return ToolResult(
                content=f"No language server installed for {lang}. Install: {self._get_install_hint(lang)}",
                is_error=True,
            )

        # Simplified: return placeholder (full LSP would require actual server communication)
        # This is a placeholder that would use the LSP client in a full implementation
        return ToolResult(
            content=self._get_placeholder_response(input.action, path, input.line, input.character),
            metadata={"language": lang, "server": server},
        )

    def _detect_language(self, path: Path) -> str | None:
        """Detect language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
        }
        return ext_map.get(path.suffix)

    def _find_language_server(self, lang: str) -> str | None:
        """Find installed language server."""
        servers = self.LANGUAGE_SERVERS.get(lang, [])
        for server in servers:
            try:
                subprocess.run([server, "--version"], capture_output=True, check=True)
                return server
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        return None

    def _get_install_hint(self, lang: str) -> str:
        """Get installation hint."""
        hints = {
            "python": "pip install python-lsp-server or pip install pyright",
            "javascript": "npm install -g typescript-language-server",
            "typescript": "npm install -g typescript-language-server",
            "go": "go install golang.org/x/tools/gopls@latest",
            "rust": "rustup component add rust-analyzer",
        }
        return hints.get(lang, f"Install language server for {lang}")

    def _get_placeholder_response(self, action: str, path: Path, line: int, char: int) -> str:
        """Get placeholder response."""
        return f"LSP {action} request at {path}:{line}:{char}\n\n(Full LSP integration would require server communication. This placeholder indicates the request would be sent.)"