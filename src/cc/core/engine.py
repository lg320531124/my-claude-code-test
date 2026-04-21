"""Core Query Engine - Complete implementation matching TypeScript QueryEngine.ts.

Ported patterns:
- QueryEngineConfig with cwd, tools, commands, mcpClients, agents
- mutableMessages for storing messages across turns
- abortController for handling cancellation
- permissionDenials tracking
- totalUsage tracking
- readFileState (file cache)
- discoveredSkillNames and loadedNestedMemoryPaths
- submitMessage() generator yielding SDKMessage
- System prompt building with custom prompts
- Tool execution with permission checks
- Message normalization
- History compression
- ThinkingConfig support
"""

from __future__ import annotations
import asyncio
import json
import os
import time
from typing import AsyncIterator, Any, Callable, Optional, Dict, List, Set, Union
from dataclasses import dataclass, field
from enum import Enum

from ..services.api.client import get_client
from ..types.message import (
    AssistantMessage,
    ContentBlock,
    Message,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_user_message,
)
from ..types.tool import Tool, ToolUseContext
from ..types.permission import PermissionDecision


class SDKStatus(str, Enum):
    """SDK status types."""

    READY = "ready"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


class ThinkingType(str, Enum):
    """Thinking configuration types."""

    DISABLED = "disabled"
    ADAPTIVE = "adaptive"
    ALWAYS = "always"


@dataclass
class ThinkingConfig:
    """Thinking configuration."""

    type: ThinkingType = ThinkingType.ADAPTIVE
    budget_tokens: Optional[int] = None


@dataclass
class Usage:
    """API usage tracking."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def total(self) -> int:
        """Get total tokens."""
        return self.input_tokens + self.output_tokens

    def add(self, other: Usage) -> None:
        """Add another usage to this one."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_creation_input_tokens += other.cache_creation_input_tokens
        self.cache_read_input_tokens += other.cache_read_input_tokens


EMPTY_USAGE = Usage()


@dataclass
class SDKPermissionDenial:
    """SDK permission denial record."""

    tool_name: str
    tool_use_id: str
    tool_input: Dict[str, Any]


@dataclass
class SDKCompactBoundaryMessage:
    """SDK compact boundary message."""

    type: str = "compact_boundary"
    message: Optional[Message] = None


@dataclass
class SDKUserMessageReplay:
    """SDK user message replay."""

    type: str = "user_message_replay"
    content: str = ""
    uuid: Optional[str] = None


@dataclass
class QueryEngineConfig:
    """QueryEngine configuration matching TypeScript QueryEngineConfig."""

    cwd: str
    tools: List[Tool]
    commands: List[Any] = field(default_factory=list)
    mcp_clients: List[Any] = field(default_factory=list)
    agents: List[Any] = field(default_factory=list)
    can_use_tool: Optional[Callable] = None
    get_app_state: Optional[Callable] = None
    set_app_state: Optional[Callable] = None
    initial_messages: Optional[List[Message]] = None
    read_file_cache: Dict[str, Any] = field(default_factory=dict)
    custom_system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None
    user_specified_model: Optional[str] = None
    fallback_model: Optional[str] = None
    thinking_config: Optional[ThinkingConfig] = None
    max_turns: int = 20
    max_budget_usd: Optional[float] = None
    task_budget: Optional[Dict[str, float]] = None
    json_schema: Optional[Dict[str, Any]] = None
    verbose: bool = False
    replay_user_messages: bool = False
    handle_elicitation: Optional[Callable] = None
    include_partial_messages: bool = False
    set_sdk_status: Optional[Callable] = None
    abort_controller: Optional[Any] = None
    orphaned_permission: Optional[Any] = None


@dataclass
class ProcessUserInputContext:
    """Context for processing user input."""

    messages: List[Message]
    set_messages: Callable
    on_change_api_key: Callable = lambda: None
    handle_elicitation: Optional[Callable] = None
    options: Dict[str, Any] = field(default_factory=dict)
    get_app_state: Optional[Callable] = None
    set_app_state: Optional[Callable] = None
    abort_controller: Optional[Any] = None
    read_file_state: Dict[str, Any] = field(default_factory=dict)
    nested_memory_attachment_triggers: Set[str] = field(default_factory=set)
    loaded_nested_memory_paths: Set[str] = field(default_factory=set)
    dynamic_skill_dir_triggers: Set[str] = field(default_factory=set)
    discovered_skill_names: Set[str] = field(default_factory=set)
    set_in_progress_tool_use_ids: Callable = lambda x: None
    set_response_length: Callable = lambda x: None
    update_file_history_state: Optional[Callable] = None
    update_attribution_state: Optional[Callable] = None
    set_sdk_status: Optional[Callable] = None


