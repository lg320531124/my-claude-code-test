"""Keybindings Module - Complete keyboard binding system.

Provides platform-specific keybindings, conflict detection, key sequences,
modes, and integration with vim and TUI systems.
"""

from __future__ import annotations
import asyncio
import platform
from typing import Dict, Callable, Optional, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict


class KeyMode(Enum):
    """Keyboard input modes."""
    NORMAL = "normal"
    INSERT = "insert"
    COMMAND = "command"
    VISUAL = "visual"
    VISUAL_LINE = "visual_line"
    VISUAL_BLOCK = "visual_block"
    REPLACE = "replace"
    PENDING = "pending"


class Platform(Enum):
    """Operating system platforms."""
    MACOS = "darwin"
    WINDOWS = "windows"
    LINUX = "linux"
    OTHER = "other"


@dataclass
class KeyBinding:
    """Key binding definition."""
    key: str
    handler: Callable
    mode: KeyMode = KeyMode.NORMAL
    description: str = ""
    repeatable: bool = False
    platform: Optional[Platform] = None  # None = all platforms
    priority: int = 0  # Higher priority wins in conflicts
    enabled: bool = True
    group: str = ""  # For grouping related bindings


@dataclass
class KeySequence:
    """Key sequence for multi-key bindings."""
    keys: List[str]
    handler: Callable
    mode: KeyMode = KeyMode.NORMAL
    timeout_ms: int = 500  # Time between keys
    description: str = ""


@dataclass
class KeyConflict:
    """Detected key binding conflict."""
    key: str
    bindings: List[KeyBinding]
    mode: KeyMode


