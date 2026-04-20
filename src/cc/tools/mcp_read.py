"""ReadMcpResourceTool - Read MCP resource content.

Async tool for reading content from MCP server resources.
"""

from __future__ import annotations
import asyncio
from typing import ClassVar, Dict, Any, Optional, Callable

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext


class ReadMcpResourceInput(ToolInput):
    """Input for ReadMcpResourceTool."""

    uri: str = Field(description="The resource URI to read")


class ReadMcpResourceOutput(BaseModel):
    """Output schema for ReadMcpResourceTool."""

    uri: str
    content: str
    mime_type: Optional[str] = None
    size: int = 0


class ReadMcpResourceTool(Tool):
    """Read content from an MCP resource."""

    name: str = "ReadMcpResource"
    input_schema: type = ReadMcpResourceInput
    max_result_size_chars: float = 100_000
    strict: bool = True

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Read MCP resource."""
        input_data = ReadMcpResourceInput.model_validate(args)

        content = ""
        mime_type = None

        # Query MCP clients from context
        if context.mcp_clients:
            for client in context.mcp_clients:
                # Try to read from this client (async)
                if hasattr(client, 'read_resource'):
                    try:
                        result = await client.read_resource(input_data.uri)
                        if result:
                            content = result.get("content", "")
                            mime_type = result.get("mimeType")
                            break
                    except Exception:
                        # Try next client
                        continue

        if not content:
            return ToolResult(
                data=ReadMcpResourceOutput(
                    uri=input_data.uri,
                    content="",
                    mime_type=mime_type,
                    size=0,
                ),
                is_error=True,
                error_message=f"Resource not found: {input_data.uri}",
            )

        output = ReadMcpResourceOutput(
            uri=input_data.uri,
            content=content,
            mime_type=mime_type,
            size=len(content),
        )

        return ToolResult(data=output)

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description."""
        uri = input.get("uri", "")
        return f"Read resource {uri}"

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary."""
        if not input:
            return None
        return f"Read: {input.get('uri', '')}"

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description."""
        return "Reading MCP resource"


def build_read_mcp_resource_tool() -> ReadMcpResourceTool:
    """Build ReadMcpResourceTool instance."""
    return ReadMcpResourceTool()


__all__ = ["ReadMcpResourceTool", "ReadMcpResourceInput", "ReadMcpResourceOutput", "build_read_mcp_resource_tool"]