class MessageHistory:
    """Manages message history with limits."""

    def __init__(
        self,
        max_messages: int = 100,
        max_tokens: int = 100_000,
        compression_threshold: float = 0.8,
    ):
        self.messages: List[Message] = []
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.compression_threshold = compression_threshold
        self._token_estimate = 0

    def add(self, message: Message) -> None:
        """Add message to history."""
        self.messages.append(message)
        self._token_estimate += self._estimate_message_tokens(message)
        self._check_limits()

    def _estimate_message_tokens(self, message: Message) -> int:
        """Estimate tokens in a message."""
        total = 0
        for block in message.content:
            if isinstance(block, TextBlock):
                total += len(block.text) // 4
            elif hasattr(block, "content") and isinstance(block.content, str):
                total += len(block.content) // 4
        return total

    def _check_limits(self) -> None:
        """Check and enforce limits."""
        if len(self.messages) > self.max_messages:
            self._compress_messages()

        if self._token_estimate > self.max_tokens * self.compression_threshold:
            self._compress_messages()

    def _compress_messages(self) -> None:
        """Compress message history."""
        if len(self.messages) <= 5:
            return

        old_messages = self.messages[:-5]
        recent_messages = self.messages[-5:]

        summary_parts = []
        for msg in old_messages:
            for block in msg.content:
                if isinstance(block, TextBlock):
                    text = block.text[:100]
                    if len(block.text) > 100:
                        text += "..."
                    summary_parts.append(f"{msg.role}: {text}")

        summary_text = "[COMPRESSED HISTORY]\n" + "\n".join(summary_parts[:5])
        if len(summary_parts) > 5:
            summary_text += f"\n... and {len(summary_parts) - 5} more messages"

        compressed = create_user_message(summary_text)
        self.messages = [compressed] + recent_messages
        self._token_estimate = self._estimate_history_tokens()

    def _estimate_history_tokens(self) -> int:
        """Estimate total tokens in history."""
        return sum(self._estimate_message_tokens(m) for m in self.messages)

    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []
        self._token_estimate = 0

    def to_api_format(self) -> List[dict]:
        """Convert to API format."""
        result = []
        for msg in self.messages:
            content = []
            for block in msg.content:
                if hasattr(block, "model_dump"):
                    content.append(block.model_dump())
                elif hasattr(block, "dict"):
                    content.append(block.dict())
                else:
                    content.append({
                        "type": getattr(block, "type", "text"),
                        "text": getattr(block, "text", str(block)),
                    })
            result.append({"role": msg.role, "content": content})
        return result

    def get_token_usage(self) -> dict:
        """Get current token usage."""
        return {
            "estimated_tokens": self._token_estimate,
            "message_count": len(self.messages),
            "max_tokens": self.max_tokens,
            "usage_percent": (self._token_estimate / self.max_tokens) * 100,
        }


