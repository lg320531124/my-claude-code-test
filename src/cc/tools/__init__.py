"""Tool system."""

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

__all__ = [
    "BashTool",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "GlobTool",
    "GrepTool",
    "WebFetchTool",
    "WebSearchTool",
    "AgentTool",
    "AGENT_TYPES",
    "TaskCreateTool",
    "TaskUpdateTool",
    "TaskListTool",
    "TaskGetTool",
    "get_default_tools",
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
    ]