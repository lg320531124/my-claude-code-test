"""Tests for MCP Subscriptions."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cc.mcp.subscriptions import (
    SubscriptionState,
    ResourceUpdate,
    SubscriptionInfo,
    SubscriptionManager,
    MCPSubscriptionClient,
    get_subscription_manager,
    start_subscriptions,
    stop_subscriptions,
)


class TestSubscriptionState:
    """Test SubscriptionState enum."""

    def test_all_states(self):
        """Test all subscription states exist."""
        states = [
            SubscriptionState.ACTIVE,
            SubscriptionState.PAUSED,
            SubscriptionState.CLOSED,
        ]
        for state in states:
            assert isinstance(state.value, str)


class TestResourceUpdate:
    """Test ResourceUpdate dataclass."""

    def test_create_update(self):
        """Test creating resource update."""
        update = ResourceUpdate(
            uri="file:///test.txt",
            content="Hello World",
            timestamp=100.0,
            server_name="test_server",
        )
        assert update.uri == "file:///test.txt"
        assert update.content == "Hello World"
        assert update.timestamp == 100.0
        assert update.server_name == "test_server"
        assert update.update_type == "content_changed"

    def test_update_with_type(self):
        """Test update with custom type."""
        update = ResourceUpdate(
            uri="file:///test.txt",
            content=None,
            timestamp=100.0,
            server_name="test_server",
            update_type="deleted",
        )
        assert update.update_type == "deleted"


class TestSubscriptionInfo:
    """Test SubscriptionInfo dataclass."""

    def test_create_info(self):
        """Test creating subscription info."""
        info = SubscriptionInfo(
            id="sub_1",
            uri="file:///test.txt",
            server_name="server1",
            state=SubscriptionState.ACTIVE,
            created_at=100.0,
        )
        assert info.id == "sub_1"
        assert info.uri == "file:///test.txt"
        assert info.state == SubscriptionState.ACTIVE
        assert info.notification_count == 0
        assert info.last_notification is None


class TestSubscriptionManager:
    """Test SubscriptionManager class."""

    def test_init(self):
        """Test manager initialization."""
        manager = SubscriptionManager()
        assert manager.subscriptions == {}
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop."""
        manager = SubscriptionManager()
        await manager.start()
        assert manager._running is True
        assert manager._listener_task is not None

        await manager.stop()
        assert manager._running is False
        assert manager._listener_task is None

    def test_subscribe(self):
        """Test subscribing."""
        manager = SubscriptionManager()
        callback = MagicMock()

        sub_id = manager.subscribe("file:///test.txt", callback)
        assert sub_id.startswith("sub_")
        assert sub_id in manager.subscriptions
        assert manager.subscriptions[sub_id].state == SubscriptionState.ACTIVE

    def test_subscribe_with_filter(self):
        """Test subscribing with filter."""
        manager = SubscriptionManager()
        callback = MagicMock()

        sub_id = manager.subscribe(
            "file:///test.txt",
            callback,
            server_name="server1",
            filter_pattern="error",
        )
        info = manager.subscriptions[sub_id]
        assert info.filter_pattern == "error"
        assert info.server_name == "server1"

    def test_unsubscribe(self):
        """Test unsubscribing."""
        manager = SubscriptionManager()
        callback = MagicMock()

        sub_id = manager.subscribe("file:///test.txt", callback)
        result = manager.unsubscribe(sub_id)
        assert result is True
        assert manager.subscriptions[sub_id].state == SubscriptionState.CLOSED

    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing nonexistent."""
        manager = SubscriptionManager()
        result = manager.unsubscribe("invalid_id")
        assert result is False

    def test_pause_resume(self):
        """Test pause and resume."""
        manager = SubscriptionManager()
        callback = MagicMock()

        sub_id = manager.subscribe("file:///test.txt", callback)

        result = manager.pause(sub_id)
        assert result is True
        assert manager.subscriptions[sub_id].state == SubscriptionState.PAUSED

        result = manager.resume(sub_id)
        assert result is True
        assert manager.subscriptions[sub_id].state == SubscriptionState.ACTIVE

    def test_pause_nonexistent(self):
        """Test pausing nonexistent."""
        manager = SubscriptionManager()
        result = manager.pause("invalid_id")
        assert result is False

    def test_push_update(self):
        """Test pushing update."""
        manager = SubscriptionManager()
        update = ResourceUpdate(
            uri="file:///test.txt",
            content="new content",
            timestamp=100.0,
            server_name="server1",
        )

        manager.push_update(update)
        # Update should be in queue
        assert manager._update_queue.qsize() == 1

    def test_get_subscriptions_for_uri(self):
        """Test getting subscriptions for URI."""
        manager = SubscriptionManager()
        callback = MagicMock()

        sub_id1 = manager.subscribe("file:///a.txt", callback)
        sub_id2 = manager.subscribe("file:///a.txt", callback)
        sub_id3 = manager.subscribe("file:///b.txt", callback)

        subs = manager.get_subscriptions_for_uri("file:///a.txt")
        assert len(subs) == 2

    def test_get_active_subscriptions(self):
        """Test getting active subscriptions."""
        manager = SubscriptionManager()
        callback = MagicMock()

        sub_id1 = manager.subscribe("file:///a.txt", callback)
        sub_id2 = manager.subscribe("file:///b.txt", callback)
        manager.pause(sub_id2)

        active = manager.get_active_subscriptions()
        assert len(active) == 1
        assert active[0].id == sub_id1

    def test_get_stats(self):
        """Test getting stats."""
        manager = SubscriptionManager()
        callback = MagicMock()

        manager.subscribe("file:///a.txt", callback)
        manager.subscribe("file:///b.txt", callback)
        manager.subscribe("file:///a.txt", callback)

        stats = manager.get_stats()
        assert stats["total_subscriptions"] == 3
        assert stats["active"] == 3
        assert stats["unique_uris"] == 2

    def test_set_update_callback(self):
        """Test setting update callback."""
        manager = SubscriptionManager()
        manager.set_update_callback(lambda u: None)
        assert manager._on_update is not None

    def test_matches_filter(self):
        """Test filter matching."""
        manager = SubscriptionManager()

        # String content
        assert manager._matches_filter("hello world", "world")
        assert not manager._matches_filter("hello world", "goodbye")

        # Dict content
        assert manager._matches_filter({"key": "value"}, "value")

        # Other content - always matches
        assert manager._matches_filter(123, "anything")

    @pytest.mark.asyncio
    async def test_process_update(self):
        """Test processing update."""
        manager = SubscriptionManager()

        callback = AsyncMock()
        sub_id = manager.subscribe("file:///test.txt", callback)

        update = ResourceUpdate(
            uri="file:///test.txt",
            content="new content",
            timestamp=100.0,
            server_name="server1",
        )

        await manager._process_update(update)
        callback.assert_called_once_with(update)

        # Check stats updated
        info = manager.subscriptions[sub_id]
        assert info.notification_count == 1
        assert info.last_notification is not None

    @pytest.mark.asyncio
    async def test_process_update_paused(self):
        """Test processing update for paused subscription."""
        manager = SubscriptionManager()

        callback = AsyncMock()
        sub_id = manager.subscribe("file:///test.txt", callback)
        manager.pause(sub_id)

        update = ResourceUpdate(
            uri="file:///test.txt",
            content="new content",
            timestamp=100.0,
            server_name="server1",
        )

        await manager._process_update(update)
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_update_filtered(self):
        """Test processing update with filter."""
        manager = SubscriptionManager()

        callback = AsyncMock()
        sub_id = manager.subscribe(
            "file:///test.txt",
            callback,
            filter_pattern="error",
        )

        # Matching update
        update_match = ResourceUpdate(
            uri="file:///test.txt",
            content="error: something failed",
            timestamp=100.0,
            server_name="server1",
        )
        await manager._process_update(update_match)
        callback.assert_called_once()

        # Non-matching update
        callback.reset_mock()
        update_no_match = ResourceUpdate(
            uri="file:///test.txt",
            content="success: everything ok",
            timestamp=100.0,
            server_name="server1",
        )
        await manager._process_update(update_no_match)
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_wait_for_update(self):
        """Test waiting for update."""
        manager = SubscriptionManager()

        # Push update after subscribe
        async def push_later():
            await asyncio.sleep(0.1)
            update = ResourceUpdate(
                uri="file:///test.txt",
                content="new content",
                timestamp=100.0,
                server_name="server1",
            )
            manager.push_update(update)
            await manager._process_update(update)

        task = asyncio.create_task(push_later())

        update = await manager.wait_for_update("file:///test.txt", timeout=1.0)
        assert update is not None
        assert update.content == "new content"

        await task

    @pytest.mark.asyncio
    async def test_wait_for_update_timeout(self):
        """Test waiting for update with timeout."""
        manager = SubscriptionManager()

        update = await manager.wait_for_update("file:///test.txt", timeout=0.1)
        assert update is None


class TestMCPSubscriptionClient:
    """Test MCPSubscriptionClient class."""

    def test_init(self):
        """Test client initialization."""
        connection = MagicMock()
        client = MCPSubscriptionClient(connection)
        assert client.connection == connection
        assert client.subscription_manager is not None

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop."""
        connection = MagicMock()
        client = MCPSubscriptionClient(connection)

        await client.start()
        assert client.subscription_manager._running is True

        await client.stop()
        assert client.subscription_manager._running is False

    def test_subscribe(self):
        """Test subscribing through client."""
        connection = MagicMock()
        connection.name = "test_server"
        client = MCPSubscriptionClient(connection)

        callback = MagicMock()
        sub_id = client.subscribe("file:///test.txt", callback)
        assert sub_id.startswith("sub_")

    def test_unsubscribe(self):
        """Test unsubscribing through client."""
        connection = MagicMock()
        client = MCPSubscriptionClient(connection)

        callback = MagicMock()
        sub_id = client.subscribe("file:///test.txt", callback)
        result = client.unsubscribe(sub_id)
        assert result is True

    def test_get_stats(self):
        """Test getting stats through client."""
        connection = MagicMock()
        client = MCPSubscriptionClient(connection)

        stats = client.get_stats()
        assert "total_subscriptions" in stats

    @pytest.mark.asyncio
    async def test_handle_notification(self):
        """Test handling notification."""
        connection = MagicMock()
        connection.name = "test_server"
        connection.read_resource = AsyncMock(return_value={"content": "updated"})

        client = MCPSubscriptionClient(connection)
        await client.start()

        callback = AsyncMock()
        sub_id = client.subscribe("file:///test.txt", callback)

        # Handle notification
        notification = {
            "method": "notifications/resources/updated",
            "params": {"uri": "file:///test.txt"},
        }
        await client.handle_notification(notification)

        # Give time for processing
        await asyncio.sleep(0.1)


class TestGlobals:
    """Test global functions."""

    def test_get_subscription_manager(self):
        """Test getting global manager."""
        manager1 = get_subscription_manager()
        manager2 = get_subscription_manager()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_start_stop_subscriptions(self):
        """Test global start/stop functions."""
        await start_subscriptions()
        manager = get_subscription_manager()
        assert manager._running is True

        await stop_subscriptions()
        assert manager._running is False