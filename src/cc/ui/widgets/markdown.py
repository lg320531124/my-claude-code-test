"""Markdown Widget - Markdown rendering."""

from __future__ import annotations
import re
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class MarkdownElement(Enum):
    """Markdown element types."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    CODE_INLINE = "code_inline"
    LIST = "list"
    LIST_ITEM = "list_item"
    LINK = "link"
    IMAGE = "image"
    TABLE = "table"
    BLOCKQUOTE = "blockquote"
    HR = "hr"
    STRONG = "strong"
    EM = "em"
    TEXT = "text"


@dataclass
class MarkdownNode:
    """Markdown AST node."""
    type: MarkdownElement
    content: str = ""
    level: int = 0  # For headings
    children: List[MarkdownNode] = field(default_factory=list)
    attrs: Dict[str, str] = field(default_factory=dict)


@dataclass
class MarkdownConfig:
    """Markdown configuration."""
    max_width: int = 80
    show_links: bool = True
    render_images: bool = False
    heading_style: str = "bold"
    code_theme: str = "dark"


class MarkdownRenderer:
    """Markdown renderer widget."""

    def __init__(self, config: MarkdownConfig = None):
        self._config = config or MarkdownConfig()
        self._root: Optional[MarkdownNode] = None
        self._link_click_callback: Optional[Callable] = None

    def parse(self, text: str) -> MarkdownNode:
        """Parse markdown text.

        Args:
            text: Markdown text

        Returns:
            Root MarkdownNode
        """
        self._root = MarkdownNode(type=MarkdownElement.TEXT, children=[])

        lines = text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Heading
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                content = line.lstrip("#").strip()
                self._root.children.append(MarkdownNode(
                    type=MarkdownElement.HEADING,
                    content=content,
                    level=level,
                ))
                i += 1
                continue

            # Code block
            if line.startswith("```"):
                lang = line[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1

                self._root.children.append(MarkdownNode(
                    type=MarkdownElement.CODE_BLOCK,
                    content="\n".join(code_lines),
                    attrs={"language": lang},
                ))
                i += 1
                continue

            # Blockquote
            if line.startswith(">"):
                content = line.lstrip(">").strip()
                self._root.children.append(MarkdownNode(
                    type=MarkdownElement.BLOCKQUOTE,
                    content=content,
                ))
                i += 1
                continue

            # HR
            if re.match(r"^[-*_]{3,}$", line):
                self._root.children.append(MarkdownNode(type=MarkdownElement.HR))
                i += 1
                continue

            # List
            if re.match(r"^\s*[-*+] ", line) or re.match(r"^\s*\d+\.", line):
                list_items = []
                while i < len(lines):
                    list_line = lines[i]
                    if re.match(r"^\s*[-*+] ", list_line):
                        content = list_line.lstrip(" ")[2:].strip()
                        list_items.append(MarkdownNode(
                            type=MarkdownElement.LIST_ITEM,
                            content=content,
                            attrs={"ordered": "false"},
                        ))
                    elif re.match(r"^\s*\d+\.", list_line):
                        content = re.sub(r"^\s*\d+\.", "", list_line).strip()
                        list_items.append(MarkdownNode(
                            type=MarkdownElement.LIST_ITEM,
                            content=content,
                            attrs={"ordered": "true"},
                        ))
                    else:
                        break
                    i += 1

                self._root.children.append(MarkdownNode(
                    type=MarkdownElement.LIST,
                    children=list_items,
                ))
                continue

            # Table
            if "|" in line and i + 1 < len(lines) and re.match(r"^\s*[|:-]+\s*$", lines[i + 1]):
                headers = [h.strip() for h in line.split("|") if h.strip()]
                rows = []
                i += 2  # Skip separator

                while i < len(lines) and "|" in lines[i]:
                    cells = [c.strip() for c in lines[i].split("|") if c.strip()]
                    rows.append(cells)
                    i += 1

                self._root.children.append(MarkdownNode(
                    type=MarkdownElement.TABLE,
                    children=[],
                    attrs={"headers": headers, "rows": rows},
                ))
                continue

            # Paragraph
            if line.strip():
                # Collect paragraph lines
                para_lines = []
                while i < len(lines) and lines[i].strip():
                    para_lines.append(lines[i])
                    i += 1

                self._root.children.append(MarkdownNode(
                    type=MarkdownElement.PARAGRAPH,
                    content=" ".join(para_lines),
                ))
                continue

            # Empty line
            i += 1

        return self._root

    def render(self, node: MarkdownNode = None) -> str:
        """Render markdown to formatted string.

        Args:
            node: Node to render (None for root)

        Returns:
            Rendered string
        """
        if node is None:
            node = self._root

        if node is None:
            return ""

        return self._render_node(node)

    def _render_node(self, node: MarkdownNode) -> str:
        """Render single node."""
        output = []

        if node.type == MarkdownElement.HEADING:
            style = "bold" if self._config.heading_style == "bold" else ""
            prefix = "#" * node.level
            output.append(f"[{style}]{prefix} {self._render_inline(node.content)}[/]")

        elif node.type == MarkdownElement.PARAGRAPH:
            output.append(self._render_inline(node.content))

        elif node.type == MarkdownElement.CODE_BLOCK:
            lang = node.attrs.get("language", "")
            output.append(f"[dim]{lang}[/]")
            output.append(node.content)
            output.append("")

        elif node.type == MarkdownElement.CODE_INLINE:
            output.append(f"[green]`{node.content}`[/]")

        elif node.type == MarkdownElement.BLOCKQUOTE:
            output.append(f"[dim]> {self._render_inline(node.content)}[/]")

        elif node.type == MarkdownElement.LIST:
            for item in node.children:
                marker = "• " if item.attrs.get("ordered") == "false" else "1. "
                output.append(f"  {marker}{self._render_inline(item.content)}")

        elif node.type == MarkdownElement.TABLE:
            headers = node.attrs.get("headers", [])
            rows = node.attrs.get("rows", [])

            if headers:
                header_str = " | ".join(headers)
                output.append(f"[bold]{header_str}[/]")
                output.append("-" * len(header_str))

            for row in rows:
                output.append(" | ".join(row))

        elif node.type == MarkdownElement.HR:
            output.append("---")

        elif node.type == MarkdownElement.TEXT:
            for child in node.children:
                output.append(self._render_node(child))

        return "\n".join(output)

    def _render_inline(self, text: str) -> str:
        """Render inline elements.

        Args:
            text: Text with inline markdown

        Returns:
            Rendered string
        """
        # Bold
        text = re.sub(r"\*\*([^*]+)\*\*", r"[bold]\1[/]", text)
        text = re.sub(r"__([^_]+)__", r"[bold]\1[/]", text)

        # Italic
        text = re.sub(r"\*([^*]+)\*", r"[italic]\1[/]", text)
        text = re.sub(r"_([^_]+)_", r"[italic]\1[/]", text)

        # Code inline
        text = re.sub(r"`([^`]+)`", r"[green]`\1`[/]", text)

        # Links
        if self._config.show_links:
            text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"[cyan]\1[/] ([dim]\2[/])", text)

        # Images
        if self._config.render_images:
            text = re.sub(r"!\[([^\]]+)\]\(([^\)]+)\)", r"[italic][image: \1][/]", text)

        return text

    def set_link_click_callback(self, callback: Callable) -> None:
        """Set link click callback."""
        self._link_click_callback = callback

    async def click_link(self, url: str) -> None:
        """Handle link click."""
        if self._link_click_callback:
            try:
                await self._link_click_callback(url)
            except Exception:
                pass


# Global renderer
_renderer: Optional[MarkdownRenderer] = None


def get_markdown_renderer(config: MarkdownConfig = None) -> MarkdownRenderer:
    """Get global renderer."""
    global _renderer
    if _renderer is None:
        _renderer = MarkdownRenderer(config)
    return _renderer


def render_markdown(text: str, config: MarkdownConfig = None) -> str:
    """Render markdown text."""
    renderer = get_markdown_renderer(config)
    renderer.parse(text)
    return renderer.render()


__all__ = [
    "MarkdownElement",
    "MarkdownNode",
    "MarkdownConfig",
    "MarkdownRenderer",
    "get_markdown_renderer",
    "render_markdown",
]
