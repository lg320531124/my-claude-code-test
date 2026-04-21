"""Keybindings Manager - Manage keybindings."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .parser import KeyParser, KeyBinding, KeySequence, KeyModifier


class KeyMode(Enum):
    """Keybinding modes."""
    NORMAL = "normal"
    INSERT = "insert"
    VISUAL = "visual"
    COMMAND = "command"


@dataclass
class KeybindingConflict:
    """Keybinding conflict."""
    binding1: KeyBinding
    binding2: KeyBinding
    message: str


class KeybindingManager:
    """Manage keybindings."""

    def __init__(self):
        self._parser = KeyParser()
        self._bindings: Dict[KeyMode, Dict[str, KeyBinding]] = {}
        self._sequences: Dict[KeyMode, Dict[str, KeySequence]] = {}
        self._handlers: Dict[str, Callable] = {}
        self._current_mode: KeyMode = KeyMode.NORMAL
        self._sequence_buffer: List[str] = []
        self._sequence_timeout: asyncio.Task = None

    def set_mode(self, mode: KeyMode) -> None:
        """Set current key mode."""
        self._current_mode = mode

    def get_mode(self) -> KeyMode:
        """Get current mode."""
        return self._current_mode

    def register_binding(
        self,
        key: str,
        action: str,
        handler: Callable,
        mode: KeyMode = None,
        modifiers: List[KeyModifier] = None,
    ) -> KeyBinding:
        """Register keybinding."""
        binding = KeyBinding(
            key=key,
            modifiers=modifiers or [],
            action=action,
        )

        target_mode = mode or self._current_mode

        if target_mode not in self._bindings:
            self._bindings[target_mode] = {}

        binding_str = self._parser._binding_to_string(binding)
        self._bindings[target_mode][binding_str] = binding
        self._handlers[action] = handler

        return binding

    def register_sequence(
        self,
        keys: List[str],
        action: str,
        handler: Callable,
        mode: KeyMode = None,
    ) -> KeySequence:
        """Register multi-key sequence."""
        sequence = KeySequence(
            keys=[KeyBinding(key=k, modifiers=[], action="") for k in keys],
            action=action,
        )

        target_mode = mode or self._current_mode

        if target_mode not in self._sequences:
            self._sequences[target_mode] = {}

        sequence_str = " ".join(keys)
        self._sequences[target_mode][sequence_str] = sequence
        self._handlers[action] = handler

        return sequence

    async def handle_key(
        self,
        key: str,
        modifiers: List[KeyModifier] = None,
    ) -> Optional[Any]:
        """Handle key press."""
        modifiers = modifiers or []

        # Check sequence buffer
        if self._sequence_buffer:
            self._sequence_buffer.append(key)
            sequence_str = " ".join(self._sequence_buffer)

            # Check for sequence match
            sequences = self._sequences.get(self._current_mode, {})
            matched = sequences.get(sequence_str)

            if matched:
                self._sequence_buffer.clear()
                if self._sequence_timeout:
                    self._sequence_timeout.cancel()

                handler = self._handlers.get(matched.action)
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        return await handler()
                    else:
                        return handler()

            # Partial match - wait for more
            partial_match = any(
                s.startswith(sequence_str)
                for s in sequences.keys()
            )

            if partial_match:
                return None  # Wait for more keys

            # No match - clear buffer and try single key
            self._sequence_buffer.clear()
            if self._sequence_timeout:
                self._sequence_timeout.cancel()

        # Try single key binding
        bindings = self._bindings.get(self._current_mode, {})
        matched = self._parser.match_key(key, modifiers)

        if matched:
            binding_str = self._parser._binding_to_string(matched)
            binding = bindings.get(binding_str)

            if binding:
                handler = self._handlers.get(binding.action)
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        return await handler()
                    else:
                        return handler()

        # Check if this starts a sequence
        sequences = self._sequences.get(self._current_mode, {})
        for seq_str in sequences.keys():
            if seq_str.startswith(key):
                self._sequence_buffer = [key]

                # Set timeout
                self._sequence_timeout = asyncio.create_task(
                    self._sequence_timeout_handler()
                )

                return None

        return None

    async def _sequence_timeout_handler(self) -> None:
        """Handle sequence timeout."""
        await asyncio.sleep(0.5)
        self._sequence_buffer.clear()

    def load_default_bindings(self) -> None:
        """Load default keybindings."""
        # Global bindings
        self.register_binding("escape", "cancel", lambda: None, KeyMode.NORMAL)
        self.register_binding("enter", "submit", lambda: None, KeyMode.NORMAL)

        # Navigation
        self.register_binding("up", "scroll_up", lambda: None, KeyMode.NORMAL)
        self.register_binding("down", "scroll_down", lambda: None, KeyMode.NORMAL)
        self.register_binding("page_up", "page_up", lambda: None, KeyMode.NORMAL)
        self.register_binding("page_down", "page_down", lambda: None, KeyMode.NORMAL)

        # Vim-style
        self.register_binding("j", "down", lambda: None, KeyMode.NORMAL)
        self.register_binding("k", "up", lambda: None, KeyMode.NORMAL)
        self.register_binding("h", "left", lambda: None, KeyMode.NORMAL)
        self.register_binding("l", "right", lambda: None, KeyMode.NORMAL)

        # Sequences
        self.register_sequence(["g", "g"], "goto_top", lambda: None, KeyMode.NORMAL)
        self.register_sequence(["G"], "goto_bottom", lambda: None, KeyMode.NORMAL)

        # Ctrl bindings
        self.register_binding("c", "copy", lambda: None, KeyMode.NORMAL, [KeyModifier.CTRL])
        self.register_binding("v", "paste", lambda: None, KeyMode.NORMAL, [KeyModifier.CTRL])

    def detect_conflicts(self) -> List[KeybindingConflict]:
        """Detect keybinding conflicts."""
        conflicts = []

        for mode in self._bindings:
            bindings = self._bindings[mode]
            seen = {}

            for binding_str, binding in bindings.items():
                # Check for duplicate bindings
                if binding_str in seen:
                    conflicts.append(KeybindingConflict(
                        binding1=seen[binding_str],
                        binding2=binding,
                        message=f"Duplicate binding: {binding_str} in {mode.value}",
                    ))

                seen[binding_str] = binding

        return conflicts

    def get_bindings_for_mode(self, mode: KeyMode) -> Dict[str, KeyBinding]:
        """Get bindings for specific mode."""
        return self._bindings.get(mode, {})

    def clear_mode_bindings(self, mode: KeyMode) -> None:
        """Clear bindings for mode."""
        self._bindings[mode] = {}
        self._sequences[mode] = {}


# Global manager
_manager: Optional[KeybindingManager] = None


def get_keybinding_manager() -> KeybindingManager:
    """Get global keybinding manager."""
    global _manager
    if _manager is None:
        _manager = KeybindingManager()
        _manager.load_default_bindings()
    return _manager


__all__ = [
    "KeyMode",
    "KeybindingConflict",
    "KeybindingManager",
    "get_keybinding_manager",
]