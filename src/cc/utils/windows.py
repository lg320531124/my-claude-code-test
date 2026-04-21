"""Windows Compatibility - Windows-specific utilities."""

from __future__ import annotations
import os
import platform
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class WindowsInfo:
    """Windows system info."""
    is_windows: bool
    version: str = ""
    powershell_available: bool = False
    cmd_available: bool = False


class WindowsCompat:
    """Windows compatibility utilities."""
    
    def __init__(self):
        self._is_windows = platform.system() == "Windows"
        self._info: Optional[WindowsInfo] = None
    
    def get_info(self) -> WindowsInfo:
        """Get Windows info."""
        if self._info:
            return self._info
        
        version = ""
        ps_avail = False
        cmd_avail = False
        
        if self._is_windows:
            try:
                version = platform.version()
                ps_avail = os.path.exists(
                    "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
                )
                cmd_avail = os.path.exists("C:\\Windows\\System32\\cmd.exe")
            except:
                pass
        
        self._info = WindowsInfo(
            is_windows=self._is_windows,
            version=version,
            powershell_available=ps_avail,
            cmd_available=cmd_avail,
        )
        
        return self._info
    
    def is_windows(self) -> bool:
        """Check if Windows."""
        return self._is_windows
    
    def get_home(self) -> Path:
        """Get home directory."""
        if self._is_windows:
            return Path(os.environ.get("USERPROFILE", "C:\\Users"))
        return Path.home()
    
    def get_shell(self) -> str:
        """Get default shell."""
        if self._is_windows:
            if self.get_info().powershell_available:
                return "powershell"
            return "cmd"
        return os.environ.get("SHELL", "/bin/bash")
    
    def get_path_separator(self) -> str:
        """Get path separator."""
        return ";" if self._is_windows else ":"
    
    def get_line_ending(self) -> str:
        """Get line ending."""
        return "\r\n" if self._is_windows else "\n"
    
    def normalize_path(self, path: str) -> str:
        """Normalize path for current OS."""
        if self._is_windows:
            return path.replace("/", "\\")
        return path.replace("\\", "/")
    
    def get_temp_dir(self) -> Path:
        """Get temp directory."""
        if self._is_windows:
            return Path(os.environ.get("TEMP", "C:\\Windows\\Temp"))
        return Path("/tmp")
    
    def get_env_path(self) -> List[str]:
        """Get PATH directories."""
        path_env = os.environ.get("PATH", "")
        separator = self.get_path_separator()
        return path_env.split(separator) if path_env else []
    
    def is_admin(self) -> bool:
        """Check if running as admin."""
        if self._is_windows:
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                return False
        return os.geteuid() == 0
    
    def get_drives(self) -> List[str]:
        """Get available drives (Windows)."""
        if not self._is_windows:
            return []
        
        drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
        
        return drives


# Global instance
_windows_compat: Optional[WindowsCompat] = None


def get_windows_compat() -> WindowsCompat:
    """Get global Windows compatibility."""
    global _windows_compat
    if _windows_compat is None:
        _windows_compat = WindowsCompat()
    return _windows_compat


def is_windows() -> bool:
    """Check if Windows."""
    return get_windows_compat().is_windows()


__all__ = [
    "WindowsInfo",
    "WindowsCompat",
    "get_windows_compat",
    "is_windows",
]
