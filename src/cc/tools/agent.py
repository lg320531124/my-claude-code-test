"""AgentTool - Spawn sub-agents."""

import asyncio
import json
import sys
from pathlib import Path
from typing import ClassVar, Any

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class AgentInput(ToolInput):
    """Input for AgentTool."""

    subagent_type: str | None = None
    description: str
    prompt: str
    model: str | None = None
    run_in_background: bool = False


class AgentTool(ToolDef):
    """Spawn sub-agents for parallel tasks."""

    name: ClassVar[str] = "Agent"
    description: ClassVar[str] = "Launch a sub-agent to handle complex multi-step tasks"
    input_schema: ClassVar[type[ToolInput]] = AgentInput

    async def execute(self, input: AgentInput, ctx: ToolUseContext) -> ToolResult:
        """Execute sub-agent."""
        try:
            # Determine subagent type
            agent_type = input.subagent_type or "general-purpose"

            # Build agent command
            agent_script = self._get_agent_script(agent_type)
            if agent_script is None:
                return ToolResult(
                    content=f"Unknown agent type: {agent_type}",
                    is_error=True,
                )

            # Run agent as subprocess
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                agent_script,
                "--prompt", input.prompt,
                "--cwd", ctx.cwd,
                "--session", ctx.session_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=300.0,  # 5 min timeout
            )

            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return ToolResult(
                    content=f"Agent failed: {error}",
                    is_error=True,
                )

            return ToolResult(
                content=output,
                metadata={
                    "agent_type": agent_type,
                    "description": input.description,
                },
            )

        except asyncio.TimeoutError:
            return ToolResult(
                content="Agent timed out after 5 minutes",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"Agent error: {e}",
                is_error=True,
            )

    def _get_agent_script(self, agent_type: str) -> Path | None:
        """Get agent script path."""
        # For now, return None - agents will be implemented later
        # This is a placeholder for the agent system
        return None


# Available agent types
AGENT_TYPES = {
    "general-purpose": "General purpose agent",
    "Explore": "Fast agent for codebase exploration",
    "plan": "Planning agent for complex tasks",
    "code-reviewer": "Code review specialist",
    "security-reviewer": "Security analysis agent",
    "build-error-resolver": "Build/compilation error fixer",
}