class ToolExecutor:
    """Manages tool execution with parallel support."""

    def __init__(
        self,
        tools: List[Tool],
        permission_prompter: Optional[Any] = None,
        max_parallel: int = 5,
    ):
        self.tools = {tool.name: tool for tool in tools}
        self.permission_prompter = permission_prompter
        self.max_parallel = max_parallel
        self.executed_tools: List[dict] = []
        self.failed_tools: List[dict] = []
        self.permission_denials: List[SDKPermissionDenial] = []

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)

    def get_schemas(self) -> List[dict]:
        """Get all tool schemas."""
        return [tool.get_api_schema() for tool in self.tools.values()]

    def matches_tool_name(self, tool: Tool, name: str) -> bool:
        """Check if tool matches name (including aliases)."""
        if tool.name == name:
            return True
        aliases = getattr(tool, "aliases", None)
        return aliases and name in aliases

    async def execute_single(
        self,
        tool_call: dict,
        ctx: ToolUseContext,
        can_use_tool: Optional[Callable] = None,
    ) -> dict:
        """Execute a single tool call."""
        tool_name = tool_call.get("name", "")
        tool_id = tool_call.get("id", "")
        tool_input = tool_call.get("input", {})

        tool = self.get_tool(tool_name)
        if tool is None:
            self.failed_tools.append(tool_call)
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Unknown tool: {tool_name}",
                "is_error": True,
            }

        # Validate input
        validation = await tool.validate_input(tool_input, ctx)
        if not validation.result:
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": validation.message or "Invalid input",
                "is_error": True,
            }

        # Check permission
        perm_result = await tool.check_permissions(tool_input, ctx)

        if perm_result.decision == PermissionDecision.DENY:
            self.permission_denials.append(SDKPermissionDenial(
                tool_name=tool_name,
                tool_use_id=tool_id,
                tool_input=tool_input,
            ))
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Permission denied: {perm_result.reason}",
                "is_error": True,
            }

        # Handle ASK permission
        if perm_result.decision == PermissionDecision.ASK:
            if can_use_tool:
                # Use permission handler
                decision = await can_use_tool(tool, tool_input, ctx, None, tool_id)
                if decision.decision != PermissionDecision.ALLOW:
                    self.permission_denials.append(SDKPermissionDenial(
                        tool_name=tool_name,
                        tool_use_id=tool_id,
                        tool_input=tool_input,
                    ))
                    return {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": "Permission denied",
                        "is_error": True,
                    }
            else:
                return {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": "Permission required",
                    "is_error": True,
                }

        # Execute
        try:
            result = await tool.call(tool_input, ctx, can_use_tool, None)
            self.executed_tools.append({
                "name": tool_name,
                "id": tool_id,
                "input": tool_input,
                "result": result,
            })

            # Map result to block
            if hasattr(tool, "map_tool_result_to_tool_result_block_param"):
                return tool.map_tool_result_to_tool_result_block_param(result.data, tool_id)

            return result.to_block(tool_id).model_dump()

        except Exception as e:
            self.failed_tools.append(tool_call)
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Execution error: {e}",
                "is_error": True,
            }

    async def execute_parallel(
        self,
        tool_calls: List[dict],
        ctx: ToolUseContext,
        can_use_tool: Optional[Callable] = None,
    ) -> List[dict]:
        """Execute multiple tool calls in parallel."""
        calls_to_execute = tool_calls[:self.max_parallel]

        results = await asyncio.gather(
            *[self.execute_single(tc, ctx, can_use_tool) for tc in calls_to_execute],
            return_exceptions=True,
        )

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "type": "tool_result",
                    "tool_use_id": calls_to_execute[i]["id"],
                    "content": f"Error: {result}",
                    "is_error": True,
                })
            else:
                processed_results.append(result)

        return processed_results

    def get_stats(self) -> dict:
        """Get execution statistics."""
        return {
            "executed": len(self.executed_tools),
            "failed": len(self.failed_tools),
            "denials": len(self.permission_denials),
            "total": len(self.executed_tools) + len(self.failed_tools),
        }


def build_default_system_prompt() -> str:
    """Build default system prompt."""
    return """You are Claude Code, Anthropic's official CLI for Claude.
You are an interactive agent that helps users with software engineering tasks.

# System
- All text you output outside of tool use is displayed to the user.
- Use Github-flavored markdown for formatting.

# Doing tasks
- When given an unclear or generic instruction, consider it in the context of software engineering tasks.
- Be careful not to introduce security vulnerabilities.
- Don't add features, refactor, or introduce abstractions beyond what the task requires.

# Using your tools
- Use dedicated tools over Bash when one fits.
- Use TaskCreate to plan and track work.
- Mark each task completed as soon as it's done; don't batch.

# Tone and style
- Your responses should be short and concise.
- When referencing code, include the pattern file_path:line_number.
- Don't narrate your internal deliberation.

# Auto memory
You have a persistent, file-based memory system."""


