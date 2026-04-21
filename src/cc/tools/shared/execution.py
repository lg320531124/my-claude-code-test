"""Tool Execution - Execution engine for tools."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, List, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class ExecutionState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    id: str
    tool_name: str
    state: ExecutionState = ExecutionState.PENDING
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_done(self) -> bool:
        return self.state in {ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.CANCELLED}


@dataclass
class ToolContext:
    session_id: str
    working_dir: str
    user_id: Optional[str] = None
    request_id: str = ""
    permissions: Dict[str, bool] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)


class ToolExecutor:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._executions: Dict[str, ExecutionResult] = {}
        self._hooks: Dict[str, List[Callable]] = {"pre_execute": [], "post_execute": [], "on_error": []}
        self._max_concurrent: int = 10
        self._running_count: int = 0
        self._default_timeout: float = 300.0

    def register_tool(self, name: str, handler: Callable) -> None:
        self._tools[name] = handler

    async def execute(self, tool_name: str, args: Dict, context: ToolContext, timeout: float = None) -> ExecutionResult:
        execution_id = str(uuid.uuid4())
        result = ExecutionResult(id=execution_id, tool_name=tool_name)
        self._executions[execution_id] = result

        handler = self._tools.get(tool_name)
        if not handler:
            result.state = ExecutionState.FAILED
            result.error = f"Unknown tool: {tool_name}"
            return result

        while self._running_count >= self._max_concurrent:
            await asyncio.sleep(0.1)

        self._running_count += 1
        result.state = ExecutionState.RUNNING
        result.started_at = datetime.now()

        try:
            timeout_val = timeout or self._default_timeout
            if asyncio.iscoroutinefunction(handler):
                output = await asyncio.wait_for(handler(args, context), timeout=timeout_val)
            else:
                loop = asyncio.get_event_loop()
                output = await asyncio.wait_for(loop.run_in_executor(None, handler, args, context), timeout=timeout_val)

            result.output = output
            result.state = ExecutionState.COMPLETED
            result.completed_at = datetime.now()
            result.duration = (result.completed_at - result.started_at).total_seconds()

        except asyncio.TimeoutError:
            result.state = ExecutionState.TIMEOUT
            result.error = f"Timeout after {timeout_val}s"
            result.completed_at = datetime.now()
        except Exception as e:
            result.state = ExecutionState.FAILED
            result.error = str(e)
            result.completed_at = datetime.now()
        finally:
            self._running_count -= 1

        return result

    async def execute_batch(self, calls: List[Dict], context: ToolContext) -> List[ExecutionResult]:
        tasks = [self.execute(c["tool_name"], c["args"], context) for c in calls]
        return await asyncio.gather(*tasks)

    def get_tools(self) -> List[str]:
        return list(self._tools.keys())


_executor: Optional[ToolExecutor] = None

def get_executor() -> ToolExecutor:
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor

async def execute_tool(tool_name: str, args: Dict, context: ToolContext) -> ExecutionResult:
    return await get_executor().execute(tool_name, args, context)

__all__ = ["ExecutionState", "ExecutionResult", "ToolContext", "ToolExecutor", "get_executor", "execute_tool"]
