"""Tool Constants - Tool names and allowed/disallowed sets.

Defines tool name constants and which tools are available to different
agent types (async agents, teammates, coordinator mode).
"""

from __future__ import annotations
from typing import Set

# Tool name constants
AGENT_TOOL_NAME = "Agent"
BASH_TOOL_NAME = "Bash"
FILE_READ_TOOL_NAME = "Read"
FILE_EDIT_TOOL_NAME = "Edit"
FILE_WRITE_TOOL_NAME = "Write"
GLOB_TOOL_NAME = "Glob"
GREP_TOOL_NAME = "Grep"
WEB_SEARCH_TOOL_NAME = "WebSearch"
WEB_FETCH_TOOL_NAME = "WebFetch"
TODO_WRITE_TOOL_NAME = "TodoWrite"
NOTEBOOK_EDIT_TOOL_NAME = "NotebookEdit"
SKILL_TOOL_NAME = "Skill"
ASK_USER_QUESTION_TOOL_NAME = "AskUserQuestion"
TASK_CREATE_TOOL_NAME = "TaskCreate"
TASK_GET_TOOL_NAME = "TaskGet"
TASK_LIST_TOOL_NAME = "TaskList"
TASK_UPDATE_TOOL_NAME = "TaskUpdate"
TASK_STOP_TOOL_NAME = "TaskStop"
SEND_MESSAGE_TOOL_NAME = "SendMessage"
SYNTHETIC_OUTPUT_TOOL_NAME = "SyntheticOutput"
ENTER_WORKTREE_TOOL_NAME = "EnterWorktree"
EXIT_WORKTREE_TOOL_NAME = "ExitWorktree"
ENTER_PLAN_MODE_TOOL_NAME = "EnterPlanMode"
EXIT_PLAN_MODE_TOOL_NAME = "ExitPlanMode"
TASK_OUTPUT_TOOL_NAME = "TaskOutput"
WORKFLOW_TOOL_NAME = "Workflow"
CRON_CREATE_TOOL_NAME = "CronCreate"
CRON_DELETE_TOOL_NAME = "CronDelete"
CRON_LIST_TOOL_NAME = "CronList"
TOOL_SEARCH_TOOL_NAME = "ToolSearch"

# Shell tool names (used by Bash)
SHELL_TOOL_NAMES: Set[str] = {BASH_TOOL_NAME}


def get_all_agent_disallowed_tools(user_type: str = None) -> Set[str]:
    """Get tools disallowed for all agents.

    Args:
        user_type: Optional user type ('ant' allows nested agents)

    Returns:
        Set of disallowed tool names
    """
    tools = {
        TASK_OUTPUT_TOOL_NAME,
        EXIT_PLAN_MODE_TOOL_NAME,
        ENTER_PLAN_MODE_TOOL_NAME,
        ASK_USER_QUESTION_TOOL_NAME,
        TASK_STOP_TOOL_NAME,
    }

    # Allow Agent tool for ant users (enables nested agents)
    if user_type != "ant":
        tools.add(AGENT_TOOL_NAME)

    return tools


def get_async_agent_allowed_tools() -> Set[str]:
    """Get tools allowed for async agents.

    These tools can be used by spawned worker agents.

    Returns:
        Set of allowed tool names
    """
    return {
        FILE_READ_TOOL_NAME,
        WEB_SEARCH_TOOL_NAME,
        TODO_WRITE_TOOL_NAME,
        GREP_TOOL_NAME,
        WEB_FETCH_TOOL_NAME,
        GLOB_TOOL_NAME,
        BASH_TOOL_NAME,
        FILE_EDIT_TOOL_NAME,
        FILE_WRITE_TOOL_NAME,
        NOTEBOOK_EDIT_TOOL_NAME,
        SKILL_TOOL_NAME,
        SYNTHETIC_OUTPUT_TOOL_NAME,
        TOOL_SEARCH_TOOL_NAME,
        ENTER_WORKTREE_TOOL_NAME,
        EXIT_WORKTREE_TOOL_NAME,
    }


