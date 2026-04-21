"""Coordinator Module - Multi-agent orchestration mode.

Provides coordinator mode functionality for orchestrating software engineering
tasks across multiple worker agents.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Set

# Tool names
AGENT_TOOL_NAME = "Agent"
BASH_TOOL_NAME = "Bash"
FILE_READ_TOOL_NAME = "Read"
FILE_EDIT_TOOL_NAME = "Edit"
SEND_MESSAGE_TOOL_NAME = "SendMessage"
SYNTHETIC_OUTPUT_TOOL_NAME = "SyntheticOutput"
TASK_STOP_TOOL_NAME = "TaskStop"
TEAM_CREATE_TOOL_NAME = "TeamCreate"
TEAM_DELETE_TOOL_NAME = "TeamDelete"

# Internal worker tools (not exposed to workers)
INTERNAL_WORKER_TOOLS: Set[str] = {
    TEAM_CREATE_TOOL_NAME,
    TEAM_DELETE_TOOL_NAME,
    SEND_MESSAGE_TOOL_NAME,
    SYNTHETIC_OUTPUT_TOOL_NAME,
}

# Default async agent allowed tools
ASYNC_AGENT_ALLOWED_TOOLS: Set[str] = {
    BASH_TOOL_NAME,
    FILE_READ_TOOL_NAME,
    FILE_EDIT_TOOL_NAME,
    "Write",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "Skill",
}


def is_env_truthy(value: Optional[str]) -> bool:
    """Check if environment variable is truthy."""
    if value is None:
        return False
    return value.lower() in ("1", "true", "yes", "on")


def is_coordinator_mode() -> bool:
    """Check if coordinator mode is enabled."""
    return is_env_truthy(os.environ.get("CLAUDE_CODE_COORDINATOR_MODE"))


def match_session_mode(session_mode: Optional[str]) -> Optional[str]:
    """Check if current coordinator mode matches session's stored mode."""
    if not session_mode:
        return None

    current_is_coordinator = is_coordinator_mode()
    session_is_coordinator = session_mode == "coordinator"

    if current_is_coordinator == session_is_coordinator:
        return None

    if session_is_coordinator:
        os.environ["CLAUDE_CODE_COORDINATOR_MODE"] = "1"
    else:
        os.environ.pop("CLAUDE_CODE_COORDINATOR_MODE", None)

    return (
        "Entered coordinator mode to match resumed session."
        if session_is_coordinator
        else "Exited coordinator mode to match resumed session."
    )


def get_coordinator_user_context(
    mcp_clients: Optional[List[Dict[str, str]]] = None,
    scratchpad_dir: Optional[str] = None,
    is_scratchpad_enabled: bool = False,
) -> Dict[str, str]:
    """Get coordinator user context for system prompt."""
    if not is_coordinator_mode():
        return {}

    if is_env_truthy(os.environ.get("CLAUDE_CODE_SIMPLE")):
        worker_tools_str = "Bash, Edit, Read"
    else:
        worker_tools = sorted([
            t for t in ASYNC_AGENT_ALLOWED_TOOLS
            if t not in INTERNAL_WORKER_TOOLS
        ])
        worker_tools_str = ", ".join(worker_tools)

    content = f"Workers spawned via the {AGENT_TOOL_NAME} tool have access to these tools: {worker_tools_str}"

    if mcp_clients and len(mcp_clients) > 0:
        server_names = ", ".join([c.get("name", "") for c in mcp_clients])
        content += f"\n\nWorkers also have access to MCP tools from connected MCP servers: {server_names}"

    if scratchpad_dir and is_scratchpad_enabled:
        content += f"\n\nScratchpad directory: {scratchpad_dir}\nWorkers can read and write here without permission prompts."

    return {"workerToolsContext": content}


COORDINATOR_SYSTEM_PROMPT_TEMPLATE = """You are Claude Code, an AI assistant that orchestrates software engineering tasks across multiple workers.

## 1. Your Role

You are a **coordinator**. Your job is to:
- Help the user achieve their goal
- Direct workers to research, implement and verify code changes
- Synthesize results and communicate with the user
- Answer questions directly when possible

Every message you send is to the user. Worker results and system notifications are internal signals.

## 2. Your Tools

- **Agent** - Spawn a new worker
- **SendMessage** - Continue an existing worker
- **TaskStop** - Stop a running worker

### Agent Results

Worker results arrive as user-role messages containing task-notification XML:
- task-id: the agent ID to continue with SendMessage
- status: completed, failed, or killed
- summary: human-readable outcome
- result: agent's final response (optional)

## 3. Workers

{worker_capabilities}

## 4. Task Workflow

| Phase | Who | Purpose |
|-------|-----|---------|
| Research | Workers (parallel) | Investigate codebase |
| Synthesis | Coordinator | Understand and plan |
| Implementation | Workers | Make changes |
| Verification | Workers | Test changes |

### Concurrency

Launch independent workers concurrently. Read-only tasks run in parallel freely.
Write-heavy tasks: one at a time per file set.

## 5. Writing Worker Prompts

Workers can't see your conversation. Every prompt must be self-contained.

### Prompt tips

Good examples:
- "Fix the null pointer in src/auth/validate.ts:42. Add null check before user.id access. Commit and report hash."
- "Create branch 'fix/session-expiry' from main. Cherry-pick abc123. Push and create draft PR."

Bad examples:
- "Fix the bug we discussed" — no context
- "Based on your findings, implement the fix" — lazy delegation
"""


def get_coordinator_system_prompt() -> str:
    """Get the coordinator system prompt."""
    worker_capabilities = (
        "Workers have access to Bash, Read, and Edit tools, plus MCP tools."
        if is_env_truthy(os.environ.get("CLAUDE_CODE_SIMPLE"))
        else "Workers have access to standard tools, MCP tools, and skills via Skill tool."
    )

    return COORDINATOR_SYSTEM_PROMPT_TEMPLATE.replace(
        "{worker_capabilities}", worker_capabilities
    )


__all__ = [
    "is_coordinator_mode",
    "match_session_mode",
    "get_coordinator_user_context",
    "get_coordinator_system_prompt",
    "AGENT_TOOL_NAME",
    "BASH_TOOL_NAME",
    "FILE_READ_TOOL_NAME",
    "FILE_EDIT_TOOL_NAME",
    "SEND_MESSAGE_TOOL_NAME",
    "TASK_STOP_TOOL_NAME",
    "ASYNC_AGENT_ALLOWED_TOOLS",
    "INTERNAL_WORKER_TOOLS",
]