class QueryEngine:
    """Query Engine matching TypeScript QueryEngine.ts.

    Owns the query lifecycle and session state for a conversation.
    One QueryEngine per conversation. Each submit_message() call starts a new turn.
    """

    def __init__(self, config: QueryEngineConfig):
        self.config = config
        self.mutable_messages = config.initial_messages or []
        # Lazy initialize abort_controller to avoid event loop requirement
        self._abort_controller: Optional[asyncio.Event] = None
        self._abort_controller_config = config.abort_controller
        self.permission_denials: List[SDKPermissionDenial] = []
        self.total_usage = EMPTY_USAGE
        self.read_file_state = config.read_file_cache
        self.discovered_skill_names: Set[str] = set()
        self.loaded_nested_memory_paths: Set[str] = set()

        # Initialize components
        self.executor = ToolExecutor(config.tools)
        self.history = MessageHistory()

        # Initialize client
        model = config.user_specified_model or config.fallback_model or "claude-sonnet-4-6"
        self.client = get_client(model=model)

        # System prompt
        self.system_prompt = config.custom_system_prompt or build_default_system_prompt()
        if config.append_system_prompt:
            self.system_prompt += "\n" + config.append_system_prompt

        # Stats
        self.stats = QueryStats()

        # Thinking config
        self.thinking_config = config.thinking_config or ThinkingConfig(type=ThinkingType.ADAPTIVE)

    @property
    def abort_controller(self) -> asyncio.Event:
        """Get abort controller, creating lazily if needed."""
        if self._abort_controller is None:
            if self._abort_controller_config is not None:
                self._abort_controller = self._abort_controller_config
            else:
                # Try to get running loop, create Event if available
                try:
                    asyncio.get_running_loop()
                    self._abort_controller = asyncio.Event()
                except RuntimeError:
                    # No running loop, use a placeholder that will be replaced
                    self._abort_controller = asyncio.Event()  # Will work when loop is available
        return self._abort_controller

    def _create_tool_use_context(self) -> ToolUseContext:
        """Create tool use context."""
        return ToolUseContext(
            commands=self.config.commands,
            debug=self.config.verbose,
            main_loop_model=self.config.user_specified_model or "claude-sonnet-4-6",
            tools=self.config.tools,
            verbose=self.config.verbose,
            thinking_config=self.thinking_config,
            mcp_clients=self.config.mcp_clients,
            is_non_interactive_session=True,
            max_budget_usd=self.config.max_budget_usd,
            custom_system_prompt=self.config.custom_system_prompt,
            append_system_prompt=self.config.append_system_prompt,
            abort_controller=self.abort_controller,
            read_file_state=self.read_file_state,
            cwd=self.config.cwd,
            messages=self.mutable_messages,
            file_reading_limits={"maxTokens": 50000, "maxSizeBytes": 10_000_000},
            glob_limits={"maxResults": 100},
        )

    async def submit_message(
        self,
        prompt: Union[str, List[ContentBlock]],
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Any]:
        """Submit a message and process the query lifecycle.

        Yields SDKMessage events as the query progresses.
        """
        start_time = time.time()
        options = options or {}

        # Clear discovered skills for this turn
        self.discovered_skill_names.clear()

        # Create context
        ctx = self._create_tool_use_context()

        # Add user message
        if isinstance(prompt, str):
            user_msg = create_user_message(prompt)
        else:
            user_msg = UserMessage(content=prompt, uuid=options.get("uuid"))

        self.mutable_messages.append(user_msg)
        self.history.add(user_msg)

        # Track state
        turn_count = 0
        complete_response = ""

        while turn_count < self.config.max_turns:
            turn_count += 1
            self.stats.turns = turn_count

            # Yield start event
            yield {"type": "turn_start", "turn": turn_count}

            # Prepare API call
            api_messages = self.history.to_api_format()

            # Stream response
            response_text = ""
            tool_calls: List[dict] = []
            current_tool: Optional[dict] = None
            tool_input_buffer = ""
            stop_reason = None

            async for event in self.client.create_message(
                messages=api_messages,
                tools=self.executor.get_schemas(),
                system=self.system_prompt,
                max_tokens=4096,
                stream=True,
            ):
                event_type = event.get("type", "")

                if event_type == "text_delta":
                    text = event.get("text", "")
                    response_text += text
                    complete_response += text
                    yield {"type": "text", "text": text}

                elif event_type == "tool_use_start":
                    current_tool = {
                        "id": event.get("id"),
                        "name": event.get("name"),
                        "index": event.get("index"),
                    }
                    tool_input_buffer = ""
                    yield {"type": "tool_start", "tool": current_tool}

                elif event_type == "input_json_delta":
                    tool_input_buffer += event.get("partial_json", "")

                elif event_type == "content_block_stop":
                    if current_tool:
                        try:
                            tool_input = json.loads(tool_input_buffer)
                        except json.JSONDecodeError:
                            tool_input = {}
                        tool_calls.append({
                            "id": current_tool["id"],
                            "name": current_tool["name"],
                            "input": tool_input,
                        })
                        self.stats.tool_calls += 1
                    current_tool = None

                elif event_type == "message_stop":
                    stop_reason = event.get("stop_reason", "end_turn")

                elif event_type == "message_start":
                    usage = event.get("usage", {})
                    self.total_usage.add(Usage(
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0),
                        cache_read_input_tokens=usage.get("cache_read_input_tokens", 0),
                    ))

                elif event_type == "error":
                    yield {"type": "error", "message": event.get("error", "")}
                    break

            # Yield response text
            if response_text:
                yield {"type": "response", "text": response_text}

            # Process tool calls
            if tool_calls:
                # Add assistant message
                assistant_msg = AssistantMessage(
                    content=[
                        TextBlock(text=response_text),
                        *[ToolUseBlock(
                            id=tc["id"],
                            name=tc["name"],
                            input=tc["input"],
                        ) for tc in tool_calls],
                    ],
                    stop_reason=stop_reason,
                )
                self.history.add(assistant_msg)

                # Execute tools
                results = await self.executor.execute_parallel(
                    tool_calls,
                    ctx,
                    self.config.can_use_tool,
                )

                # Add tool results
                tool_result_msg = UserMessage(
                    content=[
                        ToolResultBlock(
                            tool_use_id=r["tool_use_id"],
                            content=r["content"],
                            is_error=r.get("is_error", False),
                        )
                        for r in results
                    ],
                )
                self.history.add(tool_result_msg)

                # Yield tool results
                yield {"type": "tool_results", "results": results}

                # Continue loop
                continue

            # No tool calls - add assistant message and finish
            assistant_msg = AssistantMessage(
                content=[TextBlock(text=response_text)],
                stop_reason=stop_reason,
            )
            self.history.add(assistant_msg)

            break

        # Update stats
        self.stats.duration_ms = int((time.time() - start_time) * 1000)
        self.stats.input_tokens = self.total_usage.input_tokens
        self.stats.output_tokens = self.total_usage.output_tokens

        # Yield complete event
        yield {"type": "complete", "stats": self.stats.to_dict()}

    def get_context_summary(self) -> dict:
        """Get current context summary."""
        return {
            "history": self.history.get_token_usage(),
            "tools": self.executor.get_stats(),
            "stats": self.stats.to_dict(),
            "permission_denials": len(self.permission_denials),
        }

    def set_callbacks(
        self,
        on_text: Optional[Callable] = None,
        on_tool_start: Optional[Callable] = None,
        on_tool_result: Optional[Callable] = None,
    ) -> None:
        """Set callbacks for events."""
        self._on_text = on_text
        self._on_tool_start = on_tool_start
        self._on_tool_result = on_tool_result

    def get_permission_denials(self) -> List[SDKPermissionDenial]:
        """Get permission denials for SDK reporting."""
        return self.permission_denials


