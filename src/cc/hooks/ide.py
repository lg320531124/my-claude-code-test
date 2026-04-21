"""Hook IDE - Async IDE integration."""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum


class IDEType(Enum):
    """IDE types."""
    VSCODE = "vscode"
    JETBRAINS = "jetbrains"
    VIM = "vim"
    EMACS = "emacs"
    NEOVIM = "neovim"
    UNKNOWN = "unknown"


@dataclass
class IDEState:
    """IDE state."""
    ide_type: IDEType
    active_file: Optional[Path] = None
    active_line: int = 0
    active_column: int = 0
    selection: Optional[str] = None
    open_files: List[Path] = field(default_factory=list)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    workspace: Optional[Path] = None


@dataclass
class IDECommand:
    """IDE command."""
    command: str
    args: Dict[str, Any] = field(default_factory=dict)


class IDEIntegration:
    """Async IDE integration."""

    def __init__(self):
        self._state = IDEState(ide_type=IDEType.UNKNOWN)
        self._socket: Optional[asyncio.StreamWriter] = None
        self._callbacks: Dict[str, List[Callable]] = {}
        self._command_queue: asyncio.Queue = asyncio.Queue()
        self._running: bool = False

    async def connect(self, ide_type: IDEType, socket_path: str = None) -> bool:
        """Connect to IDE."""
        self._state.ide_type = ide_type

        if socket_path:
            try:
                reader, writer = await asyncio.open_unix_connection(socket_path)
                self._socket = writer
                self._running = True
                asyncio.create_task(self._listen_loop(reader))
                return True
            except Exception:
                return False

        return True

    async def disconnect(self) -> None:
        """Disconnect from IDE."""
        self._running = False

        if self._socket:
            self._socket.close()
            await self._socket.wait_closed()
            self._socket = None

    async def _listen_loop(self, reader: asyncio.StreamReader) -> None:
        """Listen for IDE messages."""
        while self._running:
            try:
                data = await reader.readline()
                if not data:
                    break

                message = json.loads(data.decode())
                await self._handle_message(message)

            except Exception:
                break

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle message from IDE."""
        event_type = message.get("type", "")

        if event_type == "file_opened":
            self._state.active_file = Path(message.get("path", ""))
            self._state.open_files.append(self._state.active_file)

        elif event_type == "file_closed":
            path = Path(message.get("path", ""))
            self._state.open_files = [f for f in self._state.open_files if f != path]

        elif event_type == "cursor_moved":
            self._state.active_line = message.get("line", 0)
            self._state.active_column = message.get("column", 0)

        elif event_type == "selection_changed":
            self._state.selection = message.get("text")

        elif event_type == "diagnostics":
            self._state.diagnostics = message.get("diagnostics", [])

        # Notify callbacks
        await self._notify_callbacks(event_type, message)

    async def send_command(self, command: IDECommand) -> None:
        """Send command to IDE."""
        if self._socket:
            data = json.dumps({
                "command": command.command,
                "args": command.args,
            })
            self._socket.write(data.encode() + b"\n")
            await self._socket.drain()

        await self._command_queue.put(command)

    async def open_file(self, path: Path, line: int = 0) -> None:
        """Open file in IDE."""
        await self.send_command(IDECommand(
            command="open_file",
            args={"path": str(path), "line": line},
        ))

    async def goto_definition(self, path: Path, line: int, column: int) -> None:
        """Go to definition."""
        await self.send_command(IDECommand(
            command="goto_definition",
            args={"path": str(path), "line": line, "column": column},
        ))

    async def insert_text(self, path: Path, line: int, column: int, text: str) -> None:
        """Insert text at position."""
        await self.send_command(IDECommand(
            command="insert_text",
            args={"path": str(path), "line": line, "column": column, "text": text},
        ))

    async def show_message(self, message: str, type: str = "info") -> None:
        """Show message in IDE."""
        await self.send_command(IDECommand(
            command="show_message",
            args={"message": message, "type": type},
        ))

    async def set_selection(self, path: Path, start_line: int, start_col: int, end_line: int, end_col: int) -> None:
        """Set selection in IDE."""
        await self.send_command(IDECommand(
            command="set_selection",
            args={
                "path": str(path),
                "start_line": start_line,
                "start_col": start_col,
                "end_line": end_line,
                "end_col": end_col,
            },
        ))

    def get_state(self) -> IDEState:
        """Get current IDE state."""
        return self._state

    def on_event(self, event_type: str, callback: Callable) -> None:
        """Register event callback."""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    async def _notify_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """Notify callbacks."""
        callbacks = self._callbacks.get(event_type, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception:
                pass


class IDEHooks:
    """Hooks for IDE integration."""

    def __init__(self, integration: IDEIntegration):
        self._integration = integration

    async def pre_edit(self, path: Path, content: str) -> Dict[str, Any]:
        """Hook before edit."""
        state = self._integration.get_state()

        # Check if file is open in IDE
        if path in state.open_files:
            # Notify IDE about pending edit
            await self._integration.show_message(f"Editing: {path.name}")

        return {"path": path, "content": content}

    async def post_edit(self, path: Path, content: str) -> None:
        """Hook after edit."""
        # Refresh IDE diagnostics
        await self._integration.send_command(IDECommand(
            command="refresh_diagnostics",
            args={"path": str(path)},
        ))

    async def pre_goto(self, symbol: str) -> Optional[Path]:
        """Hook before goto."""
        state = self._integration.get_state()

        if state.active_file:
            # Use IDE's current file context
            return state.active_file

        return None

    async def on_diagnostic(self, diagnostic: Dict[str, Any]) -> None:
        """Hook on diagnostic."""
        # Handle new diagnostic from IDE
        path = Path(diagnostic.get("path", ""))
        line = diagnostic.get("line", 0)
        message = diagnostic.get("message", "")

        # Could trigger automated fixes
        pass


# Global integration
_integration: Optional[IDEIntegration] = None


def get_ide_integration() -> IDEIntegration:
    """Get global IDE integration."""
    global _integration
    if _integration is None:
        _integration = IDEIntegration()
    return _integration


__all__ = [
    "IDEType",
    "IDEState",
    "IDECommand",
    "IDEIntegration",
    "IDEHooks",
    "get_ide_integration",
]