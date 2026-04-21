"""Help Command - Show help information."""

from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class HelpSection:
    """Help section."""
    title: str
    commands: List[str]
    description: str = ""


HELP_CONTENT = [
    HelpSection(
        title="Core Commands",
        commands=["ask", "init", "config", "doctor"],
        description="Essential Claude Code commands",
    ),
    HelpSection(
        title="Git Commands",
        commands=["commit", "review", "branch", "diff"],
        description="Git workflow commands",
    ),
    HelpSection(
        title="Session Commands",
        commands=["resume", "export", "import", "clear"],
        description="Session management",
    ),
    HelpSection(
        title="Info Commands",
        commands=["stats", "insights", "usage", "cost"],
        description="Information and analytics",
    ),
    HelpSection(
        title="Tool Commands",
        commands=["tools", "permissions", "hooks"],
        description="Tool and permission management",
    ),
]

TOOL_HELP = """
# Tool Usage

## File Tools
- Read: Read file contents
- Write: Write to file
- Edit: Edit file with find/replace
- Glob: Find files by pattern
- Grep: Search file contents

## Execution Tools
- Bash: Run shell commands
- PowerShell: Run PowerShell (Windows)
- Agent: Spawn sub-agents

## Web Tools
- WebFetch: Fetch web content
- WebSearch: Search the web

## Task Tools
- TaskCreate/Update/List/Get: Task management
- TaskOutput: Get task output
- TaskStop: Cancel task

## Other Tools
- AskUserQuestion: Ask user for input
- Skill: Invoke skill
- NotebookEdit: Edit Jupyter notebooks
"""


async def run_help(topic: str = "general") -> Dict[str, Any]:
    """Show help."""
    if topic == "tools":
        return {
            "success": True,
            "content": TOOL_HELP,
            "topic": "tools",
        }
    
    elif topic == "commands":
        lines = ["# Available Commands", ""]
        for section in HELP_CONTENT:
            lines.append(f"## {section.title}")
            lines.append(f"{section.description}")
            lines.append("")
            for cmd in section.commands:
                lines.append(f"- `{cmd}`")
            lines.append("")
        
        return {
            "success": True,
            "content": "\n".join(lines),
            "topic": "commands",
        }
    
    else:
        general_help = """
# Claude Code Help

Claude Code is an AI-powered coding assistant CLI.

## Quick Start
1. Run `cc init` to initialize a project
2. Ask questions with `cc ask "your question"`
3. Use `cc help commands` for all commands

## Key Features
- File operations: read, write, edit files
- Git integration: commit, review, branch management
- Web search: search and fetch web content
- Sub-agents: spawn specialized agents
- Skills: invoke predefined skills

## Getting Started
- `cc --help` - CLI help
- `cc help tools` - Tool documentation
- `cc help commands` - Command list
"""
        return {
            "success": True,
            "content": general_help,
            "topic": "general",
        }


class HelpCommand:
    """Help command implementation."""
    
    name = "help"
    description = "Show help information"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute help command."""
        topic = args.get("topic", "general")
        return await run_help(topic)


__all__ = [
    "HelpSection",
    "HELP_CONTENT",
    "TOOL_HELP",
    "run_help",
    "HelpCommand",
]
