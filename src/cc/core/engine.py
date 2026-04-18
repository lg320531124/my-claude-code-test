"""Core Query Engine - LLM API calling loop."""

import asyncio
from typing import AsyncIterator

from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import MessageParam, ToolParam

from ..types.message import (
    AssistantMessage,
    ContentBlock,
    Message,
    ToolResultBlock,
    ToolResultMessage,
    UserMessage,
)
from ..types.tool import ToolDef, ToolResult, ToolUseContext
from ..types.permission import PermissionMode


class QueryEngine:
    """Core engine for LLM API calls with tool-use loop."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        tools: list[ToolDef] | None = None,
        system_prompt: str | None = None,
        permission_mode: PermissionMode = PermissionMode.DEFAULT,
        max_tokens: int = 8192,
        max_turns: int = 20,
    ):
        self.model = model
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.permission_mode = permission_mode
        self.max_tokens = max_tokens
        self.max_turns = max_turns

        # Initialize API client
        self.client = AsyncAnthropic()

    def _get_tool_schemas(self) -> list[ToolParam]:
        """Get tool schemas for API."""
        return [tool.get_api_schema() for tool in self.tools]

    def _get_tool_by_name(self, name: str) -> ToolDef | None:
        """Find tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    async def query(
        self,
        messages: list[Message],
        ctx: ToolUseContext,
    ) -> AsyncIterator[ContentBlock]:
        """
        Execute the query loop:
        1. Call LLM API
        2. Stream response
        3. If tool call, execute tool and continue
        4. Repeat until done or max turns
        """
        api_messages: list[MessageParam] = self._convert_messages(messages)
        turn_count = 0

        while turn_count < self.max_turns:
            turn_count += 1

            # Call API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=api_messages,
                tools=self._get_tool_schemas(),
            )

            # Process response blocks
            tool_calls: list[ToolResultMessage] = []

            for block in response.content:
                yield block

                if block.type == "tool_use":
                    # Execute tool
                    result = await self._execute_tool(block, ctx)
                    tool_calls.append(result)

            # Check if we need to continue
            if response.stop_reason != "tool_use":
                break

            # Add tool results to messages
            for tool_result in tool_calls:
                api_messages.append(self._convert_message(tool_result))

    async def _execute_tool(
        self,
        tool_use_block: ContentBlock,
        ctx: ToolUseContext,
    ) -> ToolResultMessage:
        """Execute a tool call."""
        tool = self._get_tool_by_name(tool_use_block.name)
        if tool is None:
            return ToolResultMessage(
                content=[
                    ToolResultBlock(
                        tool_use_id=tool_use_block.id,
                        content=f"Unknown tool: {tool_use_block.name}",
                        is_error=True,
                    )
                ]
            )

        try:
            input = tool.validate_input(tool_use_block.input)
            result = await tool.execute(input, ctx)
            return ToolResultMessage(
                content=[result.to_block(tool_use_block.id)]
            )
        except Exception as e:
            return ToolResultMessage(
                content=[
                    ToolResultBlock(
                        tool_use_id=tool_use_block.id,
                        content=f"Tool execution error: {e}",
                        is_error=True,
                    )
                ]
            )

    def _convert_messages(self, messages: list[Message]) -> list[MessageParam]:
        """Convert internal messages to API format."""
        result: list[MessageParam] = []
        for msg in messages:
            result.append(self._convert_message(msg))
        return result

    def _convert_message(self, msg: Message) -> MessageParam:
        """Convert single message to API format."""
        content: list[dict] = []
        for block in msg.content:
            if hasattr(block, "model_dump"):
                content.append(block.model_dump())
            else:
                content.append(dict(block))
        return {"role": msg.role, "content": content}