class KeybindingsManager:
    """Central keybindings manager."""

    def __init__(self):
        self._bindings: Dict[str, List[KeyBinding]] = defaultdict(list)
        self._sequences: Dict[str, KeySequence] = {}
        self._mode: KeyMode = KeyMode.NORMAL
        self._key_buffer: str = ""
        self._sequence_buffer: List[str] = []
        self._last_key_time: float = 0
        self._platform: Platform = self._detect_platform()
        self._conflicts: List[KeyConflict] = []
        self._groups: Dict[str, List[KeyBinding]] = defaultdict(list)
        self._context: Dict[str, Any] = {}

    def _detect_platform(self) -> Platform:
        """Detect current platform."""
        system = platform.system().lower()
        if system == "darwin":
            return Platform.MACOS
        elif system == "windows":
            return Platform.WINDOWS
        elif system == "linux":
            return Platform.LINUX
        else:
            return Platform.OTHER

    def bind(
        self,
        key: str,
        handler: Callable,
        mode: KeyMode = KeyMode.NORMAL,
        description: str = "",
        repeatable: bool = False,
        platform: Optional[Platform] = None,
        priority: int = 0,
        group: str = "",
    ) -> None:
        """Register a key binding."""
        binding = KeyBinding(
            key=key,
            handler=handler,
            mode=mode,
            description=description,
            repeatable=repeatable,
            platform=platform,
            priority=priority,
            group=group,
        )
        self._bindings[key].append(binding)

        if group:
            self._groups[group].append(binding)

        # Check for conflicts
        self._check_conflicts(key, mode)

    def bind_sequence(
        self,
        keys: List[str],
        handler: Callable,
        mode: KeyMode = KeyMode.NORMAL,
        timeout_ms: int = 500,
        description: str = "",
    ) -> None:
        """Register a key sequence."""
        sequence = KeySequence(
            keys=keys,
            handler=handler,
            mode=mode,
            timeout_ms=timeout_ms,
            description=description,
        )
        key_id = " ".join(keys)
        self._sequences[key_id] = sequence

    def unbind(self, key: str, mode: Optional[KeyMode] = None) -> None:
        """Remove key binding."""
        if mode:
            self._bindings[key] = [
                b for b in self._bindings[key] if b.mode != mode
            ]
        else:
            self._bindings[key] = []

    def unbind_sequence(self, keys: List[str]) -> None:
        """Remove key sequence."""
        key_id = " ".join(keys)
        self._sequences.pop(key_id, None)

    def unbind_group(self, group: str) -> None:
        """Remove all bindings in a group."""
        for binding in self._groups.get(group, []):
            self._bindings[binding.key] = [
                b for b in self._bindings[binding.key]
                if b.group != group
            ]
        self._groups[group] = []

    def set_mode(self, mode: KeyMode) -> None:
        """Set keyboard mode."""
        self._mode = mode
        self._key_buffer = ""
        self._sequence_buffer = []

    def get_mode(self) -> KeyMode:
        """Get current mode."""
        return self._mode

    def set_context(self, context: Dict[str, Any]) -> None:
        """Set execution context."""
        self._context = context

    async def handle_key(self, key: str) -> Optional[Any]:
        """Handle key press."""
        current_time = asyncio.get_event_loop().time()

        # Check for sequence continuation
        if current_time - self._last_key_time < 0.5 and self._sequence_buffer:
            self._sequence_buffer.append(key)
            sequence_id = " ".join(self._sequence_buffer)

            # Check if sequence is complete
            if sequence_id in self._sequences:
                sequence = self._sequences[sequence_id]
                if sequence.mode == self._mode:
                    self._sequence_buffer = []
                    if asyncio.iscoroutinefunction(sequence.handler):
                        return await sequence.handler(self._context)
                    else:
                        return sequence.handler(self._context)

            # Check if sequence could continue
            partial_match = False
            for seq_id in self._sequences:
                if seq_id.startswith(sequence_id) and seq_id != sequence_id:
                    partial_match = True
                    break

            if not partial_match:
                self._sequence_buffer = []

            self._last_key_time = current_time
            return None

        # Start new sequence check
        self._sequence_buffer = [key]
        self._last_key_time = current_time

        # Check single key bindings
        matching_bindings = []

        for binding in self._bindings.get(key, []):
            if not binding.enabled:
                continue
            if binding.mode != self._mode:
                continue
            if binding.platform and binding.platform != self._platform:
                continue
            matching_bindings.append(binding)

        if matching_bindings:
            # Sort by priority
            matching_bindings.sort(key=lambda b: b.priority, reverse=True)

            # Execute highest priority
            binding = matching_bindings[0]

            if asyncio.iscoroutinefunction(binding.handler):
                return await binding.handler(self._context)
            else:
                return binding.handler(self._context)

        # Check for partial sequence match
        for seq_id in self._sequences:
            if seq_id.startswith(key):
                return None  # Wait for more keys

        self._sequence_buffer = []
        return None

    def _check_conflicts(self, key: str, mode: KeyMode) -> None:
        """Check for key binding conflicts."""
        bindings_for_key_mode = [
            b for b in self._bindings[key]
            if b.mode == mode and (b.platform is None or b.platform == self._platform)
        ]

        if len(bindings_for_key_mode) > 1:
            conflict = KeyConflict(
                key=key,
                bindings=bindings_for_key_mode,
                mode=mode,
            )
            self._conflicts.append(conflict)

    def get_conflicts(self) -> List[KeyConflict]:
        """Get all detected conflicts."""
        return self._conflicts

    def resolve_conflict(self, key: str, mode: KeyMode, winner_index: int) -> None:
        """Resolve conflict by selecting winner."""
        bindings = self._bindings[key]

        for i, b in enumerate(bindings):
            if b.mode == mode:
                b.enabled = (i == winner_index)

    def get_bindings(self) -> Dict[str, List[KeyBinding]]:
        """Get all bindings."""
        return dict(self._bindings)

    def get_bindings_for_mode(self, mode: KeyMode) -> Dict[str, List[KeyBinding]]:
        """Get bindings for specific mode."""
        return {
            k: [b for b in v if b.mode == mode]
            for k, v in self._bindings.items()
        }

    def get_bindings_for_group(self, group: str) -> List[KeyBinding]:
        """Get bindings for a group."""
        return self._groups.get(group, [])

    def get_sequences(self) -> Dict[str, KeySequence]:
        """Get all key sequences."""
        return self._sequences

    def get_sequences_for_mode(self, mode: KeyMode) -> Dict[str, KeySequence]:
        """Get sequences for specific mode."""
        return {
            k: v for k, v in self._sequences.items()
            if v.mode == mode
        }

    def list_bindings(self) -> List[Tuple[str, KeyBinding]]:
        """List all bindings as tuples."""
        result = []
        for key, bindings in self._bindings.items():
            for binding in bindings:
                result.append((key, binding))
        return result

    def describe_binding(self, key: str) -> str:
        """Get description of binding."""
        bindings = self._bindings.get(key, [])
        descriptions = []
        for b in bindings:
            if b.description:
                mode_str = b.mode.value
                descriptions.append(f"[{mode_str}] {b.description}")
        return "\n".join(descriptions) if descriptions else key


