"""Core Query Engine - LLM API calling loop with streaming."""

import asyncio
from typing import AsyncIterator, Any

from ..services.api.client import APIClient, get_client
from ..types.message import (
    AssistantMessage,
    ContentBlock,
    Message,
    TextBlock,
    ToolResultBlock,
    ToolResultMessage,
    ToolUseBlock,
    UserMessage,
)
from ..types.tool import ToolDef, ToolResult, ToolUseContext
from ..types.permission import PermissionMode, PermissionResult, PermissionDecision


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
        base_url: str | None = None,
    ):
        self.model = model
        self.tools = tools or []
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.permission_mode = permission_mode
        self.max_tokens = max_tokens
        self.max_turns = max_turns

        # Initialize API client (supports compatible APIs)
        self.client = get_client(model=model, base_url=base_url)

        # Tool call tracking
        self._pending_tool_calls: dict[str, ToolUseBlock] = {}

    def _default_system_prompt(self) -> str:
        """Default system prompt."""
        return """You are Claude Code, a CLI coding assistant. You help users with:
- Reading, writing, and editing files
- Running shell commands
- Searching codebases
- Answering questions about code

Always be helpful, accurate, and follow the user's instructions carefully."""

    def _get_tool_schemas(self) -> list[dict]:
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
    ) -> AsyncIterator[ContentBlock | str]:
        """
        Execute the query loop with streaming:
        1. Call LLM API (streaming)
        2. Yield text as it arrives
        3. If tool call, check permission, execute, and continue
        4. Repeat until done or max turns
        """
        api_messages: list[dict] = self._convert_messages(messages)
        turn_count = 0

        while turn_count < self.max_turns:
            turn_count += 1

            # Stream response
            tool_calls: list[dict] = []
            text_buffer = ""
            current_tool: dict | None = None
            tool_input_buffer = ""

            async for event in self.client.create_message(
                messages=api_messages,
                tools=self._get_tool_schemas(),
                system=self.system_prompt,
                max_tokens=self.max_tokens,
                stream=True,
            ):
                event_type = event.get("type", "")

                if event_type == "text_delta":
                    text = event.get("text", "")
                    text_buffer += text
                    yield text

                elif event_type == "tool_use_start":
                    current_tool = {
                        "id": event.get("id"),
                        "name": event.get("name"),
                        "index": event.get("index"),
                    }
                    tool_input_buffer = ""

                elif event_type == "input_json_delta":
                    tool_input_buffer += event.get("partial_json", "")

                elif event_type == "message_stop":
                    # Finalize any pending tool call
                    if current_tool and tool_input_buffer:
                        import json
                        try:
                            tool_input = json.loads(tool_input_buffer)
                        except json.JSONDecodeError:
                            tool_input = {}
                        tool_calls.append({
                            "id": current_tool["id"],
                            "name": current_tool["name"],
                            "input": tool_input,
                        })
                    current_tool = None

            # Process tool calls
            if tool_calls:
                tool_results: list[dict] = []
                for tc in tool_calls:
                    result = await self._execute_tool_with_permission(tc, ctx)
                    tool_results.append(result)

                # Add tool results to messages and continue
                api_messages.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": text_buffer}] + [
                        {"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]}
                        for tc in tool_calls
                    ],
                })
                api_messages.append({
                    "role": "user",
                    "content": tool_results,
                })
                continue

            # No tool calls - we're done
            break

    async def _execute_tool_with_permission(
        self,
        tool_call: dict,
        ctx: ToolUseContext,
    ) -> dict:
        """Execute a tool call with permission checking."""
        tool = self._get_tool_by_name(tool_call["name"])
        if tool is None:
            return {
                "type": "tool_result",
                "tool_use_id": tool_call["id"],
                "content": f"Unknown tool: {tool_call['name']}",
                "is_error": True,
            }

        # Check permission
        perm_result = tool.check_permission(tool.validate_input(tool_call["input"]), ctx)

        if perm_result.is_denied:
            return {
                "type": "tool_result",
                "tool_use_id": tool_call["id"],
                "content": f"Permission denied: {perm_result.reason}",
                "is_error": True,
            }

        # If needs confirmation and not bypass mode
        if perm_result.needs_confirmation and self.permission_mode != PermissionMode.BYPASS:
            # In a real implementation, this would prompt the user
            # For now, we allow with a note
            pass

        # Execute tool
        try:
            input_obj = tool.validate_input(tool_call["input"])
            result = await tool.execute(input_obj, ctx)
            return result.to_block(tool_call["id"]).model_dump()
        except Exception as e:
            return {
                "type": "tool_result",
                "tool_use_id": tool_call["id"],
                "content": f"Tool error: {e}",
                "is_error": True,
            }

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert internal messages to API format."""
        result: list[dict] = []
        for msg in messages:
            content: list[dict] = []
            for block in msg.content:
                if hasattr(block, "model_dump"):
                    content.append(block.model_dump())
                elif hasattr(block, "dict"):
                    content.append(block.dict())
                else:
                    content.append(dict(block))
            result.append({"role": msg.role, "content": content})
        return result


class QueryStats:
    """Track query statistics."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.tool_calls = 0
        self.turns = 0
        self.duration_ms = 0

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "tool_calls": self.tool_calls,
            "turns": self.turns,
            "duration_ms": self.duration_ms,
        }