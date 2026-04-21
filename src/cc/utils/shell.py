"""Shell Utilities - Shell command utilities."""

from __future__ import annotations
import os
import platform
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ShellType(Enum):
    """Shell types."""
    BASH = "bash"
    ZSH = "zsh"
    SH = "sh"
    POWERSHELL = "powershell"
    CMD = "cmd"
    FISH = "fish"


@dataclass
class ShellInfo:
    """Shell information."""
    type: ShellType
    path: str
    version: str = ""
    is_default: bool = False
    features: List[str] = field(default_factory=list)


class ShellDetector:
    """Detect and manage shell environment."""
    
    def __init__(self):
        self._current_shell: Optional[ShellInfo] = None
        self._available_shells: List[ShellInfo] = []
        self._detect_shells()
    
    def _detect_shells(self) -> None:
        """Detect available shells."""
        system = platform.system()
        
        if system == "Windows":
            self._detect_windows_shells()
        else:
            self._detect_unix_shells()
    
    def _detect_unix_shells(self) -> None:
        """Detect Unix shells."""
        shell_env = os.environ.get("SHELL", "")
        
        # Check common shell paths
        shell_paths = {
            "/bin/bash": ShellType.BASH,
            "/bin/zsh": ShellType.ZSH,
            "/bin/sh": ShellType.SH,
            "/bin/fish": ShellType.FISH,
            "/usr/bin/bash": ShellType.BASH,
            "/usr/bin/zsh": ShellType.ZSH,
            "/usr/bin/fish": ShellType.FISH,
        }
        
        for path, shell_type in shell_paths.items():
            if os.path.exists(path):
                is_default = path == shell_env
                self._available_shells.append(
                    ShellInfo(type=shell_type, path=path, is_default=is_default)
                )
        
        # Set current shell
        if shell_env:
            self._current_shell = ShellInfo(
                type=shell_paths.get(shell_env, ShellType.SH),
                path=shell_env,
                is_default=True,
            )
    
    def _detect_windows_shells(self) -> None:
        """Detect Windows shells."""
        # PowerShell
        if os.path.exists("C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"):
            self._available_shells.append(
                ShellInfo(type=ShellType.POWERSHELL, path="powershell.exe")
            )
        
        # CMD
        if os.path.exists("C:\\Windows\\System32\\cmd.exe"):
            self._available_shells.append(
                ShellInfo(type=ShellType.CMD, path="cmd.exe")
            )
        
        self._current_shell = self._available_shells[0] if self._available_shells else None
    
    def get_current_shell(self) -> Optional[ShellInfo]:
        """Get current shell info."""
        return self._current_shell
    
    def get_available_shells(self) -> List[ShellInfo]:
        """Get available shells."""
        return self._available_shells
    
    def is_unix(self) -> bool:
        """Check if Unix-like system."""
        return platform.system() != "Windows"
    
    def get_shell_command(self, shell_type: ShellType) -> str:
        """Get shell command prefix."""
        if shell_type == ShellType.POWERSHELL:
            return "powershell.exe -Command"
        elif shell_type == ShellType.CMD:
            return "cmd.exe /c"
        else:
            return ""  # Direct execution on Unix


# Global shell detector
_shell_detector: Optional[ShellDetector] = None


def get_shell_detector() -> ShellDetector:
    """Get global shell detector."""
    global _shell_detector
    if _shell_detector is None:
        _shell_detector = ShellDetector()
    return _shell_detector


def get_current_shell() -> Optional[ShellInfo]:
    """Get current shell."""
    return get_shell_detector().get_current_shell()


__all__ = [
    "ShellType",
    "ShellInfo",
    "ShellDetector",
    "get_shell_detector",
    "get_current_shell",
]
