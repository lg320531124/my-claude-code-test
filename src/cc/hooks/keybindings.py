"""Keybindings Hook - Async keyboard handling."""

from __future__ import annotations
import asyncio
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from ..services.hooks import Hook, HookType, HookContext, HookResult, get_hook_manager


class KeyMode(Enum):
    """Keyboard input modes."""
    NORMAL = "normal"
    INSERT = "insert"
    COMMAND = "command"
    VISUAL = "visual"


@dataclass
class KeyBinding:
    """Key binding definition."""
    key: str
    handler: Callable
    mode: KeyMode = KeyMode.NORMAL
    description: str = ""
    repeatable: bool = False


class KeybindingsHook:
    """Hook for keyboard bindings."""

    def __init__(self):
        self._bindings: Dict[str, KeyBinding] = {}
        self._mode: KeyMode = KeyMode.NORMAL
        self._manager = get_hook_manager()
        self._key_buffer: str = ""
        self._last_key_time: float = 0

    def bind(self, key: str, handler: Callable, mode: KeyMode = KeyMode.NORMAL, description: str = "") -> None:
        """Register key binding."""
        binding = KeyBinding(
            key=key,
            handler=handler,
            mode=mode,
            description=description,
        )
        self._bindings[key] = binding

    def unbind(self, key: str) -> None:
        """Remove key binding."""
        self._bindings.pop(key, None)

    def set_mode(self, mode: KeyMode) -> None:
        """Set keyboard mode."""
        self._mode = mode

    def get_mode(self) -> KeyMode:
        """Get current mode."""
        return self._mode

    async def handle_key(self, key: str, context: Dict = None) -> Optional[Any]:
        """Handle key press."""
        # Check for multi-key sequences
        current_time = asyncio.get_event_loop().time()

        if current_time - self._last_key_time < 0.5:
            self._key_buffer += key
        else:
            self._key_buffer = key

        self._last_key_time = current_time

        # Check bindings
        for bind_key, binding in self._bindings.items():
            if binding.mode == self._mode and bind_key == self._key_buffer:
                self._key_buffer = ""

                if asyncio.iscoroutinefunction(binding.handler):
                    return await binding.handler(context or {})
                else:
                    return binding.handler(context or {})

        # Check partial match
        for bind_key in self._bindings:
            if bind_key.startswith(self._key_buffer) and bind_key != self._key_buffer:
                return None  # Wait for more keys

        # No match
        self._key_buffer = ""

        return None

    def get_bindings(self) -> Dict[str, KeyBinding]:
        """Get all bindings."""
        return self._bindings

    def get_bindings_for_mode(self, mode: KeyMode) -> Dict[str, KeyBinding]:
        """Get bindings for specific mode."""
        return {
            k: v for k, v in self._bindings.items()
            if v.mode == mode
        }


# Default keybindings
DEFAULT_BINDINGS = {
    # Navigation
    "up": {"key": "up", "handler": lambda ctx: ctx.get("scroll_up"), "description": "Scroll up"},
    "down": {"key": "down", "handler": lambda ctx: ctx.get("scroll_down"), "description": "Scroll down"},
    "pageup": {"key": "pageup", "handler": lambda ctx: ctx.get("page_up"), "description": "Page up"},
    "pagedown": {"key": "pagedown", "handler": lambda ctx: ctx.get("page_down"), "description": "Page down"},
    "home": {"key": "home", "handler": lambda ctx: ctx.get("scroll_top"), "description": "Scroll to top"},
    "end": {"key": "end", "handler": lambda ctx: ctx.get("scroll_bottom"), "description": "Scroll to bottom"},

    # Vim-style navigation (when in normal mode)
    "j": {"key": "j", "handler": lambda ctx: ctx.get("scroll_down"), "mode": KeyMode.NORMAL, "description": "Vim down"},
    "k": {"key": "k", "handler": lambda ctx: ctx.get("scroll_up"), "mode": KeyMode.NORMAL, "description": "Vim up"},
    "g": {"key": "g", "handler": lambda ctx: ctx.get("scroll_top"), "mode": KeyMode.NORMAL, "description": "Vim top"},
    "G": {"key": "G", "handler": lambda ctx: ctx.get("scroll_bottom"), "mode": KeyMode.NORMAL, "description": "Vim bottom"},
}


async def use_keybindings(bindings: Dict[str, Callable] = None) -> KeybindingsHook:
    """Hook for keybindings.

    Usage:
        kb = await use_keybindings({
            "ctrl+p": lambda: print("Previous"),
            "ctrl+n": lambda: print("Next"),
        })
    """
    hook = KeybindingsHook()

    # Register provided bindings
    if bindings:
        for key, handler in bindings.items():
            hook.bind(key, handler)

    # Register with hook manager
    async def key_handler(context: HookContext) -> HookResult:
        key = context.data.get("key")
        result = await hook.handle_key(key, context.data)
        return HookResult(success=True, data={"result": result})

    hook._manager.register(
        hook_type=HookType.PRE_TOOL_USE,
        name="keybindings",
        handler=key_handler,
    )

    return hook


def register_default_keybindings() -> KeybindingsHook:
    """Register default keybindings."""
    hook = KeybindingsHook()

    for name, config in DEFAULT_BINDINGS.items():
        handler = config["handler"]
        mode = config.get("mode", KeyMode.NORMAL)
        description = config.get("description", "")

        hook.bind(config["key"], handler, mode, description)

    return hook


__all__ = [
    "KeyMode",
    "KeyBinding",
    "KeybindingsHook",
    "use_keybindings",
    "register_default_keybindings",
    "DEFAULT_BINDINGS",
]