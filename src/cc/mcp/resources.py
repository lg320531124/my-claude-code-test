"""MCP Resources - Resource access and caching."""

from __future__ import annotations
import asyncio
import json
import time
from typing import Any, Optional

from .client import MCPConnection


class MCPResource:
    """MCP resource wrapper."""

    def __init__(
        self,
        uri: str,
        name: str,
        description: str = "",
        mime_type: str = "text/plain",
    ):
        self.uri = uri
        self.name = name
        self.description = description
        self.mime_type = mime_type
        self.content: Optional[bytes] = None
        self.last_updated: float = 0

    async def fetch(self, connection: MCPConnection) -> bytes | None:
        """Fetch resource content."""
        result = await connection.read_resource(self.uri)

        if "content" in result:
            content = result["content"]
            if isinstance(content, str):
                self.content = content.encode()
            else:
                self.content = content
            self.last_updated = time.time()
            return self.content

        return None

    def to_text(self) -> Optional[str]:
        """Get content as text."""
        if self.content is None:
            return None

        try:
            return self.content.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def to_json(self) -> Any | None:
        """Parse content as JSON."""
        text = self.to_text()
        if text is None:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None


class MCPResourceCache:
    """Cache for MCP resources."""

    def __init__(self, ttl_seconds: float = 300.0):
        self.cache: Dict[str, MCPResource] = {}
        self.ttl = ttl_seconds

    async def get(
        self,
        uri: str,
        connection: MCPConnection,
        refresh: bool = False,
    ) -> MCPResource | None:
        """Get cached resource."""
        # Check cache
        cached = self.cache.get(uri)

        if cached and not refresh:
            # Check TTL
            if time.time() - cached.last_updated < self.ttl:
                return cached

        # Fetch fresh
        resource = MCPResource(uri, uri.split("/")[-1])
        content = await resource.fetch(connection)

        if content:
            self.cache[uri] = resource
            return resource

        return None

    def invalidate(self, uri: str) -> None:
        """Invalidate cached resource."""
        self.cache.pop(uri, None)

    def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "count": len(self.cache),
            "ttl": self.ttl,
            "resources": list(self.cache.keys()),
        }


class MCPSubscription:
    """MCP resource subscription."""

    def __init__(self, uri: str, callback: Any):
        self.uri = uri
        self.callback = callback
        self.active = True

    def notify(self, content: Any) -> None:
        """Notify subscriber."""
        if self.active and self.callback:
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._call_callback(content))
            except RuntimeError:
                # No running loop, call callback directly if synchronous
                try:
                    if not asyncio.iscoroutinefunction(self.callback):
                        self.callback(self.uri, content)
                except Exception:
                    pass

    async def _call_callback(self, content: Any) -> None:
        """Call callback."""
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(self.uri, content)
            else:
                self.callback(self.uri, content)
        except Exception:
            pass


class MCPResourceManager:
    """Manages MCP resources."""

    def __init__(self):
        self.cache = MCPResourceCache()
        self.subscriptions: Dict[str, List[MCPSubscription]] = {}
        self.connections: Dict[str, MCPConnection] = {}

    def register_connection(self, name: str, connection: MCPConnection) -> None:
        """Register a connection."""
        self.connections[name] = connection

    async def read(
        self,
        uri: str,
        server_name: Optional[str] = None,
        refresh: bool = False,
    ) -> MCPResource | None:
        """Read a resource."""
        # Find connection
        conn = None
        if server_name:
            conn = self.connections.get(server_name)
        else:
            # Try to infer from URI
            if uri.startswith("mcp://"):
                parts = uri.split("/")
                if len(parts) > 2:
                    server_name = parts[2]
                    conn = self.connections.get(server_name)

        if not conn:
            # Use first available connection
            conn = next(iter(self.connections.values()), None)

        if not conn:
            return None

        return await self.cache.get(uri, conn, refresh)

    def subscribe(self, uri: str, callback: Any) -> MCPSubscription:
        """Subscribe to resource updates."""
        sub = MCPSubscription(uri, callback)

        if uri not in self.subscriptions:
            self.subscriptions[uri] = []
        self.subscriptions[uri].append(sub)

        return sub

    def unsubscribe(self, subscription: MCPSubscription) -> None:
        """Unsubscribe from updates."""
        subscription.active = False

        if subscription.uri in self.subscriptions:
            self.subscriptions[subscription.uri] = [
                s for s in self.subscriptions[subscription.uri]
                if s != subscription
            ]

    def notify_update(self, uri: str, content: Any) -> None:
        """Notify subscribers of update."""
        subs = self.subscriptions.get(uri, [])
        for sub in subs:
            sub.notify(content)

    async def list_resources(self, server_name: str) -> List[dict]:
        """List resources from server."""
        conn = self.connections.get(server_name)
        if not conn:
            return []

        return conn.resources

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache.get_stats()


class ResourceTemplate:
    """Template for dynamic resources."""

    def __init__(self, template: str, handler: Any):
        self.template = template
        self.handler = handler

    def match(self, uri: str) -> dict | None:
        """Check if URI matches template."""
        # Simple template matching
        # Template: "file://{path}"
        # URI: "file:///home/user/test.txt"

        template_parts = self.template.split("/")
        uri_parts = uri.split("/")

        if len(template_parts) != len(uri_parts):
            return None

        params = {}
        for t_part, u_part in zip(template_parts, uri_parts):
            if t_part.startswith("{") and t_part.endswith("}"):
                param_name = t_part[1:-1]
                params[param_name] = u_part
            elif t_part != u_part:
                return None

        return params

    async def resolve(self, uri: str) -> Any:
        """Resolve resource from URI."""
        params = self.match(uri)
        if params is None:
            return None

        if asyncio.iscoroutinefunction(self.handler):
            return await self.handler(params)
        else:
            return self.handler(params)


class ResourceRegistry:
    """Registry for resource templates."""

    def __init__(self):
        self.templates: List[ResourceTemplate] = []

    def register(self, template: str, handler: Any) -> None:
        """Register template."""
        self.templates.append(ResourceTemplate(template, handler))

    async def resolve(self, uri: str) -> Any:
        """Resolve URI."""
        for template in self.templates:
            result = await template.resolve(uri)
            if result is not None:
                return result
        return None


# Global resource manager
_resource_manager: Optional[MCPResourceManager] = None


def get_resource_manager() -> MCPResourceManager:
    """Get global resource manager."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = MCPResourceManager()
    return _resource_manager
