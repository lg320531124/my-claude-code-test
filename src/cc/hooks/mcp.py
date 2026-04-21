"""Hook MCP - Async MCP connection hooks."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class MCPHookEvent(Enum):
    """MCP hook events."""
    SERVER_CONNECT = "server_connect"
    SERVER_DISCONNECT = "server_disconnect"
    SERVER_ERROR = "server_error"
    TOOL_DISCOVER = "tool_discover"
    TOOL_CALL = "tool_call"
    RESOURCE_ACCESS = "resource_access"
    PERMISSION_REQUEST = "permission_request"


@dataclass
class MCPHookContext:
    """MCP hook context."""
    event: MCPHookEvent
    server_name: str = ""
    tool_name: str = ""
    resource_uri: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: float = 0.0


class MCPHooks:
    """Hooks for MCP operations."""

    def __init__(self):
        self._hooks: Dict[MCPHookEvent, List[Callable]] = {}
        self._server_states: Dict[str, str] = {}  # server_name -> status
        self._tool_cache: Dict[str, List[Dict]] = {}  # server_name -> tools

    def register_hook(self, event: MCPHookEvent, hook: Callable) -> None:
        """Register hook for event."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(hook)

    async def trigger(self, context: MCPHookContext) -> List[Any]:
        """Trigger hooks for event."""
        results = []
        hooks = self._hooks.get(context.event, [])

        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    result = await hook(context)
                else:
                    result = hook(context)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})

        return results

    async def pre_connect(self, server_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Hook before server connect."""
        context = MCPHookContext(
            event=MCPHookEvent.SERVER_CONNECT,
            server_name=server_name,
            data=config,
        )

        results = await self.trigger(context)

        # Check if any hook blocked connection
        for result in results:
            if isinstance(result, dict) and result.get("block"):
                raise Exception(result.get("reason", "Blocked by hook"))

        self._server_states[server_name] = "connecting"
        return config

    async def post_connect(self, server_name: str, success: bool) -> None:
        """Hook after server connect."""
        self._server_states[server_name] = "connected" if success else "failed"

        context = MCPHookContext(
            event=MCPHookEvent.SERVER_CONNECT if success else MCPHookEvent.SERVER_ERROR,
            server_name=server_name,
            data={"success": success},
        )

        await self.trigger(context)

    async def pre_disconnect(self, server_name: str) -> bool:
        """Hook before disconnect."""
        context = MCPHookContext(
            event=MCPHookEvent.SERVER_DISCONNECT,
            server_name=server_name,
        )

        results = await self.trigger(context)

        # Check if any hook prevents disconnect
        for result in results:
            if isinstance(result, dict) and result.get("prevent"):
                return False

        return True

    async def post_disconnect(self, server_name: str) -> None:
        """Hook after disconnect."""
        self._server_states[server_name] = "disconnected"

        context = MCPHookContext(
            event=MCPHookEvent.SERVER_DISCONNECT,
            server_name=server_name,
        )

        await self.trigger(context)

    async def on_tool_discover(self, server_name: str, tools: List[Dict]) -> List[Dict]:
        """Hook on tool discovery."""
        # Filter tools
        filtered_tools = []

        for tool in tools:
            context = MCPHookContext(
                event=MCPHookEvent.TOOL_DISCOVER,
                server_name=server_name,
                tool_name=tool.get("name", ""),
                data=tool,
            )

            results = await self.trigger(context)

            # Check if tool should be included
            include = True
            for result in results:
                if isinstance(result, dict) and result.get("exclude"):
                    include = False
                    break

            if include:
                filtered_tools.append(tool)

        self._tool_cache[server_name] = filtered_tools
        return filtered_tools

    async def pre_tool_call(
        self,
        server_name: str,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Hook before tool call."""
        context = MCPHookContext(
            event=MCPHookEvent.TOOL_CALL,
            server_name=server_name,
            tool_name=tool_name,
            data=args,
        )

        results = await self.trigger(context)

        # Modify args if hooks return modifications
        modified_args = args.copy()
        for result in results:
            if isinstance(result, dict) and "args" in result:
                modified_args.update(result["args"])

        return modified_args

    async def post_tool_call(
        self,
        server_name: str,
        tool_name: str,
        result: Any,
    ) -> Any:
        """Hook after tool call."""
        context = MCPHookContext(
            event=MCPHookEvent.TOOL_CALL,
            server_name=server_name,
            tool_name=tool_name,
            data={"result": result},
        )

        results = await self.trigger(context)

        # Modify result if hooks return modifications
        for hook_result in results:
            if isinstance(hook_result, dict) and "result" in hook_result:
                result = hook_result["result"]

        return result

    async def pre_resource_access(
        self,
        server_name: str,
        uri: str,
    ) -> bool:
        """Hook before resource access."""
        context = MCPHookContext(
            event=MCPHookEvent.RESOURCE_ACCESS,
            server_name=server_name,
            resource_uri=uri,
        )

        results = await self.trigger(context)

        # Check if any hook blocks access
        for result in results:
            if isinstance(result, dict) and result.get("block"):
                return False

        return True

    async def on_permission_request(
        self,
        server_name: str,
        request: Dict[str, Any],
    ) -> str:
        """Hook on permission request."""
        context = MCPHookContext(
            event=MCPHookEvent.PERMISSION_REQUEST,
            server_name=server_name,
            data=request,
        )

        results = await self.trigger(context)

        # Return first decision from hooks
        for result in results:
            if isinstance(result, dict) and "decision" in result:
                return result["decision"]

        return "ask"  # Default to ask

    def get_server_states(self) -> Dict[str, str]:
        """Get all server states."""
        return self._server_states.copy()

    def get_server_tools(self, server_name: str) -> List[Dict]:
        """Get tools for server."""
        return self._tool_cache.get(server_name, [])


# Global hooks
_hooks: Optional[MCPHooks] = None


def get_mcp_hooks() -> MCPHooks:
    """Get global MCP hooks."""
    global _hooks
    if _hooks is None:
        _hooks = MCPHooks()
    return _hooks


__all__ = [
    "MCPHookEvent",
    "MCPHookContext",
    "MCPHooks",
    "get_mcp_hooks",
]