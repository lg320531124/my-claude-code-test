"""Keybindings Parser - Parse keybinding configurations."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class KeyModifier(Enum):
    """Key modifiers."""
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    META = "meta"  # Cmd on Mac


@dataclass
class KeyBinding:
    """Key binding definition."""
    key: str
    modifiers: List[KeyModifier]
    action: str
    context: str = "global"
    description: str = ""
    when: Optional[str] = None  # Condition for binding


@dataclass
class KeySequence:
    """Multi-key sequence."""
    keys: List[KeyBinding]
    action: str
    timeout_ms: int = 500


class KeyParser:
    """Parse keybinding configurations."""

    # ANSI escape sequences
    ANSI_CODES = {
        "\x1b[A": "up",
        "\x1b[B": "down",
        "\x1b[C": "right",
        "\x1b[D": "left",
        "\x1b[H": "home",
        "\x1b[F": "end",
        "\x1b[1~": "home",
        "\x1b[4~": "end",
        "\x1b[5~": "page_up",
        "\x1b[6~": "page_down",
        "\x1b[2~": "insert",
        "\x1b[3~": "delete",
        "\x1b[Z": "shift_tab",
    }

    # Special keys
    SPECIAL_KEYS = {
        "Enter": "enter",
        "Escape": "escape",
        "Tab": "tab",
        "Backspace": "backspace",
        "Space": "space",
        "Up": "up",
        "Down": "down",
        "Left": "left",
        "Right": "right",
        "Home": "home",
        "End": "end",
        "PageUp": "page_up",
        "PageDown": "page_down",
        "Delete": "delete",
        "Insert": "insert",
    }

    def __init__(self):
        self._bindings: Dict[str, KeyBinding] = {}
        self._sequences: Dict[str, KeySequence] = {}
        self._platform_modifiers: Dict[str, KeyModifier] = self._get_platform_modifiers()

    def _get_platform_modifiers(self) -> Dict[str, KeyModifier]:
        """Get platform-specific modifier names."""
        import platform
        system = platform.system()

        if system == "Darwin":  # macOS
            return {
                "Cmd": KeyModifier.META,
                "Command": KeyModifier.META,
                "Option": KeyModifier.ALT,
                "Control": KeyModifier.CTRL,
                "Shift": KeyModifier.SHIFT,
            }
        else:  # Windows/Linux
            return {
                "Ctrl": KeyModifier.CTRL,
                "Alt": KeyModifier.ALT,
                "Shift": KeyModifier.SHIFT,
                "Meta": KeyModifier.META,
            }

    def parse_binding(self, binding_str: str) -> Optional[KeyBinding]:
        """Parse binding string like 'Ctrl+Shift+A'."""
        parts = binding_str.split("+")

        if not parts:
            return None

        # Last part is the key
        key = parts[-1]

        # Rest are modifiers
        modifiers = []
        for mod_str in parts[:-1]:
            modifier = self._platform_modifiers.get(mod_str)
            if modifier:
                modifiers.append(modifier)

        return KeyBinding(
            key=self._normalize_key(key),
            modifiers=modifiers,
            action="",  # Set by caller
        )

    def _normalize_key(self, key: str) -> str:
        """Normalize key name."""
        # Handle special keys
        if key in self.SPECIAL_KEYS:
            return self.SPECIAL_KEYS[key]

        # Single character
        if len(key) == 1:
            return key.lower()

        # F1-F12
        if key.startswith("F") and key[1:].isdigit():
            return key.lower()

        return key.lower()

    def parse_config(self, config: Dict[str, Any]) -> List[KeyBinding]:
        """Parse keybinding configuration."""
        bindings = []

        for binding_str, action_config in config.items():
            binding = self.parse_binding(binding_str)

            if binding:
                if isinstance(action_config, str):
                    binding.action = action_config
                else:
                    binding.action = action_config.get("action", "")
                    binding.description = action_config.get("description", "")
                    binding.context = action_config.get("context", "global")
                    binding.when = action_config.get("when")

                bindings.append(binding)
                self._bindings[binding_str] = binding

        return bindings

    def parse_sequence(self, sequence_str: str, action: str) -> KeySequence:
        """Parse multi-key sequence like 'g g'."""
        parts = sequence_str.split()

        keys = []
        for part in parts:
            binding = self.parse_binding(part)
            if binding:
                binding.action = ""  # Part of sequence
                keys.append(binding)

        return KeySequence(keys=keys, action=action)

    def load_from_file(self, path: Path) -> List[KeyBinding]:
        """Load bindings from JSON file."""
        if not path.exists():
            return []

        content = path.read_text()
        config = json.loads(content)

        return self.parse_config(config)

    def match_key(self, key: str, modifiers: List[KeyModifier]) -> Optional[KeyBinding]:
        """Match key event to binding."""
        for binding_str, binding in self._bindings.items():
            if binding.key == key and set(binding.modifiers) == set(modifiers):
                return binding

        return None

    def match_sequence(self, keys_pressed: List[str]) -> Optional[KeySequence]:
        """Match key sequence."""
        keys_str = " ".join(keys_pressed)

        return self._sequences.get(keys_str)

    def decode_ansi(self, data: bytes) -> Optional[str]:
        """Decode ANSI escape sequence."""
        data_str = data.decode("utf-8", errors="replace")

        # Check known codes
        for code, key in self.ANSI_CODES.items():
            if data_str.startswith(code):
                return key

        # Regular key
        if len(data_str) == 1:
            return data_str

        return None

    def add_binding(self, binding: KeyBinding) -> None:
        """Add key binding."""
        binding_str = self._binding_to_string(binding)
        self._bindings[binding_str] = binding

    def _binding_to_string(self, binding: KeyBinding) -> str:
        """Convert binding to string."""
        parts = [m.value.capitalize() for m in binding.modifiers]
        parts.append(binding.key.capitalize())
        return "+".join(parts)

    def get_bindings(self) -> Dict[str, KeyBinding]:
        """Get all bindings."""
        return self._bindings.copy()


__all__ = [
    "KeyModifier",
    "KeyBinding",
    "KeySequence",
    "KeyParser",
]