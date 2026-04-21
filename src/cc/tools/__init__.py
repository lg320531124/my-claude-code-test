"""Tool system - All available tools."""

from __future__ import annotations

# Core tools
from .bash import BashTool
from .read import ReadTool
from .write import WriteTool
from .edit import EditTool
from .glob import GlobTool
from .grep import GrepTool
from .web_fetch import WebFetchTool
from .web_search import WebSearchTool
from .agent import AgentTool, AgentExecutor, AgentResult, AGENT_TYPES
from .task import TaskCreateTool, TaskUpdateTool, TaskListTool, TaskGetTool
from .ask_user import AskUserQuestionTool
from .skill import SkillTool
from .notebook import NotebookEditTool
from .plan_worktree import EnterPlanModeTool, ExitPlanModeTool, EnterWorktreeTool, ExitWorktreeTool
from .todo import TodoWriteTool
from .lsp import LSPTool
from .mcp_tool import MCPTool
from .schedule import CronCreateTool, get_scheduler

# New tools
from .task_output import TaskOutputTool, TaskOutputInput
from .task_stop import TaskStopTool, TaskStopInput
from .synthetic_output import SyntheticOutputTool, SyntheticInput
from .powershell import PowerShellTool, PowerShellInput
from .tool_search import ToolSearchTool, ToolSearchInput

# Shared utilities
from .shared import (
    PermissionChecker,
    ToolValidator,
    ToolContext,
    ToolExecutor,
)

__all__ = [
    # Core tools
    "BashTool",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "GlobTool",
    "GrepTool",
    "WebFetchTool",
    "WebSearchTool",
    "AgentTool",
    "AgentExecutor",
    "AgentResult",
    "AGENT_TYPES",
    "TaskCreateTool",
    "TaskUpdateTool",
    "TaskListTool",
    "TaskGetTool",
    "TaskOutputTool",
    "TaskOutputInput",
    "TaskStopTool",
    "TaskStopInput",
    "AskUserQuestionTool",
    "SkillTool",
    "NotebookEditTool",
    "EnterPlanModeTool",
    "ExitPlanModeTool",
    "EnterWorktreeTool",
    "ExitWorktreeTool",
    "TodoWriteTool",
    "LSPTool",
    "MCPTool",
    "CronCreateTool",
    "get_scheduler",
    "SyntheticOutputTool",
    "SyntheticInput",
    "PowerShellTool",
    "PowerShellInput",
    "ToolSearchTool",
    "ToolSearchInput",
    "PermissionChecker",
    "ToolValidator",
    "ToolContext",
    "ToolExecutor",
    "get_default_tools",
]


def get_default_tools() -> list:
    """Get default tool set."""
    return [
        BashTool(),
        ReadTool(),
        WriteTool(),
        EditTool(),
        GlobTool(),
        GrepTool(),
        WebFetchTool(),
        WebSearchTool(),
        AgentTool(),
        TaskCreateTool(),
        TaskUpdateTool(),
        TaskListTool(),
        TaskGetTool(),
        AskUserQuestionTool(),
        SkillTool(),
        TodoWriteTool(),
        TaskOutputTool(),
        TaskStopTool(),
    ]
