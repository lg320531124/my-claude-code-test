"""Tests for notification service."""

import pytest
from src.cc.services.notification_v2 import (
    NotificationService,
    NotificationConfig,
    NotificationType,
    NotificationChannel,
    Notification,
)


@pytest.mark.asyncio
async def test_notification_service_init():
    """Test notification service initialization."""
    service = NotificationService()
    assert service.config is not None


@pytest.mark.asyncio
async def test_send_notification():
    """Test sending notification."""
    service = NotificationService()

    notification = await service.send(
        NotificationType.INFO,
        "Test Title",
        "Test message"
    )

    assert notification.type == NotificationType.INFO
    assert notification.title == "Test Title"


@pytest.mark.asyncio
async def test_info_notification():
    """Test info notification."""
    service = NotificationService()

    notification = await service.info("Info", "Info message")
    assert notification.type == NotificationType.INFO


@pytest.mark.asyncio
async def test_success_notification():
    """Test success notification."""
    service = NotificationService()

    notification = await service.success("Success", "Success message")
    assert notification.type == NotificationType.SUCCESS


@pytest.mark.asyncio
async def test_warning_notification():
    """Test warning notification."""
    service = NotificationService()

    notification = await service.warning("Warning", "Warning message")
    assert notification.type == NotificationType.WARNING


@pytest.mark.asyncio
async def test_error_notification():
    """Test error notification."""
    service = NotificationService()

    notification = await service.error("Error", "Error message")
    assert notification.type == NotificationType.ERROR


@pytest.mark.asyncio
async def test_progress_notification():
    """Test progress notification."""
    service = NotificationService()

    notification = await service.progress("Progress", "Processing", 0.5)
    assert notification.type == NotificationType.PROGRESS
    assert notification.metadata.get("progress") == 0.5


@pytest.mark.asyncio
async def test_get_history():
    """Test getting history."""
    service = NotificationService()

    await service.info("Test1", "Message1")
    await service.info("Test2", "Message2")

    history = await service.get_history()
    assert len(history) == 2


@pytest.mark.asyncio
async def test_get_unread():
    """Test getting unread."""
    service = NotificationService()

    await service.info("Test", "Message")

    unread = await service.get_unread()
    assert len(unread) == 1


@pytest.mark.asyncio
async def test_mark_read():
    """Test marking read."""
    service = NotificationService()

    notification = await service.info("Test", "Message")
    await service.mark_read(notification)

    assert notification.read is True


@pytest.mark.asyncio
async def test_mark_all_read():
    """Test marking all read."""
    service = NotificationService()

    await service.info("Test1", "Message1")
    await service.info("Test2", "Message2")

    count = await service.mark_all_read()
    assert count == 2

    unread = await service.get_unread()
    assert len(unread) == 0


@pytest.mark.asyncio
async def test_clear():
    """Test clearing history."""
    service = NotificationService()

    await service.info("Test", "Message")
    count = await service.clear()

    assert count == 1
    history = await service.get_history()
    assert len(history) == 0


@pytest.mark.asyncio
async def test_get_unread_count():
    """Test getting unread count."""
    service = NotificationService()

    await service.info("Test1", "Message1")
    await service.info("Test2", "Message2")

    count = await service.get_unread_count()
    assert count == 2


@pytest.mark.asyncio
async def test_notification_config():
    """Test notification config."""
    config = NotificationConfig(
        enabled=True,
        sound_enabled=False,
        max_history=50,
    )

    assert config.enabled is True
    assert config.max_history == 50


@pytest.mark.asyncio
async def test_notification_type_enum():
    """Test notification type enum."""
    assert NotificationType.INFO.value == "info"
    assert NotificationType.ERROR.value == "error"


@pytest.mark.asyncio
async def test_notification_channel_enum():
    """Test notification channel enum."""
    assert NotificationChannel.TERMINAL.value == "terminal"
    assert NotificationChannel.DESKTOP.value == "desktop"


@pytest.mark.asyncio
async def test_register_callback():
    """Test registering callback."""
    service = NotificationService()

    callbacks = []

    def callback(n):
        callbacks.append(n)

    service.register_callback(callback)

    await service.info("Test", "Message")

    assert len(callbacks) == 1