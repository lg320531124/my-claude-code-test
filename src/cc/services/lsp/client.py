"""LSP Client - Async Language Server Protocol client.

Async client for connecting to LSP servers.
"""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from ...utils.async_process import AsyncProcess


@dataclass
class LSPDiagnostic:
    """LSP diagnostic."""
    range: Dict[str, int]  # start, end line/character
    message: str
    severity: int = 1  # 1=error, 2=warning, 3=info, 4=hint
    source: Optional[str] = None
    code: Optional[str] = None


@dataclass
class LSPCompletion:
    """LSP completion item."""
    label: str
    kind: int = 1  # text, method, function, etc.
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insert_text: Optional[str] = None


@dataclass
class LSPHover:
    """LSP hover result."""
    contents: str
    range: Optional[Dict[str, int]] = None


@dataclass
class LSPServerConfig:
    """LSP server configuration."""
    language: str
    command: str
    args: List[str] = field(default_factory=list)
    initialization_options: Dict[str, Any] = field(default_factory=dict)


class LSPClient:
    """Async LSP client implementation."""

    def __init__(self, config: LSPServerConfig, root_path: str):
        self.config = config
        self.root_path = root_path
        self._process: Optional[AsyncProcess] = None
        self._initialized = False
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._capabilities: Dict[str, Any] = {}

    async def connect(self) -> None:
        """Connect to LSP server."""
        # Build command
        full_command = self.config.command
        if self.config.args:
            full_command += " " + " ".join(self.config.args)

        # Create process
        self._process = AsyncProcess(full_command)

        # Start process
        await self._process.run()

        # Initialize LSP protocol
        await self._initialize()

    async def _initialize(self) -> None:
        """Initialize LSP protocol."""
        response = await self._send_request("initialize", {
            "processId": None,
            "rootUri": Path(self.root_path).as_uri(),
            "capabilities": {
                "textDocument": {
                    "completion": {
                        "completionItem": {
                            "snippetSupport": True,
                        },
                    },
                    "hover": {
                        "contentFormat": ["markdown", "plaintext"],
                    },
                    "diagnostics": {},
                },
                "workspace": {
                    "didChangeConfiguration": {},
                },
            },
            "initializationOptions": self.config.initialization_options,
        })

        self._capabilities = response.get("capabilities", {})

        # Send initialized notification
        await self._send_notification("initialized", {})
        self._initialized = True

    async def _send_request(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send LSP request."""
        self._request_id += 1
        request_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # Create future
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        # Send request
        content = json.dumps(request)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        message = header + content

        if self._process and self._process._process:
            self._process._process.stdin.write(message.encode())
            await self._process._process.stdin.drain()

        # Wait for response
        return await asyncio.wait_for(future, timeout=30.0)

    async def _send_notification(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> None:
        """Send LSP notification."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        content = json.dumps(notification)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        message = header + content

        if self._process and self._process._process:
            self._process._process.stdin.write(message.encode())
            await self._process._process.stdin.drain()

    async def open_document(
        self,
        file_path: str,
        language_id: str,
        content: str,
    ) -> None:
        """Open text document."""
        uri = Path(file_path).as_uri()
        await self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": content,
            },
        })

    async def close_document(self, file_path: str) -> None:
        """Close text document."""
        uri = Path(file_path).as_uri()
        await self._send_notification("textDocument/didClose", {
            "textDocument": {"uri": uri},
        })

    async def get_completions(
        self,
        file_path: str,
        line: int,
        character: int,
    ) -> List[LSPCompletion]:
        """Get completions at position."""
        uri = Path(file_path).as_uri()
        response = await self._send_request("textDocument/completion", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })

        items = response.get("items", [])
        return [
            LSPCompletion(
                label=item.get("label", ""),
                kind=item.get("kind", 1),
                detail=item.get("detail"),
                documentation=item.get("documentation"),
                insert_text=item.get("insertText"),
            )
            for item in items
        ]

    async def get_hover(
        self,
        file_path: str,
        line: int,
        character: int,
    ) -> Optional[LSPHover]:
        """Get hover info at position."""
        uri = Path(file_path).as_uri()
        response = await self._send_request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })

        if not response:
            return None

        contents = response.get("contents", "")
        if isinstance(contents, dict):
            contents = contents.get("value", "")

        return LSPHover(
            contents=contents,
            range=response.get("range"),
        )

    async def get_diagnostics(self, file_path: str) -> List[LSPDiagnostic]:
        """Get diagnostics for file."""
        # Diagnostics are usually sent as notifications
        # This method returns cached diagnostics
        uri = Path(file_path).as_uri()
        # Placeholder - would need to track incoming diagnostics
        return []

    async def close(self) -> None:
        """Close connection."""
        if self._process:
            await self._process.kill()
            self._process = None


class LSPManager:
    """Manage multiple LSP clients."""

    def __init__(self):
        self._clients: Dict[str, LSPClient] = {}

    async def start_server(
        self,
        config: LSPServerConfig,
        root_path: str,
    ) -> LSPClient:
        """Start LSP server."""
        client = LSPClient(config, root_path)
        await client.connect()
        self._clients[config.language] = client
        return client

    def get_client(self, language: str) -> Optional[LSPClient]:
        """Get client by language."""
        return self._clients.get(language)

    async def get_completions(
        self,
        file_path: str,
        language: str,
        line: int,
        character: int,
    ) -> List[LSPCompletion]:
        """Get completions."""
        client = self._clients.get(language)
        if client:
            return await client.get_completions(file_path, line, character)
        return []

    async def close_all(self) -> None:
        """Close all connections."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()


__all__ = [
    "LSPClient",
    "LSPServerConfig",
    "LSPDiagnostic",
    "LSPCompletion",
    "LSPHover",
    "LSPManager",
]