"""Notifier Service - System notifications."""

from __future__ import annotations
import asyncio
import subprocess
import shutil
from typing import List, Dict, Optional, Any, Callable, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum


class NotificationLevel(Enum):
    """Notification level."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class Notification:
    """Notification data."""
    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    timestamp: float = field(default_factory=lambda: 0.0)
    actions: List[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class NotifierService:
    """Service for system notifications."""

    def __init__(self):
        self._notifications: List[Notification] = []
        self._max_notifications = 100
        self._handlers: List[Callable] = []
        self._platform = self._detect_platform()

    def _detect_platform(self) -> str:
        """Detect platform."""
        import platform
        system = platform.system()
        if system == "Darwin":
            return "macos"
        elif system == "Linux":
            return "linux"
        elif system == "Windows":
            return "windows"
        return "unknown"

    def notify(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        actions: Optional[List[dict]] = None,
    ) -> Notification:
        """Send notification."""
        notification = Notification(
            title=title,
            message=message,
            level=level,
            timestamp=asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0.0,
            actions=actions or [],
        )

        self._notifications.append(notification)

        # Trim if needed
        if len(self._notifications) > self._max_notifications:
            self._notifications = self._notifications[-self._max_notifications:]

        # Trigger handlers
        for handler in self._handlers:
            try:
                handler(notification)
            except Exception:
                pass

        # Send system notification
        self._send_system_notification(notification)

        return notification

    def _send_system_notification(self, notification: Notification) -> bool:
        """Send actual system notification."""
        try:
            if self._platform == "macos":
                return self._notify_macos(notification)
            elif self._platform == "linux":
                return self._notify_linux(notification)
            elif self._platform == "windows":
                return self._notify_windows(notification)
        except Exception:
            return False
        return False

    def _notify_macos(self, notification: Notification) -> bool:
        """Send macOS notification."""
        # Try terminal-notifier first
        if shutil.which("terminal-notifier"):
            subprocess.run([
                "terminal-notifier",
                "-title", notification.title,
                "-message", notification.message,
                "-sound", "default",
            ], check=False)
            return True

        # Fall back to osascript
        script = f'''
        display notification "{notification.message}" with title "{notification.title}"
        '''
        subprocess.run(["osascript", "-e", script], check=False)
        return True

    def _notify_linux(self, notification: Notification) -> bool:
        """Send Linux notification."""
        if shutil.which("notify-send"):
            urgency = "normal"
            if notification.level == NotificationLevel.ERROR:
                urgency = "critical"
            elif notification.level == NotificationLevel.WARNING:
                urgency = "normal"

            subprocess.run([
                "notify-send",
                "-u", urgency,
                notification.title,
                notification.message,
            ], check=False)
            return True
        return False

    def _notify_windows(self, notification: Notification) -> bool:
        """Send Windows notification."""
        # PowerShell toast notification
        if shutil.which("powershell"):
            script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName('text')
            $textNodes.Item(0).AppendChild($template.CreateTextNode('{notification.title}')) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode('{notification.message}')) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Claude Code').Show($toast)
            '''
            subprocess.run(["powershell", "-Command", script], check=False)
            return True
        return False

    def add_handler(self, handler: Callable) -> None:
        """Add notification handler."""
        self._handlers.append(handler)

    def get_notifications(self, level: Optional[NotificationLevel] = None) -> List[Notification]:
        """Get notifications."""
        if level:
            return [n for n in self._notifications if n.level == level]
        return self._notifications.copy()

    def clear_notifications(self) -> int:
        """Clear notifications."""
        count = len(self._notifications)
        self._notifications.clear()
        return count

    def get_stats(self) -> dict:
        """Get notification statistics."""
        by_level: Dict[str, int] = {}
        for n in self._notifications:
            by_level[n.level.value] = by_level.get(n.level.value, 0) + 1

        return {
            "total_notifications": len(self._notifications),
            "by_level": by_level,
            "platform": self._platform,
        }


# Global notifier
_notifier: Optional[NotifierService] = None


def get_notifier() -> NotifierService:
    """Get global notifier."""
    global _notifier
    if _notifier is None:
        _notifier = NotifierService()
    return _notifier


def notify(title: str, message: str, level: NotificationLevel = NotificationLevel.INFO) -> Notification:
    """Send notification globally."""
    return get_notifier().notify(title, message, level)


__all__ = [
    "NotificationLevel",
    "Notification",
    "NotifierService",
    "get_notifier",
    "notify",
]
