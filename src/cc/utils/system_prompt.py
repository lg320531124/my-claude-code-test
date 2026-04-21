"""System Prompt Builder - Build system prompts for Claude."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .claude_md import load_claude_md_context, extract_instructions
from .async_io import read_file_async, exists_async


class SystemPromptBuilder:
    """Build system prompts with context."""

    def __init__(self, cwd: Path):
        self.cwd = cwd
        self._claude_md_loaded = False
        self._claude_md_content = None

    async def load_context(self) -> None:
        """Load CLAUDE.md context."""
        self._claude_md_content = await load_claude_md_context(self.cwd)
        self._claude_md_loaded = True

    async def build(
        self,
        additional_context: Dict[str, Any] = None,
        tools_description: str = None,
        extended_thinking: bool = False,
    ) -> str:
        """Build complete system prompt."""
        sections = []

        # Core identity
        sections.append(self._build_identity())

        # Current date
        sections.append(self._build_date_context())

        # Tools description
        if tools_description:
            sections.append(self._build_tools_section(tools_description))

        # Extended thinking
        if extended_thinking:
            sections.append(self._build_thinking_section())

        # CLAUDE.md context
        if not self._claude_md_loaded:
            await self.load_context()

        if self._claude_md_content:
            sections.append(self._build_claude_md_section())

        # Additional context
        if additional_context:
            sections.append(self._build_additional_section(additional_context))

        return "\n\n---\n\n".join(sections)

    def _build_identity(self) -> str:
        """Build identity section."""
        return """You are Claude Code, Anthropic's official CLI for Claude.
You are an interactive agent that helps users with software engineering tasks.
Use the instructions below and the tools available to you to assist the user.

IMPORTANT: Assist with authorized security testing, defensive security, CTF challenges, and educational contexts.
Refuse requests for destructive techniques, DoS attacks, mass targeting, supply chain compromise, or detection evasion for malicious purposes.

# System
 - All text you output outside of tool use is displayed to the user.
 - Tools are executed in a user-selected permission mode.
 - Users may configure 'hooks', shell commands that execute in response to events."""

    def _build_date_context(self) -> str:
        """Build date context."""
        now = datetime.now()
        return f"# currentDate\nToday's date is {now.strftime('%Y/%m/%d')}.\n\nIMPORTANT: this context may or may not be relevant to your tasks."

    def _build_tools_section(self, tools_description: str) -> str:
        """Build tools section."""
        return f"""# Tools\n\nYou have access to these tools:\n\n{tools_description}\n\nWhen using tools, follow these guidelines:
 - Prefer dedicated tools over Bash when one fits.
 - Use TaskCreate to plan and track work.
 - Mark each task completed as soon as it's done."""

    def _build_thinking_section(self) -> str:
        """Build extended thinking section."""
        return """# Extended Thinking

Extended thinking is enabled by default, reserving up to 31,999 tokens for internal reasoning.

Control extended thinking via:
- **Toggle**: Option+T (macOS) / Alt+T (Windows/Linux)
- **Config**: Set `alwaysThinkingEnabled` in settings
- **Budget cap**: `export MAX_THINKING_TOKENS=10000`"""

    def _build_claude_md_section(self) -> str:
        """Build CLAUDE.md section."""
        return f"""# ClaudeMd\n\nCodebase and user instructions:\n\n{self._claude_md_content}"""

    def _build_additional_section(self, context: Dict[str, Any]) -> str:
        """Build additional context section."""
        lines = ["# Additional Context\n"]

        for key, value in context.items():
            lines.append(f"\n**{key}:**\n{value}")

        return "\n".join(lines)


async def build_system_prompt(
    cwd: Path,
    tools_description: str = None,
    extended_thinking: bool = False,
    additional_context: Dict[str, Any] = None,
) -> str:
    """Build system prompt for session."""
    builder = SystemPromptBuilder(cwd)
    return await builder.build(
        additional_context=additional_context,
        tools_description=tools_description,
        extended_thinking=extended_thinking,
    )


def get_default_tools_description() -> str:
    """Get default tools description."""
    return """Available tools:
- BashTool: Execute shell commands
- ReadTool: Read files
- WriteTool: Write files
- EditTool: Edit files
- GlobTool: Find files by pattern
- GrepTool: Search file contents
- WebFetchTool: Fetch web content
- WebSearchTool: Search the web
- AgentTool: Run specialized agents
- TaskCreateTool: Create tasks
- TaskUpdateTool: Update tasks
- AskUserQuestionTool: Ask user questions"""


__all__ = [
    "SystemPromptBuilder",
    "build_system_prompt",
    "get_default_tools_description",
]