# Platform-specific key mappings
PLATFORM_KEY_MAPPINGS: Dict[Platform, Dict[str, str]] = {
    Platform.MACOS: {
        "ctrl": "ctrl",
        "alt": "option",
        "shift": "shift",
        "super": "cmd",
        "cmd": "cmd",
        "option": "option",
    },
    Platform.WINDOWS: {
        "ctrl": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "super": "win",
        "win": "win",
    },
    Platform.LINUX: {
        "ctrl": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "super": "super",
    },
}


def normalize_key(key: str, platform: Platform = None) -> str:
    """Normalize key string for platform."""
    if platform is None:
        system = platform.system().lower()
        if system == "darwin":
            platform = Platform.MACOS
        elif system == "windows":
            platform = Platform.WINDOWS
        else:
            platform = Platform.LINUX

    mappings = PLATFORM_KEY_MAPPINGS.get(platform, {})

    # Replace modifiers
    parts = key.split("+")
    normalized_parts = []

    for part in parts:
        lower_part = part.lower()
        if lower_part in mappings:
            normalized_parts.append(mappings[lower_part])
        else:
            normalized_parts.append(part)

    return "+".join(normalized_parts)


# Default keybindings for Claude Code CLI
DEFAULT_CLI_BINDINGS = [
    # Navigation group
    KeyBinding("up", lambda ctx: ctx.get("scroll_up", lambda: None)(), KeyMode.NORMAL, "Scroll up", group="navigation"),
    KeyBinding("down", lambda ctx: ctx.get("scroll_down", lambda: None)(), KeyMode.NORMAL, "Scroll down", group="navigation"),
    KeyBinding("pageup", lambda ctx: ctx.get("page_up", lambda: None)(), KeyMode.NORMAL, "Page up", group="navigation"),
    KeyBinding("pagedown", lambda ctx: ctx.get("page_down", lambda: None)(), KeyMode.NORMAL, "Page down", group="navigation"),
    KeyBinding("home", lambda ctx: ctx.get("scroll_top", lambda: None)(), KeyMode.NORMAL, "Scroll to top", group="navigation"),
    KeyBinding("end", lambda ctx: ctx.get("scroll_bottom", lambda: None)(), KeyMode.NORMAL, "Scroll to bottom", group="navigation"),

    # Vim navigation
    KeyBinding("j", lambda ctx: ctx.get("scroll_down", lambda: None)(), KeyMode.NORMAL, "Vim down", group="vim"),
    KeyBinding("k", lambda ctx: ctx.get("scroll_up", lambda: None)(), KeyMode.NORMAL, "Vim up", group="vim"),
    KeyBinding("h", lambda ctx: ctx.get("scroll_left", lambda: None)(), KeyMode.NORMAL, "Vim left", group="vim"),
    KeyBinding("l", lambda ctx: ctx.get("scroll_right", lambda: None)(), KeyMode.NORMAL, "Vim right", group="vim"),
    KeyBinding("g", lambda ctx: ctx.get("scroll_top", lambda: None)(), KeyMode.NORMAL, "Vim top", group="vim"),
    KeyBinding("G", lambda ctx: ctx.get("scroll_bottom", lambda: None)(), KeyMode.NORMAL, "Vim bottom", group="vim"),

    # Control key actions
    KeyBinding("ctrl+c", lambda ctx: ctx.get("cancel", lambda: None)(), KeyMode.NORMAL, "Cancel operation", group="control", priority=10),
    KeyBinding("ctrl+d", lambda ctx: ctx.get("exit", lambda: None)(), KeyMode.NORMAL, "Exit CLI", group="control", priority=10),
    KeyBinding("ctrl+l", lambda ctx: ctx.get("clear", lambda: None)(), KeyMode.NORMAL, "Clear screen", group="control"),
    KeyBinding("ctrl+r", lambda ctx: ctx.get("redo", lambda: None)(), KeyMode.NORMAL, "Redo", group="control"),
    KeyBinding("ctrl+u", lambda ctx: ctx.get("undo", lambda: None)(), KeyMode.NORMAL, "Undo", group="control"),
    KeyBinding("ctrl+z", lambda ctx: ctx.get("suspend", lambda: None)(), KeyMode.NORMAL, "Suspend", group="control", platform=Platform.LINUX),

    # Mode switching
    KeyBinding("i", lambda ctx: ctx.get("enter_insert", lambda: None)(), KeyMode.NORMAL, "Enter insert mode", group="mode"),
    KeyBinding("v", lambda ctx: ctx.get("enter_visual", lambda: None)(), KeyMode.NORMAL, "Enter visual mode", group="mode"),
    KeyBinding("V", lambda ctx: ctx.get("enter_visual_line", lambda: None)(), KeyMode.NORMAL, "Enter visual line mode", group="mode"),
    KeyBinding(":", lambda ctx: ctx.get("enter_command", lambda: None)(), KeyMode.NORMAL, "Enter command mode", group="mode"),
    KeyBinding("escape", lambda ctx: ctx.get("exit_mode", lambda: None)(), KeyMode.NORMAL, "Exit mode", group="mode", priority=5),

    # Tool actions
    KeyBinding("enter", lambda ctx: ctx.get("execute", lambda: None)(), KeyMode.NORMAL, "Execute", group="action", priority=5),
    KeyBinding("space", lambda ctx: ctx.get("select", lambda: None)(), KeyMode.NORMAL, "Select", group="action"),
    KeyBinding("tab", lambda ctx: ctx.get("next", lambda: None)(), KeyMode.NORMAL, "Next item", group="action"),
    KeyBinding("shift+tab", lambda ctx: ctx.get("prev", lambda: None)(), KeyMode.NORMAL, "Previous item", group="action"),

    # Help
    KeyBinding("?", lambda ctx: ctx.get("show_help", lambda: None)(), KeyMode.NORMAL, "Show help", group="help"),
    KeyBinding("ctrl+?", lambda ctx: ctx.get("show_bindings", lambda: None)(), KeyMode.NORMAL, "Show bindings", group="help"),

    # Mac-specific
    KeyBinding("cmd+c", lambda ctx: ctx.get("copy", lambda: None)(), KeyMode.NORMAL, "Copy", group="clipboard", platform=Platform.MACOS),
    KeyBinding("cmd+v", lambda ctx: ctx.get("paste", lambda: None)(), KeyMode.NORMAL, "Paste", group="clipboard", platform=Platform.MACOS),
    KeyBinding("cmd+x", lambda ctx: ctx.get("cut", lambda: None)(), KeyMode.NORMAL, "Cut", group="clipboard", platform=Platform.MACOS),
    KeyBinding("cmd+z", lambda ctx: ctx.get("undo", lambda: None)(), KeyMode.NORMAL, "Undo", group="clipboard", platform=Platform.MACOS),
    KeyBinding("cmd+shift+z", lambda ctx: ctx.get("redo", lambda: None)(), KeyMode.NORMAL, "Redo", group="clipboard", platform=Platform.MACOS),

    # Windows-specific
    KeyBinding("ctrl+c", lambda ctx: ctx.get("copy", lambda: None)(), KeyMode.NORMAL, "Copy", group="clipboard", platform=Platform.WINDOWS),
    KeyBinding("ctrl+v", lambda ctx: ctx.get("paste", lambda: None)(), KeyMode.NORMAL, "Paste", group="clipboard", platform=Platform.WINDOWS),
    KeyBinding("ctrl+x", lambda ctx: ctx.get("cut", lambda: None)(), KeyMode.NORMAL, "Cut", group="clipboard", platform=Platform.WINDOWS),
    KeyBinding("ctrl+z", lambda ctx: ctx.get("undo", lambda: None)(), KeyMode.NORMAL, "Undo", group="clipboard", platform=Platform.WINDOWS),
    KeyBinding("ctrl+y", lambda ctx: ctx.get("redo", lambda: None)(), KeyMode.NORMAL, "Redo", group="clipboard", platform=Platform.WINDOWS),
]

