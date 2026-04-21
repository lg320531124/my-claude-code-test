"""Key Parser - Parse keyboard input from terminal.

Handles parsing of raw terminal input into normalized key strings.
Supports escape sequences, special keys, and modifier combinations.
"""

from __future__ import annotations
import re
from typing import Optional, Tuple, Dict


class KeyParser:
    """Parse raw terminal input into key strings."""

    # ANSI escape sequences for special keys
    ANSI_CODES: Dict[str, str] = {
        # Arrow keys
        "\x1b[A": "up",
        "\x1b[B": "down",
        "\x1b[C": "right",
        "\x1b[D": "left",

        # Modified arrow keys (xterm)
        "\x1b[1;2A": "shift+up",
        "\x1b[1;2B": "shift+down",
        "\x1b[1;2C": "shift+right",
        "\x1b[1;2D": "shift+left",
        "\x1b[1;5A": "ctrl+up",
        "\x1b[1;5B": "ctrl+down",
        "\x1b[1;5C": "ctrl+right",
        "\x1b[1;5D": "ctrl+left",
        "\x1b[1;3A": "alt+up",
        "\x1b[1;3B": "alt+down",
        "\x1b[1;3C": "alt+right",
        "\x1b[1;3D": "alt+left",
        "\x1b[1;4A": "shift+alt+up",
        "\x1b[1;4B": "shift+alt+down",
        "\x1b[1;4C": "shift+alt+right",
        "\x1b[1;4D": "shift+alt+left",

        # Function keys
        "\x1bOP": "f1",
        "\x1bOQ": "f2",
        "\x1bOR": "f3",
        "\x1bOS": "f4",
        "\x1b[15~": "f5",
        "\x1b[17~": "f6",
        "\x1b[18~": "f7",
        "\x1b[19~": "f8",
        "\x1b[20~": "f9",
        "\x1b[21~": "f10",
        "\x1b[23~": "f11",
        "\x1b[24~": "f12",

        # Modified function keys
        "\x1b[1;2P": "shift+f1",
        "\x1b[1;5P": "ctrl+f1",
        "\x1b[1;6P": "ctrl+shift+f1",

        # Navigation keys
        "\x1b[5~": "pageup",
        "\x1b[6~": "pagedown",
        "\x1b[H": "home",
        "\x1b[F": "end",

        # Modified navigation keys
        "\x1b[5;2~": "shift+pageup",
        "\x1b[6;2~": "shift+pagedown",
        "\x1b[5;5~": "ctrl+pageup",
        "\x1b[6;5~": "ctrl+pagedown",

        # Editing keys
        "\x1b[2~": "insert",
        "\x1b[3~": "delete",

        # Misc
        "\x1b[Z": "shift+tab",  # Backtab
        "\x1b[200~": "bracketed_paste_start",
        "\x1b[201~": "bracketed_paste_end",
    }

    # Single byte special keys
    SINGLE_BYTE: Dict[int, str] = {
        0: "ctrl+space",
        1: "ctrl+a",
        2: "ctrl+b",
        3: "ctrl+c",
        4: "ctrl+d",
        5: "ctrl+e",
        6: "ctrl+f",
        7: "ctrl+g",
        8: "backspace",
        9: "tab",
        10: "enter",
        11: "ctrl+k",
        12: "ctrl+l",
        13: "enter",
        14: "ctrl+n",
        15: "ctrl+o",
        16: "ctrl+p",
        17: "ctrl+q",
        18: "ctrl+r",
        19: "ctrl+s",
        20: "ctrl+t",
        21: "ctrl+u",
        22: "ctrl+v",
        23: "ctrl+w",
        24: "ctrl+x",
        25: "ctrl+y",
        26: "ctrl+z",
        27: "escape",
        28: "ctrl+\\",
        29: "ctrl+]",
        30: "ctrl+^",
        31: "ctrl+_",
        32: "space",
        127: "backspace",
    }

    def __init__(self):
        self._buffer: bytes = b""
        self._bracketed_paste_mode: bool = False
        self._paste_buffer: str = ""

    def parse(self, data: bytes) -> Tuple[str, bool]:
        """Parse raw bytes into key string.

        Returns:
            (key_string, is_complete) - is_complete indicates if more bytes needed
        """
        self._buffer += data

        # Check for bracketed paste
        if self._bracketed_paste_mode:
            if b"\x1b[201~" in self._buffer:
                # End of bracketed paste
                end_idx = self._buffer.find(b"\x1b[201~")
                paste_data = self._buffer[:end_idx].decode("utf-8", errors="replace")
                self._buffer = self._buffer[end_idx + 6:]
                self._bracketed_paste_mode = False
                return ("paste:" + paste_data, True)
            else:
                # Still collecting paste
                return ("", False)

        # Check for escape sequence start
        if self._buffer.startswith(b"\x1b"):
            # Check for bracketed paste start
            if self._buffer.startswith(b"\x1b[200~"):
                self._bracketed_paste_mode = True
                self._buffer = self._buffer[6:]
                return ("", False)

            # Check for complete ANSI sequence
            for seq, key in self.ANSI_CODES.items():
                if self._buffer.decode("latin-1", errors="replace").startswith(seq):
                    remaining = self._buffer[len(seq.encode("latin-1")):]
                    self._buffer = remaining
                    return (key, True)

            # Escape sequence incomplete, need more bytes
            if len(self._buffer) < 3:
                return ("", False)

            # Unknown escape sequence, just return escape
            if len(self._buffer) == 1:
                self._buffer = b""
                return ("escape", True)

            # Try to parse CSI sequence
            csi_pattern = re.compile(r"\x1b\[([0-9;]*)([A-Za-z])")
            text = self._buffer.decode("latin-1", errors="replace")
            match = csi_pattern.match(text)

            if match:
                params = match.group(1)
                final = match.group(2)
                key = self._parse_csi(params, final)
                self._buffer = self._buffer[len(match.group(0)):]
                return (key, True)

            # Unknown sequence, consume and return escape
            self._buffer = b""
            return ("escape", True)

        # Check for single byte special key
        if len(self._buffer) == 1:
            byte_val = self._buffer[0]

            if byte_val in self.SINGLE_BYTE:
                self._buffer = b""
                return (self.SINGLE_BYTE[byte_val], True)

            # Regular character
            if byte_val < 32:
                # Control key
                key = chr(byte_val + 64)
                self._buffer = b""
                return (f"ctrl+{key.lower()}", True)

            if byte_val < 127:
                # Regular printable
                self._buffer = b""
                return (chr(byte_val), True)

        # Multi-byte UTF-8
        if len(self._buffer) > 1:
            try:
                text = self._buffer.decode("utf-8")
                self._buffer = b""
                return (text, True)
            except UnicodeDecodeError:
                # Incomplete UTF-8, need more bytes
                return ("", False)

        return ("", False)

    def _parse_csi(self, params: str, final: str) -> str:
        """Parse CSI escape sequence."""
        # Standard VT100 codes
        if final in "ABCD":
            arrow_keys = {"A": "up", "B": "down", "C": "right", "D": "left"}
            key = arrow_keys[final]

            if params:
                modifiers = params.split(";")
                if len(modifiers) >= 2:
                    mod_num = int(modifiers[1]) if modifiers[1] else 0
                    key = self._apply_modifier(key, mod_num)

            return key

        # Home/End
        if final == "H":
            return "home"
        if final == "F":
            return "end"

        # Function keys
        if final == "~":
            key_codes = {
                "1": "home",
                "2": "insert",
                "3": "delete",
                "4": "end",
                "5": "pageup",
                "6": "pagedown",
                "7": "home",
                "8": "end",
                "11": "f1",
                "12": "f2",
                "13": "f3",
                "14": "f4",
                "15": "f5",
                "17": "f6",
                "18": "f7",
                "19": "f8",
                "20": "f9",
                "21": "f10",
                "23": "f11",
                "24": "f12",
            }

            if params:
                parts = params.split(";")
                key_num = parts[0]

                key = key_codes.get(key_num, f"unknown_{key_num}")

                if len(parts) >= 2:
                    mod_num = int(parts[1])
                    key = self._apply_modifier(key, mod_num)

                return key

        return f"csi_{params}_{final}"

    def _apply_modifier(self, key: str, mod_num: int) -> str:
        """Apply modifier to key."""
        modifiers = []

        if mod_num == 0:
            return key

        # Modifier codes: 2=shift, 3=alt, 4=shift+alt, 5=ctrl, 6=shift+ctrl, 7=ctrl+alt, 8=shift+ctrl+alt
        if mod_num & 1:  # shift
            modifiers.append("shift")
        if mod_num & 2:  # alt/meta
            modifiers.append("alt")
        if mod_num & 4:  # ctrl
            modifiers.append("ctrl")

        # Simpler mapping
        simple_mods = {
            2: "shift",
            3: "alt",
            4: "shift+alt",
            5: "ctrl",
            6: "shift+ctrl",
            7: "ctrl+alt",
            8: "shift+ctrl+alt",
            9: "meta",
        }

        if mod_num in simple_mods:
            mod_str = simple_mods[mod_num]
            return f"{mod_str}+{key}"

        return key

    def reset(self) -> None:
        """Reset buffer."""
        self._buffer = b""
        self._bracketed_paste_mode = False


def parse_key(data: bytes) -> Optional[str]:
    """Quick parse of key from bytes."""
    parser = KeyParser()
    key, complete = parser.parse(data)
    return key if complete else None


def key_to_display(key: str) -> str:
    """Convert key string to display format."""
    # Split modifiers
    parts = key.split("+")

    display_parts = []
    for part in parts:
        display = {
            "ctrl": "⌃",
            "alt": "⌥",
            "option": "⌥",
            "shift": "⇧",
            "cmd": "⌘",
            "super": "⌘",
            "up": "↑",
            "down": "↓",
            "left": "←",
            "right": "→",
            "escape": "Esc",
            "enter": "⏎",
            "backspace": "⌫",
            "delete": "⌦",
            "tab": "⇥",
            "space": "␣",
            "pageup": "PgUp",
            "pagedown": "PgDn",
            "home": "Home",
            "end": "End",
        }.get(part, part)

        display_parts.append(display)

    return "".join(display_parts)


__all__ = [
    "KeyParser",
    "parse_key",
    "key_to_display",
]