def get_in_process_teammate_allowed_tools(
    enable_agent_triggers: bool = False
) -> Set[str]:
    """Get tools allowed for in-process teammates.

    These are additional tools beyond async_agent_allowed_tools.

    Args:
        enable_agent_triggers: If True, include cron tools

    Returns:
        Set of allowed tool names
    """
    tools = {
        TASK_CREATE_TOOL_NAME,
        TASK_GET_TOOL_NAME,
        TASK_LIST_TOOL_NAME,
        TASK_UPDATE_TOOL_NAME,
        SEND_MESSAGE_TOOL_NAME,
    }

    if enable_agent_triggers:
        tools.update({
            CRON_CREATE_TOOL_NAME,
            CRON_DELETE_TOOL_NAME,
            CRON_LIST_TOOL_NAME,
        })

    return tools


def get_coordinator_mode_allowed_tools() -> Set[str]:
    """Get tools allowed in coordinator mode.

    Coordinator mode only has output and agent management tools.

    Returns:
        Set of allowed tool names
    """
    return {
        AGENT_TOOL_NAME,
        TASK_STOP_TOOL_NAME,
        SEND_MESSAGE_TOOL_NAME,
        SYNTHETIC_OUTPUT_TOOL_NAME,
    }


# Pre-computed default sets
ALL_AGENT_DISALLOWED_TOOLS: Set[str] = get_all_agent_disallowed_tools()
ASYNC_AGENT_ALLOWED_TOOLS: Set[str] = get_async_agent_allowed_tools()
IN_PROCESS_TEAMMATE_ALLOWED_TOOLS: Set[str] = get_in_process_teammate_allowed_tools()
COORDINATOR_MODE_ALLOWED_TOOLS: Set[str] = get_coordinator_mode_allowed_tools()


__all__ = [
    # Tool names
    "AGENT_TOOL_NAME",
    "BASH_TOOL_NAME",
    "FILE_READ_TOOL_NAME",
    "FILE_EDIT_TOOL_NAME",
    "FILE_WRITE_TOOL_NAME",
    "GLOB_TOOL_NAME",
    "GREP_TOOL_NAME",
    "WEB_SEARCH_TOOL_NAME",
    "WEB_FETCH_TOOL_NAME",
    "TODO_WRITE_TOOL_NAME",
    "NOTEBOOK_EDIT_TOOL_NAME",
    "SKILL_TOOL_NAME",
    "ASK_USER_QUESTION_TOOL_NAME",
    "TASK_CREATE_TOOL_NAME",
    "TASK_GET_TOOL_NAME",
    "TASK_LIST_TOOL_NAME",
    "TASK_UPDATE_TOOL_NAME",
    "TASK_STOP_TOOL_NAME",
    "SEND_MESSAGE_TOOL_NAME",
    "SYNTHETIC_OUTPUT_TOOL_NAME",
    "ENTER_WORKTREE_TOOL_NAME",
    "EXIT_WORKTREE_TOOL_NAME",
    "ENTER_PLAN_MODE_TOOL_NAME",
    "EXIT_PLAN_MODE_TOOL_NAME",
    "TASK_OUTPUT_TOOL_NAME",
    "WORKFLOW_TOOL_NAME",
    "CRON_CREATE_TOOL_NAME",
    "CRON_DELETE_TOOL_NAME",
    "CRON_LIST_TOOL_NAME",
    "TOOL_SEARCH_TOOL_NAME",
    "SHELL_TOOL_NAMES",
    # Functions
    "get_all_agent_disallowed_tools",
    "get_async_agent_allowed_tools",
    "get_in_process_teammate_allowed_tools",
    "get_coordinator_mode_allowed_tools",
    # Pre-computed sets
    "ALL_AGENT_DISALLOWED_TOOLS",
    "ASYNC_AGENT_ALLOWED_TOOLS",
    "IN_PROCESS_TEAMMATE_ALLOWED_TOOLS",
    "COORDINATOR_MODE_ALLOWED_TOOLS",
]