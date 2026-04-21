"""MCP Tools - MCP resource and authentication tools."""

from __future__ import annotations
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class McpListInput(ToolInput):
    """Input for McpList."""
    server_name: str = ""


class McpListTool(ToolDef):
    """List MCP resources."""

    name: ClassVar[str] = "ListMcpResources"
    description: ClassVar[str] = "List resources from MCP server"
    input_schema: ClassVar[type] = McpListInput

    async def execute(self, input: McpListInput, ctx: ToolUseContext) -> ToolResult:
        """List MCP resources."""
        from ..services.mcp import get_mcp_manager

        manager = get_mcp_manager()

        if input.server_name:
            server = manager.get_server(input.server_name)
            if not server:
                return ToolResult(content=f"Server not found: {input.server_name}", is_error=True)
            resources = await server.list_resources()
        else:
            resources = []
            for server in manager.get_connected_servers():
                resources.extend(await server.list_resources())

        lines = []
        for r in resources:
            lines.append(f"- {r.uri}: {r.name}")

        return ToolResult(content="\n".join(lines) if lines else "No resources found")


class McpReadInput(ToolInput):
    """Input for McpRead."""
    uri: str


class McpReadTool(ToolDef):
    """Read MCP resource."""

    name: ClassVar[str] = "ReadMcpResource"
    description: ClassVar[str] = "Read a resource from MCP server"
    input_schema: ClassVar[type] = McpReadInput

    async def execute(self, input: McpReadInput, ctx: ToolUseContext) -> ToolResult:
        """Read MCP resource."""
        from ..services.mcp import get_mcp_manager

        manager = get_mcp_manager()

        for server in manager.get_connected_servers():
            try:
                content = await server.read_resource(input.uri)
                return ToolResult(content=content, metadata={"uri": input.uri})
            except Exception:
                continue

        return ToolResult(content=f"Resource not found: {input.uri}", is_error=True)


class McpAuthInput(ToolInput):
    """Input for McpAuth."""
    server_name: str
    auth_type: str = "oauth"  # oauth, api_key, basic


class McpAuthTool(ToolDef):
    """Authenticate MCP server."""

    name: ClassVar[str] = "McpAuth"
    description: ClassVar[str] = "Authenticate with MCP server"
    input_schema: ClassVar[type] = McpAuthInput

    async def execute(self, input: McpAuthInput, ctx: ToolUseContext) -> ToolResult:
        """Authenticate MCP server."""
        from ..services.oauth import get_oauth_manager

        oauth = get_oauth_manager()

        if input.auth_type == "oauth":
            # Start OAuth flow
            auth_url = await oauth.get_auth_url(input.server_name)
            return ToolResult(
                content=f"Please visit: {auth_url}\nThen run: McpAuth {input.server_name} --complete",
                metadata={"auth_url": auth_url}
            )

        return ToolResult(content="Authentication initiated", metadata={"server": input.server_name})


__all__ = ["McpListTool", "McpReadTool", "McpAuthTool"]