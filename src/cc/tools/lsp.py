"""Enhanced LSPTool with asyncio and actual LSP client."""

from __future__ import annotations
import asyncio
import json
import subprocess
from pathlib import Path
from typing import ClassVar, Any, Callable, Optional

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class LSPInput(ToolInput):
    """Input for LSPTool."""

    action: str  # "definition", "references", "hover", "completion", "symbols"
    file_path: str
    line: Optional[int] = None
    character: Optional[int] = None
    query: Optional[str] = None  # For completion/symbols


class LSPClient:
    """Simple LSP client using asyncio."""

    def __init__(self, server_cmd: str, server_args: List[str] = []):
        self.server_cmd = server_cmd
        self.server_args = server_args
        self.process: asyncio.subprocess.Process | None = None
        self.initialized = False
        self._request_id = 0

    async def start(self) -> bool:
        """Start LSP server."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.server_cmd,
                *self.server_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Initialize
            await self._send_request("initialize", {
                "processId": None,
                "rootUri": None,
                "capabilities": {
                    "textDocument": {
                        "definition": {"dynamicRegistration": False},
                        "references": {"dynamicRegistration": False},
                        "hover": {"dynamicRegistration": False},
                        "completion": {"dynamicRegistration": False},
                        "documentSymbol": {"dynamicRegistration": False},
                    },
                },
            })

            self.initialized = True
            return True

        except Exception:
            return False

    async def stop(self) -> None:
        """Stop LSP server."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
            self.process = None
        self.initialized = False

    async def _send_request(self, method: str, params: dict) -> dict | None:
        """Send LSP request."""
        if not self.process or not self.process.stdin:
            return None

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        # Write with Content-Length header
        content = json.dumps(request)
        header = f"Content-Length: {len(content)}\r\n\r\n"

        try:
            self.process.stdin.write(header.encode())
            self.process.stdin.write(content.encode())
            await self.process.stdin.drain()

            # Read response
            return await self._read_response()

        except Exception:
            return None

    async def _read_response(self) -> dict | None:
        """Read LSP response."""
        if not self.process or not self.process.stdout:
            return None

        try:
            # Read Content-Length header
            header_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=10.0,
            )

            if not header_line.startswith("Content-Length:"):
                return None

            length = int(header_line.split(":")[1].strip())

            # Skip empty line
            await self.process.stdout.readline()

            # Read content
            content = await asyncio.wait_for(
                self.process.stdout.readexactly(length),
                timeout=10.0,
            )

            return json.loads(content.decode())

        except Exception:
            return None

    async def goto_definition(self, file_path: str, line: int, char: int) -> List[dict]:
        """Get definition location."""
        result = await self._send_request("textDocument/definition", {
            "textDocument": {"uri": f"file://{file_path}"},
            "position": {"line": line - 1, "character": char - 1},
        })

        if result and "result" in result:
            locations = result["result"]
            if isinstance(locations, list):
                return locations
            elif locations:
                return [locations]
        return []

    async def find_references(self, file_path: str, line: int, char: int) -> List[dict]:
        """Find all references."""
        result = await self._send_request("textDocument/references", {
            "textDocument": {"uri": f"file://{file_path}"},
            "position": {"line": line - 1, "character": char - 1},
            "context": {"includeDeclaration": True},
        })

        if result and "result" in result:
            return result["result"] or []
        return []

    async def hover(self, file_path: str, line: int, char: int) -> dict | None:
        """Get hover information."""
        result = await self._send_request("textDocument/hover", {
            "textDocument": {"uri": f"file://{file_path}"},
            "position": {"line": line - 1, "character": char - 1},
        })

        if result and "result" in result:
            return result["result"]
        return None

    async def completion(self, file_path: str, line: int, char: int, query: str = "") -> List[dict]:
        """Get completions."""
        result = await self._send_request("textDocument/completion", {
            "textDocument": {"uri": f"file://{file_path}"},
            "position": {"line": line - 1, "character": char - 1},
            "context": {"triggerKind": 1},
        })

        if result and "result" in result:
            items = result["result"]
            if isinstance(items, dict):
                items = items.get("items", [])
            return items or []
        return []

    async def document_symbols(self, file_path: str) -> List[dict]:
        """Get document symbols."""
        result = await self._send_request("textDocument/documentSymbol", {
            "textDocument": {"uri": f"file://{file_path}"},
        })

        if result and "result" in result:
            return result["result"] or []
        return []


class LSPManager:
    """Manages multiple LSP clients."""

    LANGUAGE_SERVERS: ClassVar[dict] = {
        "python": ["pylsp", "pyright", "pyright-langserver"],
        "javascript": ["typescript-language-server", "vls"],
        "typescript": ["typescript-language-server"],
        "go": ["gopls"],
        "rust": ["rust-analyzer"],
    }

    def __init__(self):
        self.clients: Dict[str, LSPClient] = {}

    async def get_client(self, language: str) -> LSPClient | None:
        """Get or create LSP client."""
        if language in self.clients:
            return self.clients[language]

        # Find server
        server_cmd = self._find_server(language)
        if not server_cmd:
            return None

        # Create and start client
        client = LSPClient(server_cmd)
        if await client.start():
            self.clients[language] = client
            return client

        return None

    def _find_server(self, language: str) -> Optional[str]:
        """Find installed language server."""
        servers = self.LANGUAGE_SERVERS.get(language, [])
        for server in servers:
            try:
                subprocess.run([server, "--version"], capture_output=True, check=True)
                return server
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        return None

    async def close_all(self) -> None:
        """Close all clients."""
        for client in self.clients.values():
            await client.stop()
        self.clients.clear()


