"""Clipboard Hook - Async clipboard operations."""

from __future__ import annotations
import asyncio
import subprocess
from typing import Any, Dict, Callable, Optional, List
from dataclasses import dataclass


@dataclass
class ClipboardContent:
    """Clipboard content."""
    text: Optional[str] = None
    image_path: Optional[str] = None
    html: Optional[str] = None
    rtf: Optional[str] = None


class ClipboardHook:
    """Async clipboard operations hook."""

    def __init__(self):
        self._platform = self._detect_platform()
        self._copy_cmd = self._get_copy_command()
        self._paste_cmd = self._get_paste_command()

    def _detect_platform(self) -> str:
        """Detect current platform."""
        import platform
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "windows":
            return "windows"
        elif system == "linux":
            return "linux"
        return "unknown"

    def _get_copy_command(self) -> List[str]:
        """Get platform copy command."""
        if self._platform == "macos":
            return ["pbcopy"]
        elif self._platform == "linux":
            return ["xclip", "-selection", "clipboard"]
        elif self._platform == "windows":
            return ["clip"]
        return []

    def _get_paste_command(self) -> List[str]:
        """Get platform paste command."""
        if self._platform == "macos":
            return ["pbpaste"]
        elif self._platform == "linux":
            return ["xclip", "-selection", "clipboard", "-o"]
        elif self._platform == "windows":
            return ["powershell", "-command", "Get-Clipboard"]
        return []

    async def copy_text(self, text: str) -> bool:
        """Copy text to clipboard.

        Args:
            text: Text to copy

        Returns:
            True if successful
        """
        if not self._copy_cmd:
            return False

        try:
            proc = await asyncio.create_subprocess_exec(
                *self._copy_cmd,
                stdin=asyncio.subprocess.PIPE,
            )
            await proc.communicate(input=text.encode())
            return proc.returncode == 0
        except Exception:
            return False

    async def paste_text(self) -> Optional[str]:
        """Paste text from clipboard.

        Returns:
            Clipboard text or None
        """
        if not self._paste_cmd:
            return None

        try:
            proc = await asyncio.create_subprocess_exec(
                *self._paste_cmd,
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip()
        except Exception:
            pass
        return None

    async def copy_image(self, image_path: str) -> bool:
        """Copy image to clipboard.

        Args:
            image_path: Path to image file

        Returns:
            True if successful
        """
        if self._platform == "macos":
            try:
                proc = await asyncio.create_subprocess_exec(
                    "osascript", "-e",
                    f'tell app "Finder" to set the clipboard to (POSIX file "{image_path}")',
                )
                await proc.wait()
                return proc.returncode == 0
            except Exception:
                return False
        elif self._platform == "linux":
            try:
                proc = await asyncio.create_subprocess_exec(
                    "xclip", "-selection", "clipboard",
                    "-t", "image/png", "-i", image_path,
                )
                await proc.wait()
                return proc.returncode == 0
            except Exception:
                return False
        return False

    async def get_clipboard_content(self) -> ClipboardContent:
        """Get all clipboard content.

        Returns:
            ClipboardContent with available data
        """
        content = ClipboardContent()

        # Get text
        text = await self.paste_text()
        if text:
            content.text = text

        # Check for image (macOS)
        if self._platform == "macos":
            try:
                proc = await asyncio.create_subprocess_exec(
                    "osascript", "-e",
                    'get clipboard as «class PNGf»',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    content.image_path = "clipboard_image.png"
            except Exception:
                pass

        return content

    async def clear_clipboard(self) -> bool:
        """Clear clipboard content.

        Returns:
            True if successful
        """
        return await self.copy_text("")

    async def watch_clipboard(
        self,
        callback: Callable[[ClipboardContent], None],
        interval: float = 0.5,
    ) -> None:
        """Watch clipboard for changes.

        Args:
            callback: Function to call on change
            interval: Check interval in seconds
        """
        last_content = await self.paste_text() or ""

        while True:
            await asyncio.sleep(interval)
            current = await self.paste_text() or ""

            if current != last_content:
                last_content = current
                content = ClipboardContent(text=current)
                if asyncio.iscoroutinefunction(callback):
                    await callback(content)
                else:
                    callback(content)


# Global clipboard hook
_clipboard_hook: Optional[ClipboardHook] = None


def get_clipboard_hook() -> ClipboardHook:
    """Get global clipboard hook."""
    global _clipboard_hook
    if _clipboard_hook is None:
        _clipboard_hook = ClipboardHook()
    return _clipboard_hook


async def use_clipboard() -> Dict[str, Any]:
    """Clipboard hook for hooks module.

    Returns clipboard functions.
    """
    hook = get_clipboard_hook()

    return {
        "copy": hook.copy_text,
        "paste": hook.paste_text,
        "copy_image": hook.copy_image,
        "get_content": hook.get_clipboard_content,
        "clear": hook.clear_clipboard,
        "watch": hook.watch_clipboard,
    }


__all__ = [
    "ClipboardContent",
    "ClipboardHook",
    "get_clipboard_hook",
    "use_clipboard",
]