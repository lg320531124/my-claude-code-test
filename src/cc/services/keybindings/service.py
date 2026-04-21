"""Keybinding Manager - Manage keyboard bindings."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ...utils.log import get_logger

logger = get_logger(__name__)


class KeybindingMode(Enum):
    """Keybinding modes."""
    NORMAL = "normal"
    VIM = "vim"
    EMACS = "emacs"
    CUSTOM = "custom"


class KeybindingAction(Enum):
    """Keybinding actions."""
    COMMAND = "command"
    INSERT = "insert"
    DELETE = "delete"
    MOVE = "move"
    SELECT = "select"
    COPY = "copy"
    PASTE = "paste"
    SEARCH = "search"
    UNDO = "undo"
    REDO = "redo"
    SAVE = "save"
    QUIT = "quit"
    HELP = "help"
    CUSTOM = "custom"


@dataclass
class Keybinding:
    """Keybinding definition."""
    key: str
    action: KeybindingAction
    command: Optional[str] = None
    description: str = ""
    mode: KeybindingMode = KeybindingMode.NORMAL
    enabled: bool = True


@dataclass
class KeybindingConfig:
    """Keybinding configuration."""
    mode: KeybindingMode = KeybindingMode.NORMAL
    allow_custom: bool = True
    max_bindings: int = 100
    strict_mode: bool = False


class KeybindingManager:
    """Manage keyboard bindings."""

    # Default bindings
    DEFAULT_BINDINGS: List[Keybinding] = [
        # Normal mode
        Keybinding("ctrl+c", KeybindingAction.QUIT, description="Quit"),
        Keybinding("ctrl+d", KeybindingAction.DELETE, description="Delete"),
        Keybinding("ctrl+u", KeybindingAction.DELETE, description="Delete to start"),
        Keybinding("ctrl+k", KeybindingAction.DELETE, description="Delete to end"),
        Keybinding("ctrl+a", KeybindingAction.MOVE, command="start", description="Move to start"),
        Keybinding("ctrl+e", KeybindingAction.MOVE, command="end", description="Move to end"),
        Keybinding("ctrl+p", KeybindingAction.MOVE, command="up", description="Move up"),
        Keybinding("ctrl+n", KeybindingAction.MOVE, command="down", description="Move down"),
        Keybinding("ctrl+b", KeybindingAction.MOVE, command="left", description="Move left"),
        Keybinding("ctrl+f", KeybindingAction.MOVE, command="right", description="Move right"),
        Keybinding("ctrl+l", KeybindingAction.COMMAND, command="clear", description="Clear"),
        Keybinding("ctrl+r", KeybindingAction.SEARCH, description="Search"),
        Keybinding("ctrl+z", KeybindingAction.UNDO, description="Undo"),
        Keybinding("ctrl+y", KeybindingAction.REDO, description="Redo"),
        Keybinding("ctrl+s", KeybindingAction.SAVE, description="Save"),
        Keybinding("ctrl+h", KeybindingAction.HELP, description="Help"),
        # Vim mode
        Keybinding("h", KeybindingAction.MOVE, command="left", mode=KeybindingMode.VIM),
        Keybinding("j", KeybindingAction.MOVE, command="down", mode=KeybindingMode.VIM),
        Keybinding("k", KeybindingAction.MOVE, command="up", mode=KeybindingMode.VIM),
        Keybinding("l", KeybindingAction.MOVE, command="right", mode=KeybindingMode.VIM),
        Keybinding("i", KeybindingAction.INSERT, mode=KeybindingMode.VIM),
        Keybinding("x", KeybindingAction.DELETE, mode=KeybindingMode.VIM),
        Keybinding("dd", KeybindingAction.DELETE, command="line", mode=KeybindingMode.VIM),
        Keybinding("yy", KeybindingAction.COPY, command="line", mode=KeybindingMode.VIM),
        Keybinding("p", KeybindingAction.PASTE, mode=KeybindingMode.VIM),
        Keybinding("u", KeybindingAction.UNDO, mode=KeybindingMode.VIM),
        Keybinding("/", KeybindingAction.SEARCH, mode=KeybindingMode.VIM),
        Keybinding(":q", KeybindingAction.QUIT, mode=KeybindingMode.VIM),
        Keybinding(":w", KeybindingAction.SAVE, mode=KeybindingMode.VIM),
    ]

    def __init__(self, config: Optional[KeybindingConfig] = None):
        self.config = config or KeybindingConfig()
        self._bindings: Dict[str, Keybinding] = {}
        self._custom_bindings: Dict[str, Keybinding] = {}
        self._callbacks: Dict[KeybindingAction, List[callable]] = {}

        # Load defaults
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default bindings."""
        for binding in self.DEFAULT_BINDINGS:
            if binding.mode == self.config.mode:
                self._bindings[binding.key] = binding

    async def get_binding(
        self,
        key: str
    ) -> Optional[Keybinding]:
        """Get binding for key."""
        # Check custom first
        if key in self._custom_bindings:
            return self._custom_bindings[key]

        return self._bindings.get(key)

    async def register_binding(
        self,
        binding: Keybinding
    ) -> bool:
        """Register keybinding."""
        if not self.config.allow_custom and binding.mode == KeybindingMode.CUSTOM:
            return False

        if binding.mode == KeybindingMode.CUSTOM:
            if len(self._custom_bindings) >= self.config.max_bindings:
                return False
            self._custom_bindings[binding.key] = binding
        else:
            self._bindings[binding.key] = binding

        logger.info(f"Registered binding: {binding.key} -> {binding.action.value}")
        return True

    async def unregister_binding(
        self,
        key: str
    ) -> bool:
        """Unregister keybinding."""
        if key in self._custom_bindings:
            del self._custom_bindings[key]
            return True

        if key in self._bindings:
            del self._bindings[key]
            return True

        return False

    async def handle_key(
        self,
        key: str
    ) -> Optional[KeybindingAction]:
        """Handle key press."""
        binding = await self.get_binding(key)

        if not binding or not binding.enabled:
            return None

        # Call callbacks
        await self._call_callbacks(binding)

        return binding.action

    async def _call_callbacks(
        self,
        binding: Keybinding
    ) -> None:
        """Call registered callbacks."""
        callbacks = self._callbacks.get(binding.action, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(binding)
                else:
                    callback(binding)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def get_all_bindings(self) -> Dict[str, Keybinding]:
        """Get all bindings."""
        result = {}
        result.update(self._bindings)
        result.update(self._custom_bindings)
        return result

    async def get_bindings_by_mode(
        self,
        mode: KeybindingMode
    ) -> Dict[str, Keybinding]:
        """Get bindings by mode."""
        return {
            key: binding
            for key, binding in self._bindings.items()
            if binding.mode == mode
        }

    async def set_mode(
        self,
        mode: KeybindingMode
    ) -> None:
        """Set keybinding mode."""
        self.config.mode = mode
        self._bindings.clear()
        self._load_defaults()
        logger.info(f"Mode set to {mode.value}")

    async def enable_binding(
        self,
        key: str
    ) -> bool:
        """Enable binding."""
        binding = await self.get_binding(key)
        if binding:
            binding.enabled = True
            return True
        return False

    async def disable_binding(
        self,
        key: str
    ) -> bool:
        """Disable binding."""
        binding = await self.get_binding(key)
        if binding:
            binding.enabled = False
            return True
        return False

    def register_callback(
        self,
        action: KeybindingAction,
        callback: callable
    ) -> None:
        """Register action callback."""
        if action not in self._callbacks:
            self._callbacks[action] = []

        self._callbacks[action].append(callback)

    async def export_bindings(self) -> Dict[str, Any]:
        """Export bindings."""
        return {
            "mode": self.config.mode.value,
            "bindings": [
                {
                    "key": b.key,
                    "action": b.action.value,
                    "command": b.command,
                    "description": b.description,
                }
                for b in self._bindings.values()
            ],
            "custom_bindings": [
                {
                    "key": b.key,
                    "action": b.action.value,
                    "command": b.command,
                }
                for b in self._custom_bindings.values()
            ],
        }

    async def import_bindings(
        self,
        data: Dict[str, Any]
    ) -> int:
        """Import bindings."""
        count = 0

        if "mode" in data:
            await self.set_mode(KeybindingMode(data["mode"]))

        if "bindings" in data:
            for b in data["bindings"]:
                binding = Keybinding(
                    key=b["key"],
                    action=KeybindingAction(b["action"]),
                    command=b.get("command"),
                    description=b.get("description", ""),
                )
                if await self.register_binding(binding):
                    count += 1

        return count

    async def clear_custom(self) -> int:
        """Clear custom bindings."""
        count = len(self._custom_bindings)
        self._custom_bindings.clear()
        return count


__all__ = [
    "KeybindingMode",
    "KeybindingAction",
    "Keybinding",
    "KeybindingConfig",
    "KeybindingManager",
]