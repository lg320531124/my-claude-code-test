"""Enhanced AgentTool with asyncio support."""

from __future__ import annotations
import asyncio
import time
from typing import List, Dict, ClassVar, Callable, Optional
from dataclasses import dataclass, field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
from ..types.permission import PermissionResult, PermissionDecision


@dataclass
class AgentResult:
    """Agent execution result."""
    content: str
    is_error: bool = False
    metadata: dict = field(default_factory=dict)
    duration_ms: int = 0


class AgentInput(ToolInput):
    """Input for AgentTool."""

    subagent_type: Optional[str] = None
    description: str = ""
    prompt: str
    model: Optional[str] = None
    run_in_background: bool = False
    isolation: Optional[str] = None  # "worktree" for isolated execution


class AgentExecutor:
    """Executes sub-agents with asyncio."""

    def __init__(self, max_parallel: int = 3):
        self.max_parallel = max_parallel
        self.active_agents: Dict[str, asyncio.Task] = {}
        self.results: Dict[str, AgentResult] = {}
        self._on_result: Optional[Callable] = None

    async def execute(
        self,
        agent_type: str,
        prompt: str,
        ctx: ToolUseContext,
        model: Optional[str] = None,
        timeout: float = 300.0,
    ) -> AgentResult:
        """Execute agent with timeout."""
        start_time = time.time()
        agent_id = f"agent-{time.time_ns()}"

        try:
            # Run agent task
            task = asyncio.create_task(
                self._run_agent(agent_type, prompt, ctx, model),
                name=agent_id,
            )
            self.active_agents[agent_id] = task

            # Wait with timeout
            result = await asyncio.wait_for(task, timeout=timeout)

            duration = int((time.time() - start_time) * 1000)
            result.duration_ms = duration

            self.results[agent_id] = result
            return result

        except asyncio.TimeoutError:
            # Cancel task
            if agent_id in self.active_agents:
                self.active_agents[agent_id].cancel()
            return AgentResult(
                content=f"Agent timed out after {timeout}s",
                is_error=True,
                duration_ms=int(timeout * 1000),
            )

        except asyncio.CancelledError:
            return AgentResult(
                content="Agent cancelled",
                is_error=True,
            )

        except Exception as e:
            return AgentResult(
                content=f"Agent error: {e}",
                is_error=True,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        finally:
            self.active_agents.pop(agent_id, None)

    async def _run_agent(
        self,
        agent_type: str,
        prompt: str,
        ctx: ToolUseContext,
        model: Optional[str],
    ) -> AgentResult:
        """Run agent logic."""
        # Import agent implementation based on type
        agent_impl = self._get_agent_impl(agent_type)

        if agent_impl is None:
            return AgentResult(
                content=f"Unknown agent type: {agent_type}",
                is_error=True,
            )

        # Execute agent
        try:
            if asyncio.iscoroutinefunction(agent_impl):
                result = await agent_impl(prompt, ctx, model)
            else:
                # Run in executor for sync functions
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    agent_impl,
                    prompt,
                    ctx,
                    model,
                )

            if isinstance(result, str):
                return AgentResult(content=result)
            elif isinstance(result, AgentResult):
                return result
            else:
                return AgentResult(content=str(result))

        except Exception as e:
            return AgentResult(content=f"Error: {e}", is_error=True)

    def _get_agent_impl(self, agent_type: str) -> Callable | None:
        """Get agent implementation."""
        # Agent implementations map
        agents = {
            "general-purpose": self._general_agent,
            "Explore": self._explore_agent,
            "Plan": self._plan_agent,
            "code-reviewer": self._code_review_agent,
            "security-reviewer": self._security_review_agent,
            "build-error-resolver": self._build_error_agent,
            "refactor-cleaner": self._refactor_agent,
        }
        return agents.get(agent_type)

    async def _general_agent(self, prompt: str, ctx: ToolUseContext, model: Optional[str]) -> str:
        """General purpose agent."""
        # This would call the actual LLM with tools
        # For now, return placeholder
        return f"General agent result for: {prompt[:100]}"

    async def _explore_agent(self, prompt: str, ctx: ToolUseContext, model: Optional[str]) -> str:
        """Explore codebase agent."""
        # Uses Glob/Grep/Read tools
        return f"Exploration results for: {prompt[:100]}"

    async def _plan_agent(self, prompt: str, ctx: ToolUseContext, model: Optional[str]) -> str:
        """Planning agent."""
        return f"Plan for: {prompt[:100]}"

    async def _code_review_agent(self, prompt: str, ctx: ToolUseContext, model: Optional[str]) -> str:
        """Code review agent."""
        return f"Review: {prompt[:100]}"

    async def _security_review_agent(self, prompt: str, ctx: ToolUseContext, model: Optional[str]) -> str:
        """Security review agent."""
        return f"Security review: {prompt[:100]}"

    async def _build_error_agent(self, prompt: str, ctx: ToolUseContext, model: Optional[str]) -> str:
        """Build error resolver agent."""
        return f"Build fix: {prompt[:100]}"

    async def _refactor_agent(self, prompt: str, ctx: ToolUseContext, model: Optional[str]) -> str:
        """Refactor agent."""
        return f"Refactor: {prompt[:100]}"

    async def execute_parallel(
        self,
        agents: List[dict],
        ctx: ToolUseContext,
    ) -> List[AgentResult]:
        """Execute multiple agents in parallel."""
        # Limit to max_parallel
        agents_to_run = agents[:self.max_parallel]

        tasks = [
            self.execute(
                a.get("type", "general-purpose"),
                a.get("prompt", ""),
                ctx,
                a.get("model"),
            )
            for a in agents_to_run
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = []
        for result in results:
            if isinstance(result, Exception):
                processed.append(AgentResult(
                    content=f"Error: {result}",
                    is_error=True,
                ))
            else:
                processed.append(result)

        return processed

    def cancel_all(self) -> int:
        """Cancel all active agents."""
        cancelled = 0
        for task in self.active_agents.values():
            task.cancel()
            cancelled += 1
        return cancelled

    def get_active_count(self) -> int:
        """Get count of active agents."""
        return len(self.active_agents)

    def set_callback(self, callback: Callable) -> None:
        """Set result callback."""
        self._on_result = callback


class AgentTool(ToolDef):
    """Spawn sub-agents for parallel tasks."""

    name: ClassVar[str] = "Agent"
    description: ClassVar[str] = """Launch a sub-agent to handle complex multi-step tasks.

Available agent types:
- general-purpose: For general tasks
- Explore: Fast codebase exploration
- Plan: Implementation planning
- code-reviewer: Code review
- security-reviewer: Security analysis
- build-error-resolver: Fix build errors
- refactor-cleaner: Refactoring"""
    input_schema: ClassVar[type] = AgentInput

    # Agent executor instance
    _executor: ClassVar[AgentExecutor | None] = None

    def get_executor(self) -> AgentExecutor:
        """Get executor instance."""
        if AgentTool._executor is None:
            AgentTool._executor = AgentExecutor()
        return AgentTool._executor

    async def execute(self, input: AgentInput, ctx: ToolUseContext) -> ToolResult:
        """Execute sub-agent."""
        executor = self.get_executor()

        agent_type = input.subagent_type or "general-purpose"

        # Run agent
        result = await executor.execute(
            agent_type,
            input.prompt,
            ctx,
            input.model,
            timeout=300.0,
        )

        return ToolResult(
            content=result.content,
            is_error=result.is_error,
            metadata=result.metadata,
        )

    def check_permission(self, input: AgentInput, ctx: ToolUseContext) -> PermissionResult:
        """Check permission."""
        # Agents are generally allowed
        return PermissionResult(
            decision=PermissionDecision.ALLOW.value,
            reason="Sub-agent execution",
        )

    def get_api_schema(self) -> dict:
        """Get API schema."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "subagent_type": {
                        "type": "string",
                        "enum": [
                            "general-purpose",
                            "Explore",
                            "Plan",
                            "code-reviewer",
                            "security-reviewer",
                            "build-error-resolver",
                            "refactor-cleaner",
                        ],
                        "description": "Type of sub-agent",
                    },
                    "description": {
                        "type": "string",
                        "description": "Short task description",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Full prompt for agent",
                    },
                    "model": {
                        "type": "string",
                        "description": "Optional model override",
                    },
                    "run_in_background": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["prompt"],
            },
        }


# Agent type registry
AGENT_TYPES = {
    "general-purpose": "General purpose agent for any task",
    "Explore": "Fast agent for codebase exploration",
    "Plan": "Planning agent for complex features",
    "code-reviewer": "Expert code review specialist",
    "security-reviewer": "Security vulnerability analysis",
    "build-error-resolver": "Build and compilation error fixer",
    "refactor-cleaner": "Dead code cleanup and refactoring",
    "tdd-guide": "Test-driven development guide",
    "database-reviewer": "Database schema and query review",
    "doc-updater": "Documentation and codemap updates",
    "e2e-runner": "End-to-end test runner",
}


def get_agent_types() -> Dict[str, str]:
    """Get available agent types."""
    return AGENT_TYPES


async def run_agent(
    agent_type: str,
    prompt: str,
    ctx: ToolUseContext,
    model: Optional[str] = None,
) -> AgentResult:
    """Run agent directly."""
    executor = AgentExecutor()
    return await executor.execute(agent_type, prompt, ctx, model)
