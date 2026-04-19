"""MCP Subscription Handler - Listen for resource updates."""

from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from typing import Any, Callable, ClassVar, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class SubscriptionState(Enum):
    """Subscription state."""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


@dataclass
class ResourceUpdate:
    """Resource update event."""
    uri: str
    content: Any
    timestamp: float
    server_name: str
    update_type: str = "content_changed"  # content_changed, deleted, created


@dataclass
class SubscriptionInfo:
    """Information about a subscription."""
    id: str
    uri: str
    server_name: str
    state: SubscriptionState
    created_at: float
    last_notification: Optional[float] = None
    notification_count: int = 0
    callback: Optional[Callable] = None
    filter_pattern: Optional[str] = None


class SubscriptionManager:
    """Manage resource subscriptions."""

    def __init__(self):
        self.subscriptions: Dict[str, SubscriptionInfo] = {}
        self._uri_to_subs: Dict[str, List[str]] = defaultdict(list)
        self._listener_task: asyncio.Task | None = None
        self._running = False
        self._update_queue: asyncio.Queue = asyncio.Queue()
        self._on_update: Optional[Callable] = None
        self._sub_counter: int = 0

    async def start(self) -> None:
        """Start subscription listener."""
        if self._running:
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        """Stop subscription listener."""
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        # Close all subscriptions
        for sub_info in self.subscriptions.values():
            sub_info.state = SubscriptionState.CLOSED

    async def _listen_loop(self) -> None:
        """Main listener loop."""
        while self._running:
            try:
                # Wait for updates
                update = await asyncio.wait_for(
                    self._update_queue.get(),
                    timeout=30.0,
                )
                await self._process_update(update)
            except asyncio.TimeoutError:
                # No updates, continue listening
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                continue

    async def _process_update(self, update: ResourceUpdate) -> None:
        """Process a resource update."""
        # Find subscriptions for this URI
        sub_ids = self._uri_to_subs.get(update.uri, [])

        for sub_id in sub_ids:
            sub_info = self.subscriptions.get(sub_id)
            if not sub_info or sub_info.state != SubscriptionState.ACTIVE:
                continue

            # Check filter pattern
            if sub_info.filter_pattern and not self._matches_filter(
                update.content, sub_info.filter_pattern
            ):
                continue

            # Notify subscriber
            if sub_info.callback:
                try:
                    await self._notify(sub_info, update)
                except Exception:
                    # Mark subscription as problematic but keep it
                    pass

            # Update stats
            sub_info.last_notification = time.time()
            sub_info.notification_count += 1

        # Global callback
        if self._on_update:
            self._on_update(update)

    async def _notify(self, sub_info: SubscriptionInfo, update: ResourceUpdate) -> None:
        """Notify subscriber of update."""
        if asyncio.iscoroutinefunction(sub_info.callback):
            await sub_info.callback(update)
        else:
            sub_info.callback(update)

    def _matches_filter(self, content: Any, pattern: str) -> bool:
        """Check if content matches filter pattern."""
        # Simple pattern matching
        if isinstance(content, str):
            return pattern in content
        elif isinstance(content, dict):
            return pattern in str(content)
        return True

    def subscribe(
        self,
        uri: str,
        callback: Callable,
        server_name: Optional[str] = None,
        filter_pattern: Optional[str] = None,
    ) -> str:
        """Subscribe to resource updates."""
        self._sub_counter += 1
        sub_id = f"sub_{self._sub_counter}"

        sub_info = SubscriptionInfo(
            id=sub_id,
            uri=uri,
            server_name=server_name or "",
            state=SubscriptionState.ACTIVE,
            created_at=time.time(),
            callback=callback,
            filter_pattern=filter_pattern,
        )

        self.subscriptions[sub_id] = sub_info
        self._uri_to_subs[uri].append(sub_id)

        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Cancel a subscription."""
        sub_info = self.subscriptions.get(subscription_id)
        if not sub_info:
            return False

        sub_info.state = SubscriptionState.CLOSED

        # Remove from URI mapping
        if sub_info.uri in self._uri_to_subs:
            self._uri_to_subs[sub_info.uri] = [
                sid for sid in self._uri_to_subs[sub_info.uri]
                if sid != subscription_id
            ]

        return True

    def pause(self, subscription_id: str) -> bool:
        """Pause a subscription."""
        sub_info = self.subscriptions.get(subscription_id)
        if sub_info and sub_info.state == SubscriptionState.ACTIVE:
            sub_info.state = SubscriptionState.PAUSED
            return True
        return False

    def resume(self, subscription_id: str) -> bool:
        """Resume a paused subscription."""
        sub_info = self.subscriptions.get(subscription_id)
        if sub_info and sub_info.state == SubscriptionState.PAUSED:
            sub_info.state = SubscriptionState.ACTIVE
            return True
        return False

    def push_update(self, update: ResourceUpdate) -> None:
        """Push a resource update."""
        self._update_queue.put_nowait(update)

    async def wait_for_update(
        self,
        uri: str,
        timeout: float = 30.0,
    ) -> ResourceUpdate | None:
        """Wait for a specific resource update."""
        updates_seen = []

        # Create a temporary queue
        temp_queue: asyncio.Queue = asyncio.Queue()

        # Temporary callback
        def temp_callback(update: ResourceUpdate) -> None:
            temp_queue.put_nowait(update)

        # Subscribe temporarily
        sub_id = self.subscribe(uri, temp_callback)

        try:
            update = await asyncio.wait_for(temp_queue.get(), timeout=timeout)
            return update
        except asyncio.TimeoutError:
            return None
        finally:
            self.unsubscribe(sub_id)

    def get_subscriptions_for_uri(self, uri: str) -> List[SubscriptionInfo]:
        """Get all subscriptions for a URI."""
        sub_ids = self._uri_to_subs.get(uri, [])
        return [
            self.subscriptions[sid]
            for sid in sub_ids
            if sid in self.subscriptions
        ]

    def get_active_subscriptions(self) -> List[SubscriptionInfo]:
        """Get all active subscriptions."""
        return [
            sub for sub in self.subscriptions.values()
            if sub.state == SubscriptionState.ACTIVE
        ]

    def get_stats(self) -> dict:
        """Get subscription statistics."""
        active = sum(1 for s in self.subscriptions.values() if s.state == SubscriptionState.ACTIVE)
        paused = sum(1 for s in self.subscriptions.values() if s.state == SubscriptionState.PAUSED)

        total_notifications = sum(s.notification_count for s in self.subscriptions.values())

        return {
            "total_subscriptions": len(self.subscriptions),
            "active": active,
            "paused": paused,
            "total_notifications": total_notifications,
            "unique_uris": len(self._uri_to_subs),
        }

    def set_update_callback(self, callback: Callable) -> None:
        """Set global update callback."""
        self._on_update = callback


class MCPSubscriptionClient:
    """Client for MCP subscriptions."""

    def __init__(self, connection: Any):
        self.connection = connection
        self.subscription_manager = SubscriptionManager()
        self._active_server_subs: Dict[str, List[str]] = {}

    async def start(self) -> None:
        """Start subscription client."""
        await self.subscription_manager.start()

        # Subscribe to server notifications
        await self._setup_server_subscriptions()

    async def stop(self) -> None:
        """Stop subscription client."""
        await self.subscription_manager.stop()

    async def _setup_server_subscriptions(self) -> None:
        """Set up server-side subscriptions."""
        # Subscribe to all resources on the server
        if hasattr(self.connection, "resources"):
            for resource in self.connection.resources:
                uri = resource.get("uri", "")
                if uri:
                    # Send subscribe request to server
                    await self._send_subscribe(uri)

    async def _send_subscribe(self, uri: str) -> bool:
        """Send subscribe request to MCP server."""
        if hasattr(self.connection, "_send_request"):
            response = await self.connection._send_request(
                "resources/subscribe",
                {"uri": uri},
            )
            return response and "result" in response
        return False

    async def _send_unsubscribe(self, uri: str) -> bool:
        """Send unsubscribe request."""
        if hasattr(self.connection, "_send_request"):
            response = await self.connection._send_request(
                "resources/unsubscribe",
                {"uri": uri},
            )
            return response and "result" in response
        return False

    def subscribe(
        self,
        uri: str,
        callback: Callable,
        filter_pattern: Optional[str] = None,
    ) -> str:
        """Subscribe to a resource."""
        return self.subscription_manager.subscribe(
            uri,
            callback,
            server_name=self.connection.name if hasattr(self.connection, "name") else "",
            filter_pattern=filter_pattern,
        )

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a resource."""
        return self.subscription_manager.unsubscribe(subscription_id)

    async def handle_notification(self, notification: dict) -> None:
        """Handle incoming notification from server."""
        method = notification.get("method", "")

        if method == "notifications/resources/updated":
            params = notification.get("params", {})
            uri = params.get("uri", "")

            # Fetch updated content
            content = await self._fetch_content(uri)

            # Push update
            update = ResourceUpdate(
                uri=uri,
                content=content,
                timestamp=time.time(),
                server_name=self.connection.name if hasattr(self.connection, "name") else "",
            )
            self.subscription_manager.push_update(update)

    async def _fetch_content(self, uri: str) -> Any:
        """Fetch content for updated resource."""
        if hasattr(self.connection, "read_resource"):
            result = await self.connection.read_resource(uri)
            return result.get("content")
        return None

    def get_stats(self) -> dict:
        """Get subscription stats."""
        return self.subscription_manager.get_stats()


# Global subscription manager
_subscription_manager: Optional[SubscriptionManager] = None


def get_subscription_manager() -> SubscriptionManager:
    """Get global subscription manager."""
    global _subscription_manager
    if _subscription_manager is None:
        _subscription_manager = SubscriptionManager()
    return _subscription_manager


async def start_subscriptions() -> None:
    """Start global subscription listener."""
    manager = get_subscription_manager()
    await manager.start()


async def stop_subscriptions() -> None:
    """Stop global subscription listener."""
    manager = get_subscription_manager()
    await manager.stop()


__all__ = [
    "SubscriptionState",
    "ResourceUpdate",
    "SubscriptionInfo",
    "SubscriptionManager",
    "MCPSubscriptionClient",
    "get_subscription_manager",
    "start_subscriptions",
    "stop_subscriptions",
]
