"""MCP (Model Context Protocol) module."""

from __future__ import annotations
from .client import (
    MCPConnection,
    MCPManager,
    MCPToolWrapper,
    get_mcp_manager,
    initialize_mcp,
)
from .server import (
    MCPServerProcess,
    MCPResourceHandler,
    MCPToolRegistry,
    get_registry,
    start_mcp_server,
    stop_mcp_server,
    restart_mcp_server,
    list_mcp_servers,
    discover_mcp_tools,
    show_mcp_status,
    show_mcp_tools,
    call_mcp_tool,
    read_mcp_resource,
)
from .resources import (
    MCPResource,
    MCPResourceCache,
    MCPSubscription,
    MCPResourceManager,
    ResourceTemplate,
    ResourceRegistry,
    get_resource_manager,
)
from .health import (
    ServerHealthStatus,
    HealthCheckResult,
    ServerHealthConfig,
    MCPHealthMonitor,
    MCPAutoRecovery,
    MCPServerRegistry,
    get_health_monitor,
    start_health_monitoring,
    stop_health_monitoring,
)
from .subscriptions import (
    SubscriptionState,
    ResourceUpdate,
    SubscriptionInfo,
    SubscriptionManager,
    MCPSubscriptionClient,
    get_subscription_manager,
    start_subscriptions,
    stop_subscriptions,
)

__all__ = [
    # Client
    "MCPConnection",
    "MCPManager",
    "MCPToolWrapper",
    "get_mcp_manager",
    "initialize_mcp",
    # Server
    "MCPServerProcess",
    "MCPResourceHandler",
    "MCPToolRegistry",
    "get_registry",
    "start_mcp_server",
    "stop_mcp_server",
    "restart_mcp_server",
    "list_mcp_servers",
    "discover_mcp_tools",
    "show_mcp_status",
    "show_mcp_tools",
    "call_mcp_tool",
    "read_mcp_resource",
    # Resources
    "MCPResource",
    "MCPResourceCache",
    "MCPSubscription",
    "MCPResourceManager",
    "ResourceTemplate",
    "ResourceRegistry",
    "get_resource_manager",
    # Health
    "ServerHealthStatus",
    "HealthCheckResult",
    "ServerHealthConfig",
    "MCPHealthMonitor",
    "MCPAutoRecovery",
    "MCPServerRegistry",
    "get_health_monitor",
    "start_health_monitoring",
    "stop_health_monitoring",
    # Subscriptions
    "SubscriptionState",
    "ResourceUpdate",
    "SubscriptionInfo",
    "SubscriptionManager",
    "MCPSubscriptionClient",
    "get_subscription_manager",
    "start_subscriptions",
    "stop_subscriptions",
]
