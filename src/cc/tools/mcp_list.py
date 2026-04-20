"""ListMcpResourcesTool - List MCP resources.

Async tool for discovering MCP server resources.
"""

from __future__ import annotations
import asyncio
from typing import ClassVar, Dict, Any, Optional, Callable, List

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext


class ListMcpResourcesInput(ToolInput):
    """Input for ListMcpResourcesTool."""

    server_name: Optional[str] = Field(default=None, description="Specific server to query")


class McpResource(BaseModel):
    """MCP resource info."""

    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class ListMcpResourcesOutput(BaseModel):
    """Output schema for ListMcpResourcesTool."""

    resources: List[McpResource] = Field(default_factory=list)
    total: int = 0


class ListMcpResourcesTool(Tool):
    """List available MCP resources."""

    name: str = "ListMcpResources"
    input_schema: type = ListMcpResourcesInput
    max_result_size_chars: float = 50_000
    strict: bool = True

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """List MCP resources."""
        input_data = ListMcpResourcesInput.model_validate(args)

        resources = []

        # Query MCP clients from context
        if context.mcp_clients:
            for client in context.mcp_clients:
                if input_data.server_name:
                    # Filter by server name
                    if hasattr(client, 'name') and client.name != input_data.server_name:
                        continue

                # List resources from client (async)
                if hasattr(client, 'list_resources'):
                    try:
                        client_resources = await client.list_resources()
                        for r in client_resources:
                            resources.append(McpResource(
                                uri=r.get("uri", ""),
                                name=r.get("name", ""),
                                description=r.get("description"),
                                mime_type=r.get("mimeType"),
                            ))
                    except Exception as e:
                        # Skip failed clients
                        pass

        output = ListMcpResourcesOutput(
            resources=resources,
            total=len(resources),
        )

        return ToolResult(data=output)

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description."""
        server = input.get("server_name")
        if server:
            return f"List resources from {server}"
        return "List MCP resources"

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary."""
        return "List MCP resources"

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description."""
        return "Listing MCP resources"


def build_list_mcp_resources_tool() -> ListMcpResourcesTool:
    """Build ListMcpResourcesTool instance."""
    return ListMcpResourcesTool()


__all__ = ["ListMcpResourcesTool", "ListMcpResourcesInput", "ListMcpResourcesOutput", "McpResource", "build_list_mcp_resources_tool"]