class LSPTool(ToolDef):
    """Language Server Protocol integration."""

    name: ClassVar[str] = "LSP"
    description: ClassVar[str] = """Get code intelligence via LSP.

Actions:
- definition: Go to definition
- references: Find all references
- hover: Get type/signature info
- completion: Get completions
- symbols: List document symbols"""
    input_schema: ClassVar[type] = LSPInput

    _manager: ClassVar[LSPManager | None] = None

    def get_manager(self) -> LSPManager:
        """Get LSP manager."""
        if LSPTool._manager is None:
            LSPTool._manager = LSPManager()
        return LSPTool._manager

    async def execute(self, input: LSPInput, ctx: ToolUseContext) -> ToolResult:
        """Execute LSP request."""
        path = Path(input.file_path)
        if not path.is_absolute():
            path = Path(ctx.cwd) / path

        if not path.exists():
            return ToolResult(content=f"File not found: {path}", is_error=True)

        # Detect language
        language = self._detect_language(path)
        if not language:
            return ToolResult(content=f"Unknown language: {path.suffix}", is_error=True)

        # Get client
        manager = self.get_manager()
        client = await manager.get_client(language)

        if not client:
            return ToolResult(
                content=f"No LSP server for {language}. Install: {self._get_install_hint(language)}",
                is_error=True,
            )

        # Execute action
        try:
            if input.action == "definition":
                locations = await client.goto_definition(
                    str(path), input.line or 1, input.character or 1,
                )
                return self._format_locations(locations)

            elif input.action == "references":
                refs = await client.find_references(
                    str(path), input.line or 1, input.character or 1,
                )
                return self._format_locations(refs)

            elif input.action == "hover":
                info = await client.hover(
                    str(path), input.line or 1, input.character or 1,
                )
                return self._format_hover(info)

            elif input.action == "completion":
                items = await client.completion(
                    str(path), input.line or 1, input.character or 1,
                    input.query or "",
                )
                return self._format_completions(items)

            elif input.action == "symbols":
                symbols = await client.document_symbols(str(path))
                return self._format_symbols(symbols)

            else:
                return ToolResult(content=f"Unknown action: {input.action}", is_error=True)

        except Exception as e:
            return ToolResult(content=f"LSP error: {e}", is_error=True)

    def _detect_language(self, path: Path) -> Optional[str]:
        """Detect language from file."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
        }
        return ext_map.get(path.suffix)

    def _get_install_hint(self, lang: str) -> str:
        """Get installation hint."""
        hints = {
            "python": "pip install python-lsp-server",
            "javascript": "npm install -g typescript-language-server",
            "typescript": "npm install -g typescript-language-server",
            "go": "go install golang.org/x/tools/gopls@latest",
            "rust": "rustup component add rust-analyzer",
        }
        return hints.get(lang, f"Install LSP server for {lang}")

    def _format_locations(self, locations: List[dict]) -> ToolResult:
        """Format location results."""
        if not locations:
            return ToolResult(content="No locations found")

        lines = []
        for loc in locations:
            uri = loc.get("uri", "")
            range = loc.get("range", {})
            start = range.get("start", {})
            line = start.get("line", 0) + 1
            char = start.get("character", 0) + 1
            lines.append(f"{uri}:{line}:{char}")

        return ToolResult(content="\n".join(lines))

    def _format_hover(self, info: Optional[dict]) -> ToolResult:
        """Format hover info."""
        if not info:
            return ToolResult(content="No hover info")

        content = info.get("contents", "")
        if isinstance(content, dict):
            content = content.get("value", "")
        elif isinstance(content, list):
            content = "\n".join(c.get("value", str(c)) for c in content)

        return ToolResult(content=str(content))

    def _format_completions(self, items: List[dict]) -> ToolResult:
        """Format completions."""
        if not items:
            return ToolResult(content="No completions")

        lines = []
        for item in items[:50]:  # Limit
            label = item.get("label", "")
            kind = item.get("kind", 0)
            detail = item.get("detail", "")
            lines.append(f"{label} - {detail}")

        return ToolResult(content="\n".join(lines))

    def _format_symbols(self, symbols: List[dict]) -> ToolResult:
        """Format document symbols."""
        if not symbols:
            return ToolResult(content="No symbols found")

        lines = []
        for sym in symbols:
            name = sym.get("name", "")
            kind = sym.get("kind", 0)
            range = sym.get("range", {})
            start = range.get("start", {})
            line = start.get("line", 0) + 1
            lines.append(f"{name} (line {line})")

        return ToolResult(content="\n".join(lines))


# Global LSP manager
_lsp_manager: Optional[LSPManager] = None


def get_lsp_manager() -> LSPManager:
    """Get global LSP manager."""
    global _lsp_manager
    if _lsp_manager is None:
        _lsp_manager = LSPManager()
    return _lsp_manager


async def close_lsp() -> None:
    """Close all LSP clients."""
    if _lsp_manager:
        await _lsp_manager.close_all()
