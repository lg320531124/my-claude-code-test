"""Notification Service - Send notifications."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class NotificationType(Enum):
    """Notification types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"
    CUSTOM = "custom"


class NotificationChannel(Enum):
    """Notification channels."""
    TERMINAL = "terminal"
    DESKTOP = "desktop"
    SOUND = "sound"
    WEBHOOK = "webhook"
    SLACK = "slack"
    EMAIL = "email"


@dataclass
class Notification:
    """Notification data."""
    type: NotificationType
    title: str
    message: str
    timestamp: datetime
    channel: NotificationChannel = NotificationChannel.TERMINAL
    duration: float = 5.0
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    read: bool = False


@dataclass
class NotificationConfig:
    """Notification configuration."""
    enabled: bool = True
    channels: List[NotificationChannel] = field(
        default_factory=lambda: [NotificationChannel.TERMINAL]
    )
    sound_enabled: bool = False
    desktop_enabled: bool = False
    max_history: int = 100
    quiet_hours: Optional[tuple] = None


class NotificationService:
    """Service for sending notifications."""

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self._history: List[Notification] = []
        self._unread_count: int = 0
        self._callbacks: List[callable] = []

    async def send(
        self,
        type: NotificationType,
        title: str,
        message: str,
        channel: Optional[NotificationChannel] = None,
        duration: float = 5.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Send notification."""
        if not self.config.enabled:
            return Notification(
                type=type,
                title=title,
                message=message,
                timestamp=datetime.now(),
            )

        # Check quiet hours
        if self._is_quiet_hours():
            logger.debug("Quiet hours - notification suppressed")
            return Notification(
                type=type,
                title=title,
                message=message,
                timestamp=datetime.now(),
            )

        # Determine channel
        use_channel = channel or self.config.channels[0]

        notification = Notification(
            type=type,
            title=title,
            message=message,
            timestamp=datetime.now(),
            channel=use_channel,
            duration=duration,
            metadata=metadata or {},
        )

        # Send to channel
        await self._send_to_channel(notification)

        # Store in history
        self._history.append(notification)
        self._unread_count += 1

        # Trim history
        if len(self._history) > self.config.max_history:
            self._history = self._history[-self.config.max_history:]

        # Call callbacks
        await self._call_callbacks(notification)

        return notification

    def _is_quiet_hours(self) -> bool:
        """Check if current time is in quiet hours."""
        if not self.config.quiet_hours:
            return False

        start, end = self.config.quiet_hours
        now = datetime.now().hour

        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end

    async def _send_to_channel(
        self,
        notification: Notification
    ) -> None:
        """Send notification to channel."""
        channel = notification.channel

        if channel == NotificationChannel.TERMINAL:
            await self._send_terminal(notification)

        elif channel == NotificationChannel.DESKTOP:
            if self.config.desktop_enabled:
                await self._send_desktop(notification)

        elif channel == NotificationChannel.SOUND:
            if self.config.sound_enabled:
                await self._send_sound(notification)

        elif channel == NotificationChannel.WEBHOOK:
            await self._send_webhook(notification)

        elif channel == NotificationChannel.SLACK:
            await self._send_slack(notification)

    async def _send_terminal(
        self,
        notification: Notification
    ) -> None:
        """Send terminal notification."""
        # Use logger for terminal output
        level_map = {
            NotificationType.INFO: logger.info,
            NotificationType.SUCCESS: logger.info,
            NotificationType.WARNING: logger.warning,
            NotificationType.ERROR: logger.error,
        }

        log_func = level_map.get(notification.type, logger.info)
        log_func(f"[{notification.title}] {notification.message}")

    async def _send_desktop(
        self,
        notification: Notification
    ) -> None:
        """Send desktop notification."""
        # Would integrate with system notification API
        logger.debug(f"Desktop notification: {notification.title}")

    async def _send_sound(
        self,
        notification: Notification
    ) -> None:
        """Send sound notification."""
        # Would play notification sound
        logger.debug(f"Sound notification: {notification.type.value}")

    async def _send_webhook(
        self,
        notification: Notification
    ) -> None:
        """Send webhook notification."""
        # Would POST to webhook URL
        logger.debug(f"Webhook notification: {notification.title}")

    async def _send_slack(
        self,
        notification: Notification
    ) -> None:
        """Send Slack notification."""
        # Would use Slack API
        logger.debug(f"Slack notification: {notification.title}")

    async def _call_callbacks(
        self,
        notification: Notification
    ) -> None:
        """Call registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(notification)
                else:
                    callback(notification)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def info(
        self,
        title: str,
        message: str
    ) -> Notification:
        """Send info notification."""
        return await self.send(
            NotificationType.INFO,
            title,
            message
        )

    async def success(
        self,
        title: str,
        message: str
    ) -> Notification:
        """Send success notification."""
        return await self.send(
            NotificationType.SUCCESS,
            title,
            message
        )

    async def warning(
        self,
        title: str,
        message: str
    ) -> Notification:
        """Send warning notification."""
        return await self.send(
            NotificationType.WARNING,
            title,
            message
        )

    async def error(
        self,
        title: str,
        message: str
    ) -> Notification:
        """Send error notification."""
        return await self.send(
            NotificationType.ERROR,
            title,
            message
        )

    async def progress(
        self,
        title: str,
        message: str,
        progress: float
    ) -> Notification:
        """Send progress notification."""
        return await self.send(
            NotificationType.PROGRESS,
            title,
            message,
            metadata={"progress": progress}
        )

    async def get_history(
        self,
        limit: int = 50
    ) -> List[Notification]:
        """Get notification history."""
        return self._history[-limit:]

    async def get_unread(self) -> List[Notification]:
        """Get unread notifications."""
        return [n for n in self._history if not n.read]

    async def mark_read(
        self,
        notification: Notification
    ) -> None:
        """Mark notification as read."""
        notification.read = True
        self._unread_count = max(0, self._unread_count - 1)

    async def mark_all_read(self) -> int:
        """Mark all notifications as read."""
        count = self._unread_count

        for n in self._history:
            n.read = True

        self._unread_count = 0
        return count

    async def clear(self) -> int:
        """Clear notification history."""
        count = len(self._history)
        self._history.clear()
        self._unread_count = 0
        return count

    async def get_unread_count(self) -> int:
        """Get unread count."""
        return self._unread_count

    def register_callback(
        self,
        callback: callable
    ) -> None:
        """Register notification callback."""
        self._callbacks.append(callback)

    async def set_channels(
        self,
        channels: List[NotificationChannel]
    ) -> None:
        """Set notification channels."""
        self.config.channels = channels


__all__ = [
    "NotificationType",
    "NotificationChannel",
    "Notification",
    "NotificationConfig",
    "NotificationService",
]