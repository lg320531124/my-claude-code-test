"""Tool system - All available tools."""

from __future__ import annotations
from .bash import BashTool
from .read import ReadTool
from .write import WriteTool
from .edit import EditTool
from .glob import GlobTool
from .grep import GrepTool
from .web_fetch import WebFetchTool
from .web_search import WebSearchTool
from .agent import AgentTool, AgentExecutor, AgentResult, AGENT_TYPES, get_agent_types, run_agent
from .task import TaskCreateTool, TaskUpdateTool, TaskListTool, TaskGetTool
from .ask_user import AskUserQuestionTool
from .skill import SkillTool
from .skill_system import SkillLoader, SkillExecutor, SkillManager, get_skill_manager, initialize_skills
from .notebook import NotebookEditTool, read_notebook, read_notebook_async
from .plan_worktree import EnterPlanModeTool, ExitPlanModeTool, EnterWorktreeTool, ExitWorktreeTool
from .todo import TodoWriteTool, get_todos, update_todo_status, clear_todos
from .lsp import LSPTool, LSPClient, LSPManager, get_lsp_manager, close_lsp
from .mcp_tool import MCPTool, ListMcpResourcesTool, ReadMcpResourceTool
from .schedule import (
    CronCreateTool,
    ScheduleWakeupTool,
    RemoteTriggerTool,
    CronScheduler,
    ScheduledJob,
    get_scheduler,
    start_scheduler,
    stop_scheduler,
    list_scheduled_jobs,
)
# New tools
from .brief import BriefTool, BriefInput
from .config_tool import ConfigTool, ConfigInput
from .sleep import SleepTool, SleepInput
from .remote_trigger import RemoteTriggerTool, RemoteTriggerInput
from .synthetic_output import SyntheticOutputTool, SyntheticInput
from .powershell import PowerShellTool, PowerShellInput
from .output import OutputTool, OutputInput
from .file_ops import MoveTool, MoveInput, CopyTool, CopyInput, DeleteTool, DeleteInput
from .list_files import ListFilesTool, ListFilesInput, FileInfo
from .image import ImageTool, ImageInput, ImageResult
from .pdf import PDFTool, PDFInput
from .diff import DiffTool, DiffInput
from .history import HistoryTool, HistoryInput, HistoryEntry
from .process import ProcessTool, ProcessInput, ProcessInfo
# Additional tools
from .environment import EnvironmentTool, EnvironmentInput
from .checksum import ChecksumTool, ChecksumInput
from .archive import ArchiveTool, ArchiveInput
from .code import CodeTool, CodeInput, CodeAnalysis
from .network import NetworkTool, NetworkInput
from .timer import TimerTool, TimerInput, TimerResult
from .template import TemplateTool, TemplateInput
from .json_tool import JSONTool, JSONInput
from .xml import XMLTool, XMLInput
from .regex import RegexTool, RegexInput, RegexMatch
from .url import URLTool, URLInput, URLInfo

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
    "AgentExecutor",
    "AgentResult",
    "AGENT_TYPES",
    "get_agent_types",
    "run_agent",
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
    "read_notebook",
    "read_notebook_async",
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
    # Schedule tools
    "CronCreateTool",
    "ScheduleWakeupTool",
    "RemoteTriggerTool",
    "CronScheduler",
    "ScheduledJob",
    "get_scheduler",
    "start_scheduler",
    "stop_scheduler",
    "list_scheduled_jobs",
    # New tools
    "BriefTool",
    "BriefInput",
    "ConfigTool",
    "ConfigInput",
    "SleepTool",
    "SleepInput",
    "SyntheticOutputTool",
    "SyntheticInput",
    "PowerShellTool",
    "PowerShellInput",
    "OutputTool",
    "OutputInput",
    # File operations
    "MoveTool",
    "MoveInput",
    "CopyTool",
    "CopyInput",
    "DeleteTool",
    "DeleteInput",
    "ListFilesTool",
    "ListFilesInput",
    "FileInfo",
    # Media tools
    "ImageTool",
    "ImageInput",
    "ImageResult",
    "PDFTool",
    "PDFInput",
    # Utility tools
    "DiffTool",
    "DiffInput",
    "HistoryTool",
    "HistoryInput",
    "HistoryEntry",
    "ProcessTool",
    "ProcessInput",
    "ProcessInfo",
    # Additional tools
    "EnvironmentTool",
    "EnvironmentInput",
    "ChecksumTool",
    "ChecksumInput",
    "ArchiveTool",
    "ArchiveInput",
    "CodeTool",
    "CodeInput",
    "CodeAnalysis",
    "NetworkTool",
    "NetworkInput",
    "TimerTool",
    "TimerInput",
    "TimerResult",
    "TemplateTool",
    "TemplateInput",
    "JSONTool",
    "JSONInput",
    "XMLTool",
    "XMLInput",
    "RegexTool",
    "RegexInput",
    "RegexMatch",
    "URLTool",
    "URLInput",
    "URLInfo",
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
        CronCreateTool(),
        ScheduleWakeupTool(),
        RemoteTriggerTool(),
        # New tools
        BriefTool(),
        ConfigTool(),
        SleepTool(),
        SyntheticOutputTool(),
        PowerShellTool(),
        OutputTool(),
    ]
