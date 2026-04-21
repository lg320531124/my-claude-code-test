"""Claude.md Parser - Parse CLAUDE.md files for context."""

from __future__ import annotations
import asyncio
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .async_io import read_file_async, exists_async


@dataclass
class ClaudeMDSection:
    """Section from CLAUDE.md file."""
    title: str
    content: str
    level: int  # Heading level
    children: List["ClaudeMDSection"] = field(default_factory=list)


@dataclass
class ClaudeMDContent:
    """Parsed CLAUDE.md content."""
    path: Path
    sections: List[ClaudeMDSection]
    raw_content: str
    directives: Dict[str, Any]  # Special directives like @include


async def parse_claude_md(path: Path) -> ClaudeMDContent:
    """Parse a CLAUDE.md file asynchronously."""
    if not await exists_async(path):
        return ClaudeMDContent(
            path=path,
            sections=[],
            raw_content="",
            directives={},
        )

    content = await read_file_async(path)
    return parse_claude_md_content(content, path)


def parse_claude_md_content(content: str, path: Path) -> ClaudeMDContent:
    """Parse CLAUDE.md content."""
    sections = []
    directives = {}

    # Parse directives
    directive_pattern = re.compile(r"@(\w+)\s+(.+)")
    for match in directive_pattern.finditer(content):
        directive_name = match.group(1)
        directive_value = match.group(2)
        directives[directive_name] = directive_value

    # Parse sections (markdown headings)
    lines = content.split("\n")
    current_section = None
    section_content = []

    for line in lines:
        heading_match = re.match(r"^#{1,6}\s+(.+)", line)
        if heading_match:
            # Save previous section
            if current_section:
                current_section.content = "\n".join(section_content)
                sections.append(current_section)

            # Start new section
            level = len(line) - len(line.lstrip("#"))
            title = heading_match.group(1)
            current_section = ClaudeMDSection(
                title=title,
                content="",
                level=level,
                children=[],
            )
            section_content = []
        elif current_section:
            section_content.append(line)

    # Save last section
    if current_section:
        current_section.content = "\n".join(section_content)
        sections.append(current_section)

    return ClaudeMDContent(
        path=path,
        sections=sections,
        raw_content=content,
        directives=directives,
    )


async def find_claude_md_files(cwd: Path) -> List[Path]:
    """Find all CLAUDE.md files in directory."""
    files = []

    # Check common locations
    locations = [
        cwd / "CLAUDE.md",
        cwd / ".claude" / "CLAUDE.md",
        cwd / "docs" / "CLAUDE.md",
        cwd / ".github" / "CLAUDE.md",
    ]

    for location in locations:
        if await exists_async(location):
            files.append(location)

    return files


async def load_claude_md_context(cwd: Path) -> str:
    """Load CLAUDE.md context for session."""
    files = await find_claude_md_files(cwd)

    if not files:
        return ""

    contents = []
    for file in files:
        parsed = await parse_claude_md(file)

        # Process @include directives
        for directive_name, directive_value in parsed.directives.items():
            if directive_name == "include":
                include_path = cwd / directive_value
                if await exists_async(include_path):
                    include_content = await read_file_async(include_path)
                    contents.append(f"[Included: {directive_value}]\n{include_content}")

        # Add main content
        if parsed.raw_content:
            contents.append(f"[{file}]\n{parsed.raw_content}")

    return "\n\n---\n\n".join(contents)


def extract_instructions(content: ClaudeMDContent) -> Dict[str, str]:
    """Extract specific instructions from CLAUDE.md."""
    instructions = {}

    instruction_patterns = {
        "coding_style": r"coding style|style guide|code style",
        "testing": r"testing|test strategy|tests",
        "git_workflow": r"git|workflow|commit",
        "architecture": r"architecture|structure|design",
    }

    for section in content.sections:
        for key, pattern in instruction_patterns.items():
            if re.search(pattern, section.title.lower()):
                instructions[key] = section.content

    return instructions


__all__ = [
    "ClaudeMDSection",
    "ClaudeMDContent",
    "parse_claude_md",
    "parse_claude_md_content",
    "find_claude_md_files",
    "load_claude_md_context",
    "extract_instructions",
]