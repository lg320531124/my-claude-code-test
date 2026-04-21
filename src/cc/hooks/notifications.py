"""Notifications Hook - Async notification handling."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Callable, Optional, List, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class NotificationLevel(Enum):
    """Notification levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


@dataclass
class NotificationMessage:
    """Notification message."""
    id: str
    level: NotificationLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    dismissible: bool = True
    persistent: bool = False
    timeout: Optional[float] = None  # Auto-dismiss timeout


class NotificationHook:
    """Async notifications hook."""

    def __init__(self):
        self._notifications: Dict[str, NotificationMessage] = {}
        self._subscribers: List[Callable] = []
        self._notification_id = 0
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None

    async def start_processor(self) -> None:
        """Start notification processor."""
        if self._processor_task is None:
            self._processor_task = asyncio.create_task(
                self._process_notifications()
            )

    async def stop_processor(self) -> None:
        """Stop notification processor."""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None

    async def _process_notifications(self) -> None:
        """Process notification queue."""
        while True:
            notification = await self._notification_queue.get()

            # Notify subscribers
            for subscriber in self._subscribers:
                try:
                    if asyncio.iscoroutinefunction(subscriber):
                        await subscriber(notification)
                    else:
                        subscriber(notification)
                except Exception:
                    pass

            # Auto-dismiss if timeout set
            if notification.timeout:
                await asyncio.sleep(notification.timeout)
                await self.dismiss(notification.id)

    async def notify(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        actions: List[Dict[str, Any]] = None,
        dismissible: bool = True,
        persistent: bool = False,
        timeout: Optional[float] = None,
    ) -> str:
        """Create notification.

        Args:
            title: Notification title
            message: Notification message
            level: Notification level
            actions: Optional actions (e.g., [{"label": "OK", "action": "dismiss"}])
            dismissible: Can be dismissed
            persistent: Won't auto-dismiss
            timeout: Auto-dismiss timeout in seconds

        Returns:
            Notification ID
        """
        self._notification_id += 1
        notification_id = f"notif_{self._notification_id}"

        notification = NotificationMessage(
            id=notification_id,
            level=level,
            title=title,
            message=message,
            actions=actions or [],
            dismissible=dismissible,
            persistent=persistent,
            timeout=timeout if not persistent else None,
        )

        self._notifications[notification_id] = notification
        await self._notification_queue.put(notification)

        return notification_id

    async def dismiss(self, notification_id: str) -> bool:
        """Dismiss notification.

        Args:
            notification_id: Notification ID

        Returns:
            True if dismissed
        """
        if notification_id in self._notifications:
            notification = self._notifications.pop(notification_id)

            # Notify subscribers of dismiss
            for subscriber in self._subscribers:
                try:
                    dismiss_event = {
                        "type": "dismiss",
                        "notification_id": notification_id,
                    }
                    if asyncio.iscoroutinefunction(subscriber):
                        await subscriber(dismiss_event)
                    else:
                        subscriber(dismiss_event)
                except Exception:
                    pass

            return True
        return False

    async def dismiss_all(self) -> int:
        """Dismiss all notifications.

        Returns:
            Number of dismissed notifications
        """
        count = len(self._notifications)
        for notification_id in list(self._notifications.keys()):
            await self.dismiss(notification_id)
        return count

    async def action(
        self,
        notification_id: str,
        action_id: str,
    ) -> bool:
        """Execute notification action.

        Args:
            notification_id: Notification ID
            action_id: Action ID

        Returns:
            True if action executed
        """
        if notification_id not in self._notifications:
            return False

        notification = self._notifications[notification_id]

        for action in notification.actions:
            if action.get("id") == action_id or action.get("label") == action_id:
                # Execute action callback if present
                callback = action.get("callback")
                if callback:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(notification)
                    else:
                        callback(notification)

                # Auto-dismiss if action dismisses
                if action.get("action") == "dismiss":
                    await self.dismiss(notification_id)

                return True

        return False

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to notifications.

        Args:
            callback: Function to call on notification
        """
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> bool:
        """Unsubscribe from notifications.

        Args:
            callback: Callback to remove

        Returns:
            True if removed
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            return True
        return False

    def get_notifications(self) -> List[NotificationMessage]:
        """Get all active notifications.

        Returns:
            List of notifications
        """
        return list(self._notifications.values())

    def get_notification(self, notification_id: str) -> Optional[NotificationMessage]:
        """Get specific notification.

        Args:
            notification_id: Notification ID

        Returns:
            Notification or None
        """
        return self._notifications.get(notification_id)


# Global notification hook
_notification_hook: Optional[NotificationHook] = None


def get_notification_hook() -> NotificationHook:
    """Get global notification hook."""
    global _notification_hook
    if _notification_hook is None:
        _notification_hook = NotificationHook()
    return _notification_hook


async def use_notifications() -> Dict[str, Any]:
    """Notifications hook for hooks module.

    Returns notification functions.
    """
    hook = get_notification_hook()

    return {
        "notify": hook.notify,
        "dismiss": hook.dismiss,
        "dismiss_all": hook.dismiss_all,
        "action": hook.action,
        "subscribe": hook.subscribe,
        "unsubscribe": hook.unsubscribe,
        "get_notifications": hook.get_notifications,
    }


__all__ = [
    "NotificationLevel",
    "NotificationMessage",
    "NotificationHook",
    "get_notification_hook",
    "use_notifications",
]