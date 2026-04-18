"""Tool system - All available tools."""

from .bash import BashTool
from .read import ReadTool
from .write import WriteTool
from .edit import EditTool
from .glob import GlobTool
from .grep import GrepTool
from .web_fetch import WebFetchTool
from .web_search import WebSearchTool
from .agent import AgentTool, AGENT_TYPES
from .task import TaskCreateTool, TaskUpdateTool, TaskListTool, TaskGetTool
from .ask_user import AskUserQuestionTool
from .skill import SkillTool
from .notebook import NotebookEditTool
from .plan_worktree import EnterPlanModeTool, ExitPlanModeTool, EnterWorktreeTool, ExitWorktreeTool
from .todo import TodoWriteTool, get_todos, update_todo_status, clear_todos
from .lsp import LSPTool
from .mcp_tool import MCPTool, ListMcpResourcesTool, ReadMcpResourceTool

__all__ = [
    # Core tools
    "BashTool",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "GlobTool",
    "GrepTool",
    # Web tools
    "WebFetchTool",
    "WebSearchTool",
    # Agent tools
    "AgentTool",
    "AGENT_TYPES",
    # Task tools
    "TaskCreateTool",
    "TaskUpdateTool",
    "TaskListTool",
    "TaskGetTool",
    # Interactive tools
    "AskUserQuestionTool",
    "SkillTool",
    # Notebook tools
    "NotebookEditTool",
    # Plan/Worktree tools
    "EnterPlanModeTool",
    "ExitPlanModeTool",
    "EnterWorktreeTool",
    "ExitWorktreeTool",
    # Todo tools
    "TodoWriteTool",
    "get_todos",
    "update_todo_status",
    "clear_todos",
    # LSP tools
    "LSPTool",
    # MCP tools
    "MCPTool",
    "ListMcpResourcesTool",
    "ReadMcpResourceTool",
    # Utility
    "get_default_tools",
    "get_all_tools",
]


def get_default_tools() -> list:
    """Get default tool set for a session."""
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
    ]


def get_all_tools() -> list:
    """Get all available tools."""
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
        NotebookEditTool(),
        EnterPlanModeTool(),
        ExitPlanModeTool(),
        EnterWorktreeTool(),
        ExitWorktreeTool(),
        TodoWriteTool(),
        LSPTool(),
        MCPTool(),
        ListMcpResourcesTool(),
        ReadMcpResourceTool(),
    ]