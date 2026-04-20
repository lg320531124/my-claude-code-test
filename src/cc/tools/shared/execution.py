"""Shared tool execution engine.

Common execution patterns for tools.
"""

from __future__ import annotations
import asyncio
import time
from typing import Dict, Any, Optional, Callable, List, AsyncIterator

from ..types.tool import Tool, ToolResult, ToolUseContext


async def execute_with_timeout(
    tool: Tool,
    args: Dict[str, Any],
    context: ToolUseContext,
    can_use_tool: Callable,
    parent_message: Any,
    timeout: float,
    on_progress: Optional[Callable] = None,
) -> ToolResult:
    """Execute tool with timeout."""
    try:
        return await asyncio.wait_for(
            tool.call(args, context, can_use_tool, parent_message, on_progress),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return ToolResult(
            data={"error": f"Tool timed out after {timeout}s"},
            is_error=True,
        )


async def execute_with_retry(
    tool: Tool,
    args: Dict[str, Any],
    context: ToolUseContext,
    can_use_tool: Callable,
    parent_message: Any,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    on_progress: Optional[Callable] = None,
) -> ToolResult:
    """Execute tool with retry logic."""
    for attempt in range(max_retries + 1):
        result = await tool.call(args, context, can_use_tool, parent_message, on_progress)

        # Check if success or non-retriable error
        if not hasattr(result, 'is_error') or not result.is_error:
            return result

        # Check error type (some errors shouldn't retry)
        error_msg = getattr(result, 'error_message', '')
        if "not found" in error_msg.lower() or "permission" in error_msg.lower():
            return result  # Don't retry permission/not found errors

        if attempt < max_retries:
            await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff

    return result


async def execute_parallel(
    tools: List[Tool],
    args_list: List[Dict[str, Any]],
    context: ToolUseContext,
    can_use_tool: Callable,
    parent_message: Any,
    on_progress: Optional[Callable] = None,
) -> List[ToolResult]:
    """Execute multiple tools in parallel."""
    tasks = [
        tool.call(args, context, can_use_tool, parent_message, on_progress)
        for tool, args in zip(tools, args_list)
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def execute_with_progress(
    tool: Tool,
    args: Dict[str, Any],
    context: ToolUseContext,
    can_use_tool: Callable,
    parent_message: Any,
    on_progress: Callable,
    progress_interval: float = 0.5,
) -> ToolResult:
    """Execute tool with periodic progress updates."""
    start_time = time.time()
    last_progress = start_time

    async def progress_task():
        while True:
            await asyncio.sleep(progress_interval)
            elapsed = time.time() - last_progress
            on_progress({"elapsed": elapsed, "running": True})

    # Start progress task
    progress = asyncio.create_task(progress_task())

    try:
        result = await tool.call(args, context, can_use_tool, parent_message)
        progress.cancel()
        on_progress({"elapsed": time.time() - start_time, "completed": True})
        return result
    except Exception as e:
        progress.cancel()
        on_progress({"elapsed": time.time() - start_time, "error": str(e)})
        raise


async def execute_with_callback(
    tool: Tool,
    args: Dict[str, Any],
    context: ToolUseContext,
    can_use_tool: Callable,
    parent_message: Any,
    on_start: Optional[Callable] = None,
    on_complete: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
) -> ToolResult:
    """Execute tool with lifecycle callbacks."""
    if on_start:
        on_start(tool.name, args)

    try:
        result = await tool.call(args, context, can_use_tool, parent_message)
        if on_complete:
            on_complete(tool.name, result)
        return result
    except Exception as e:
        if on_error:
            on_error(tool.name, e)
        raise


class ToolExecutor:
    """Async tool execution manager."""

    def __init__(
        self,
        context: ToolUseContext,
        can_use_tool: Callable,
        default_timeout: float = 120.0,
    ):
        self.context = context
        self.can_use_tool = can_use_tool
        self.default_timeout = default_timeout

    async def execute(
        self,
        tool: Tool,
        args: Dict[str, Any],
        parent_message: Any,
        timeout: Optional[float] = None,
    ) -> ToolResult:
        """Execute a single tool."""
        return await execute_with_timeout(
            tool,
            args,
            self.context,
            self.can_use_tool,
            parent_message,
            timeout or self.default_timeout,
        )

    async def execute_all(
        self,
        tools: List[Tool],
        args_list: List[Dict[str, Any]],
        parent_message: Any,
    ) -> List[ToolResult]:
        """Execute multiple tools in parallel."""
        return await execute_parallel(
            tools,
            args_list,
            self.context,
            self.can_use_tool,
            parent_message,
        )


__all__ = [
    "execute_with_timeout",
    "execute_with_retry",
    "execute_parallel",
    "execute_with_progress",
    "execute_with_callback",
    "ToolExecutor",
]