# Default key sequences
DEFAULT_CLI_SEQUENCES = [
    KeySequence(["g", "g"], lambda ctx: ctx.get("scroll_top", lambda: None)(), KeyMode.NORMAL, 500, "Go to top (gg)"),
    KeySequence(["d", "d"], lambda ctx: ctx.get("delete_line", lambda: None)(), KeyMode.NORMAL, 500, "Delete line (dd)"),
    KeySequence(["y", "y"], lambda ctx: ctx.get("yank_line", lambda: None)(), KeyMode.NORMAL, 500, "Yank line (yy)"),
    KeySequence(["d", "w"], lambda ctx: ctx.get("delete_word", lambda: None)(), KeyMode.NORMAL, 500, "Delete word (dw)"),
    KeySequence(["d", "$"], lambda ctx: ctx.get("delete_to_end", lambda: None)(), KeyMode.NORMAL, 500, "Delete to end (d$)"),
    KeySequence(["c", "w"], lambda ctx: ctx.get("change_word", lambda: None)(), KeyMode.NORMAL, 500, "Change word (cw)"),
    KeySequence(["c", "c"], lambda ctx: ctx.get("change_line", lambda: None)(), KeyMode.NORMAL, 500, "Change line (cc)"),
    KeySequence(["g", "u"], lambda ctx: ctx.get("lowercase", lambda: None)(), KeyMode.NORMAL, 500, "Lowercase (gu)"),
    KeySequence(["g", "U"], lambda ctx: ctx.get("uppercase", lambda: None)(), KeyMode.NORMAL, 500, "Uppercase (gU)"),
    KeySequence(["g", "J"], lambda ctx: ctx.get("join_no_space", lambda: None)(), KeyMode.NORMAL, 500, "Join without space (gJ)"),
    KeySequence(["z", "z"], lambda ctx: ctx.get("center_line", lambda: None)(), KeyMode.NORMAL, 500, "Center line (zz)"),
    KeySequence(["z", "t"], lambda ctx: ctx.get("top_line", lambda: None)(), KeyMode.NORMAL, 500, "Top line (zt)"),
    KeySequence(["z", "b"], lambda ctx: ctx.get("bottom_line", lambda: None)(), KeyMode.NORMAL, 500, "Bottom line (zb)"),
]


