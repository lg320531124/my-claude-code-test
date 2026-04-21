"""Help Dialog - Help display."""

from __future__ import annotations
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ...utils.log import get_logger

logger = get_logger(__name__)


class HelpCategory(Enum):
    """Help categories."""
    GETTING_STARTED = "getting_started"
    COMMANDS = "commands"
    TOOLS = "tools"
    KEYBINDINGS = "keybindings"
    SETTINGS = "settings"
    TIPS = "tips"
    FAQ = "faq"


@dataclass
class HelpEntry:
    """Help entry."""
    title: str
    content: str
    category: HelpCategory
    tags: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)


@dataclass
class HelpDialogConfig:
    """Help dialog configuration."""
    show_search: bool = True
    show_categories: bool = True
    max_entries: int = 50
    width: int = 80


class HelpDialog:
    """Help display dialog."""

    def __init__(self, config: Optional[HelpDialogConfig] = None):
        self.config = config or HelpDialogConfig()
        self._entries: Dict[str, HelpEntry] = {}
        self._selected_category: Optional[HelpCategory] = None
        self._selected_index = 0

        self._load_default_help()

    def _load_default_help(self) -> None:
        """Load default help entries."""
        entries = [
            HelpEntry(
                title="Getting Started",
                content="Claude Code is an AI-powered coding assistant. Start by asking questions or giving tasks.",
                category=HelpCategory.GETTING_STARTED,
                tags=["intro", "start"],
            ),
            HelpEntry(
                title="Commands",
                content="Use slash commands like /init, /commit, /review to perform actions.",
                category=HelpCategory.COMMANDS,
                tags=["commands", "slash"],
            ),
            HelpEntry(
                title="Tools",
                content="Claude can use tools like Read, Write, Edit, Bash, Glob, Grep to help you.",
                category=HelpCategory.TOOLS,
                tags=["tools", "bash", "files"],
            ),
            HelpEntry(
                title="Keybindings",
                content="Ctrl+C: Cancel\nCtrl+O: Toggle verbose\nTab: Autocomplete",
                category=HelpCategory.KEYBINDINGS,
                tags=["keyboard", "shortcuts"],
            ),
            HelpEntry(
                title="Settings",
                content="Configure Claude in ~/.claude/settings.json or .claude/settings.json",
                category=HelpCategory.SETTINGS,
                tags=["config", "settings"],
            ),
            HelpEntry(
                title="Vim Mode",
                content="Enable vim mode for vim-like navigation and editing.",
                category=HelpCategory.TIPS,
                tags=["vim", "navigation"],
            ),
            HelpEntry(
                title="Extended Thinking",
                content="Claude uses extended thinking for complex reasoning. Toggle with Option+T.",
                category=HelpCategory.TIPS,
                tags=["thinking", "reasoning"],
            ),
            HelpEntry(
                title="How to commit?",
                content="Use /commit to create a git commit with Claude's help.",
                category=HelpCategory.FAQ,
                tags=["git", "commit"],
            ),
        ]

        for entry in entries:
            self._entries[entry.title] = entry

    def get_entries(
        self,
        category: Optional[HelpCategory] = None
    ) -> List[HelpEntry]:
        """Get help entries."""
        entries = list(self._entries.values())

        if category:
            entries = [e for e in entries if e.category == category]

        return entries

    def get_entry(self, title: str) -> Optional[HelpEntry]:
        """Get help entry."""
        return self._entries.get(title)

    def search(self, query: str) -> List[HelpEntry]:
        """Search help."""
        results = []

        for entry in self._entries.values():
            if query.lower() in entry.title.lower():
                results.append(entry)
            elif query.lower() in entry.content.lower():
                results.append(entry)
            elif any(query.lower() in tag.lower() for tag in entry.tags):
                results.append(entry)

        return results

    def set_category(self, category: Optional[HelpCategory]) -> None:
        """Set selected category."""
        self._selected_category = category
        self._selected_index = 0

    def get_selected(self) -> Optional[HelpEntry]:
        """Get selected entry."""
        entries = self.get_entries(self._selected_category)

        if entries and 0 <= self._selected_index < len(entries):
            return entries[self._selected_index]

        return None

    def select_next(self) -> None:
        """Select next entry."""
        entries = self.get_entries(self._selected_category)

        if self._selected_index < len(entries) - 1:
            self._selected_index += 1

    def select_prev(self) -> None:
        """Select previous entry."""
        if self._selected_index > 0:
            self._selected_index -= 1

    def get_categories(self) -> List[HelpCategory]:
        """Get available categories."""
        return list(HelpCategory)

    async def render(self) -> str:
        """Render help dialog."""
        lines = [
            "Help",
            "",
        ]

        # Categories
        if self.config.show_categories:
            lines.append("Categories:")
            for cat in HelpCategory:
                marker = "*" if cat == self._selected_category else " "
                lines.append(f"  {marker} {cat.value}")
            lines.append("")

        # Entries
        entries = self.get_entries(self._selected_category)

        for i, entry in enumerate(entries[:self.config.max_entries]):
            marker = ">" if i == self._selected_index else " "
            lines.append(f"{marker} {entry.title}")

        # Selected content
        selected = self.get_selected()

        if selected:
            lines.append("")
            lines.append(f"--- {selected.title} ---")
            lines.append(selected.content)

        return "\n".join(lines)

    def add_entry(self, entry: HelpEntry) -> None:
        """Add help entry."""
        self._entries[entry.title] = entry

    def remove_entry(self, title: str) -> bool:
        """Remove help entry."""
        if title in self._entries:
            del self._entries[title]
            return True
        return False


__all__ = [
    "HelpCategory",
    "HelpEntry",
    "HelpDialogConfig",
    "HelpDialog",
]