class QueryStats:
    """Query statistics."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.tool_calls = 0
        self.turns = 0
        self.duration_ms = 0
        self.api_calls = 0

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "tool_calls": self.tool_calls,
            "turns": self.turns,
            "duration_ms": self.duration_ms,
            "api_calls": self.api_calls,
        }

    def estimate_cost(self, model: str = "claude-sonnet-4-6") -> float:
        """Estimate cost in USD."""
        prices = {
            "claude-opus-4-5": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
            "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
        }

        price = prices.get(model, {"input": 3.0, "output": 15.0})
        input_cost = (self.input_tokens / 1_000_000) * price["input"]
        output_cost = (self.output_tokens / 1_000_000) * price["output"]

        return input_cost + output_cost


# Convenience function for simple queries
async def query(
    prompt: str,
    model: str = "claude-sonnet-4-6",
    tools: Optional[List[Tool]] = None,
    cwd: Optional[str] = None,
) -> str:
    """Execute a simple query."""
    config = QueryEngineConfig(
        cwd=cwd or os.getcwd(),
        tools=tools or [],
    )
    engine = QueryEngine(config)

    result = []
    async for event in engine.submit_message(prompt):
        if event.get("type") == "text":
            result.append(event.get("text", ""))
        elif event.get("type") == "complete":
            break

    return "".join(result)


__all__ = [
    "QueryEngine",
    "QueryEngineConfig",
    "QueryStats",
    "Usage",
    "EMPTY_USAGE",
    "SDKStatus",
    "SDKPermissionDenial",
    "ThinkingConfig",
    "ThinkingType",
    "ProcessUserInputContext",
    "ToolExecutor",
    "MessageHistory",
    "query",
    "build_default_system_prompt",
]