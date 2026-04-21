"""Core Executor - Tool execution orchestration."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from ..tools.shared.execution import ToolContext, ExecutionResult


class ExecutorMode(Enum):
    """Executor modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"


@dataclass
class ExecutionPlan:
    """Execution plan for tools."""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    mode: ExecutorMode = ExecutorMode.SEQUENTIAL
    max_parallel: int = 4
    timeout: float = 300.0
    on_error: str = "stop"  # stop, continue, retry


@dataclass
class PlanResult:
    """Plan execution result."""
    plan_id: str
    success: bool = False
    results: List[ExecutionResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_time: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CoreExecutor:
    """Core tool execution orchestrator."""

    def __init__(self):
        self._plans: Dict[str, PlanResult] = {}
        self._running: Dict[str, asyncio.Task] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "pre_step": [],
            "post_step": [],
            "on_plan_start": [],
            "on_plan_complete": [],
        }

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        context: ToolContext,
    ) -> PlanResult:
        """Execute execution plan.

        Args:
            plan: Execution plan
            context: Tool context

        Returns:
            PlanResult
        """
        from ..tools.shared.execution import get_executor

        plan_id = str(uuid.uuid4())[:8]
        result = PlanResult(
            plan_id=plan_id,
            started_at=datetime.now(),
        )

        self._plans[plan_id] = result

        # Run pre-plan hooks
        for hook in self._hooks["on_plan_start"]:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(plan, context)
                else:
                    hook(plan, context)
            except Exception:
                pass

        executor = get_executor()

        try:
            if plan.mode == ExecutorMode.SEQUENTIAL:
                for step in plan.steps:
                    step_result = await self._execute_step(
                        step, context, executor, plan.timeout
                    )
                    result.results.append(step_result)

                    if not step_result.success and plan.on_error == "stop":
                        result.errors.append(step_result.error or "Step failed")
                        break

            elif plan.mode == ExecutorMode.PARALLEL:
                semaphore = asyncio.Semaphore(plan.max_parallel)

                async def limited_execute(step):
                    async with semaphore:
                        return await self._execute_step(
                            step, context, executor, plan.timeout
                        )

                results = await asyncio.gather(
                    *[limited_execute(step) for step in plan.steps],
                    return_exceptions=True,
                )

                for r in results:
                    if isinstance(r, Exception):
                        result.errors.append(str(r))
                    else:
                        result.results.append(r)

            elif plan.mode == ExecutorMode.BATCH:
                # Execute all steps in batch
                batch_results = await executor.execute_batch(
                    plan.steps, context
                )
                result.results = batch_results

            result.success = len(result.errors) == 0

        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        finally:
            result.completed_at = datetime.now()
            result.total_time = (
                result.completed_at - result.started_at
            ).total_seconds()

            # Run post-plan hooks
            for hook in self._hooks["on_plan_complete"]:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook(result, context)
                    else:
                        hook(result, context)
                except Exception:
                    pass

        return result

    async def _execute_step(
        self,
        step: Dict[str, Any],
        context: ToolContext,
        executor: Any,
        timeout: float,
    ) -> ExecutionResult:
        """Execute single step."""
        # Run pre-step hooks
        for hook in self._hooks["pre_step"]:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(step, context)
                else:
                    hook(step, context)
            except Exception:
                pass

        result = await executor.execute(
            step.get("tool_name"),
            step.get("args", {}),
            context,
            timeout=timeout,
        )

        # Run post-step hooks
        for hook in self._hooks["post_step"]:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(result, context)
                else:
                    hook(result, context)
            except Exception:
                pass

        return result

    def add_hook(self, hook_type: str, hook: Callable) -> None:
        """Add execution hook.

        Args:
            hook_type: pre_step, post_step, on_plan_start, on_plan_complete
            hook: Hook function
        """
        if hook_type in self._hooks:
            self._hooks[hook_type].append(hook)

    def cancel(self, plan_id: str) -> bool:
        """Cancel running plan.

        Args:
            plan_id: Plan ID

        Returns:
            True if cancelled
        """
        if plan_id in self._running:
            task = self._running[plan_id]
            task.cancel()
            return True
        return False

    def get_result(self, plan_id: str) -> Optional[PlanResult]:
        """Get plan result.

        Args:
            plan_id: Plan ID

        Returns:
            PlanResult or None
        """
        return self._plans.get(plan_id)


# Global executor
_core_executor: Optional[CoreExecutor] = None


def get_core_executor() -> CoreExecutor:
    """Get global core executor."""
    global _core_executor
    if _core_executor is None:
        _core_executor = CoreExecutor()
    return _core_executor


async def execute_tools(
    steps: List[Dict[str, Any]],
    context: ToolContext,
    mode: ExecutorMode = ExecutorMode.SEQUENTIAL,
) -> PlanResult:
    """Execute tools.

    Args:
        steps: Tool steps
        context: Tool context
        mode: Execution mode

    Returns:
        PlanResult
    """
    plan = ExecutionPlan(steps=steps, mode=mode)
    return await get_core_executor().execute_plan(plan, context)


__all__ = [
    "ExecutorMode",
    "ExecutionPlan",
    "PlanResult",
    "CoreExecutor",
    "get_core_executor",
    "execute_tools",
]