def create_default_keybindings() -> KeybindingsManager:
    """Create manager with default bindings."""
    manager = KeybindingsManager()

    for binding in DEFAULT_CLI_BINDINGS:
        manager.bind(
            key=binding.key,
            handler=binding.handler,
            mode=binding.mode,
            description=binding.description,
            repeatable=binding.repeatable,
            platform=binding.platform,
            priority=binding.priority,
            group=binding.group,
        )

    for sequence in DEFAULT_CLI_SEQUENCES:
        manager.bind_sequence(
            keys=sequence.keys,
            handler=sequence.handler,
            mode=sequence.mode,
            timeout_ms=sequence.timeout_ms,
            description=sequence.description,
        )

    return manager


# Singleton manager
_keybindings_manager: Optional[KeybindingsManager] = None


def get_keybindings_manager() -> KeybindingsManager:
    """Get global keybindings manager."""
    global _keybindings_manager
    if _keybindings_manager is None:
        _keybindings_manager = create_default_keybindings()
    return _keybindings_manager


async def use_keybindings(bindings: Dict[str, Callable] = None) -> KeybindingsManager:
    """Hook for keybindings.

    Usage:
        kb = await use_keybindings({
            "ctrl+p": lambda: print("Previous"),
            "ctrl+n": lambda: print("Next"),
        })
    """
    manager = get_keybindings_manager()

    if bindings:
        for key, handler in bindings:
            manager.bind(key, handler)

    return manager


# Import submodules
from .parser import KeyParser, parse_key, key_to_display
from .config import (
    KeybindingConfig,
    load_keybindings,
    save_keybindings,
    apply_config,
    find_config,
    load_user_keybindings,
    DEFAULT_CONFIG_PATHS,
    EXAMPLE_CONFIG,
)


__all__ = [
    # Core
    "KeyMode",
    "Platform",
    "KeyBinding",
    "KeySequence",
    "KeyConflict",
    "KeybindingsManager",
    "PLATFORM_KEY_MAPPINGS",
    "normalize_key",
    "DEFAULT_CLI_BINDINGS",
    "DEFAULT_CLI_SEQUENCES",
    "create_default_keybindings",
    "get_keybindings_manager",
    "use_keybindings",
    # Parser
    "KeyParser",
    "parse_key",
    "key_to_display",
    # Config
    "KeybindingConfig",
    "load_keybindings",
    "save_keybindings",
    "apply_config",
    "find_config",
    "load_user_keybindings",
    "DEFAULT_CONFIG_PATHS",
    "EXAMPLE_CONFIG",
]