"""Notifier - Desktop and mobile notifications."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class NotificationPriority(Enum):
    """Notification priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(Enum):
    """Notification types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"


@dataclass
class Notification:
    """Notification data."""
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    timestamp: datetime = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationConfig:
    """Notification configuration."""
    enabled: bool = True
    sound: bool = True
    desktop: bool = True
    mobile: bool = False
    max_queue: int = 50


class NotificationManager:
    """Manage notifications."""

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self._queue: List[Notification] = []
        self._handlers: List[Any] = []
        self._history: List[Notification] = []

    async def send(
        self,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> bool:
        """Send notification."""
        if not self.config.enabled:
            return False

        notification = Notification(
            title=title,
            message=message,
            type=type,
            priority=priority,
            timestamp=datetime.now(),
        )

        # Add to queue
        self._queue.append(notification)

        # Trim queue
        if len(self._queue) > self.config.max_queue:
            self._queue = self._queue[-self.config.max_queue:]

        # Dispatch to handlers
        for handler in self._handlers:
            try:
                await handler(notification)
            except Exception as e:
                logger.error(f"Notification handler error: {e}")

        # Add to history
        self._history.append(notification)

        return True

    async def info(self, title: str, message: str) -> bool:
        """Send info notification."""
        return await self.send(title, message, NotificationType.INFO)

    async def success(self, title: str, message: str) -> bool:
        """Send success notification."""
        return await self.send(title, message, NotificationType.SUCCESS)

    async def warning(self, title: str, message: str) -> bool:
        """Send warning notification."""
        return await self.send(
            title, message, NotificationType.WARNING,
            NotificationPriority.HIGH
        )

    async def error(self, title: str, message: str) -> bool:
        """Send error notification."""
        return await self.send(
            title, message, NotificationType.ERROR,
            NotificationPriority.HIGH
        )

    async def progress(
        self,
        title: str,
        message: str,
        progress: float
    ) -> bool:
        """Send progress notification."""
        notification = Notification(
            title=title,
            message=message,
            type=NotificationType.PROGRESS,
            metadata={"progress": progress},
        )

        self._queue.append(notification)
        return True

    def add_handler(self, handler: Any) -> None:
        """Add notification handler."""
        self._handlers.append(handler)

    def remove_handler(self, handler: Any) -> bool:
        """Remove handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)
            return True
        return False

    async def get_queue(self) -> List[Notification]:
        """Get notification queue."""
        return list(self._queue)

    async def clear_queue(self) -> int:
        """Clear queue."""
        count = len(self._queue)
        self._queue.clear()
        return count

    async def get_history(
        self,
        limit: int = 100
    ) -> List[Notification]:
        """Get notification history."""
        return self._history[-limit:]

    async def mark_read(self, index: int) -> bool:
        """Mark notification as read."""
        if 0 <= index < len(self._history):
            self._history[index].metadata["read"] = True
            return True
        return False

    async def get_unread(self) -> List[Notification]:
        """Get unread notifications."""
        return [
            n for n in self._history
            if not n.metadata.get("read", False)
        ]


class DesktopNotifier:
    """Desktop notification handler."""

    async def send(self, notification: Notification) -> bool:
        """Send desktop notification."""
        # Simulate desktop notification
        # In production, would use platform-specific APIs
        logger.info(f"Desktop: {notification.title} - {notification.message}")
        return True


class MobileNotifier:
    """Mobile notification handler."""

    async def send(self, notification: Notification) -> bool:
        """Send mobile notification."""
        # Simulate mobile push
        logger.info(f"Mobile: {notification.title} - {notification.message}")
        return True


class SoundNotifier:
    """Sound notification handler."""

    async def play(self, notification: Notification) -> bool:
        """Play notification sound."""
        # Simulate sound playback
        # Would use system audio API
        logger.debug(f"Sound: {notification.type.value}")
        return True


__all__ = [
    "NotificationPriority",
    "NotificationType",
    "Notification",
    "NotificationConfig",
    "NotificationManager",
    "DesktopNotifier",
    "MobileNotifier",
    "SoundNotifier",
]