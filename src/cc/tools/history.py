"""History Tool - Command history management."""

from __future__ import annotations
from typing import ClassVar, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class HistoryEntry(BaseModel):
    """History entry."""
    timestamp: str
    command: str
    result_summary: Optional[str] = None


class HistoryInput(ToolInput):
    """Input for HistoryTool."""
    action: str = Field(description="Action: list, search, clear, export")
    limit: int = Field(default=50, description="Maximum entries to return")
    search: Optional[str] = Field(default=None, description="Search pattern")
    format: str = Field(default="text", description="Output format: text, json")


class HistoryTool(ToolDef):
    """Manage command history."""

    name: ClassVar[str] = "History"
    description: ClassVar[str] = "View and manage command history"
    input_schema: ClassVar[type] = HistoryInput

    # Simulated history storage
    _history: List[HistoryEntry] = []

    async def execute(self, input: HistoryInput, ctx: ToolUseContext) -> ToolResult:
        """Execute history operation."""
        action = input.action

        if action == "list":
            return self._list_history(input.limit, input.format)
        elif action == "search":
            return self._search_history(input.search, input.limit)
        elif action == "clear":
            return self._clear_history()
        elif action == "export":
            return self._export_history(input.format)
        else:
            return ToolResult(
                content=f"Unknown action: {action}",
                is_error=True,
            )

    def _list_history(self, limit: int, format: str) -> ToolResult:
        """List history entries."""
        entries = self._history[:limit]

        if format == "json":
            content = "\n".join([e.model_dump_json() for e in entries])
        else:
            lines = []
            for i, e in enumerate(entries, 1):
                lines.append(f"{i:4} [{e.timestamp}] {e.command}")
            content = "\n".join(lines) if lines else "No history entries."

        return ToolResult(
            content=content,
            metadata={"count": len(entries), "total": len(self._history)},
        )

    def _search_history(self, pattern: Optional[str], limit: int) -> ToolResult:
        """Search history."""
        if not pattern:
            return ToolResult(
                content="Search pattern required",
                is_error=True,
            )

        matches = [
            e for e in self._history
            if pattern.lower() in e.command.lower()
        ][:limit]

        lines = []
        for i, e in enumerate(matches, 1):
            lines.append(f"{i:4} [{e.timestamp}] {e.command}")

        return ToolResult(
            content="\n".join(lines) if lines else f"No matches for: {pattern}",
            metadata={"pattern": pattern, "matches": len(matches)},
        )

    def _clear_history(self) -> ToolResult:
        """Clear history."""
        count = len(self._history)
        self._history.clear()

        return ToolResult(
            content=f"History cleared ({count} entries removed)",
            metadata={"cleared": count},
        )

    def _export_history(self, format: str) -> ToolResult:
        """Export history."""
        if format == "json":
            import json
            data = [e.model_dump() for e in self._history]
            content = json.dumps(data, indent=2)
        else:
            lines = []
            for e in self._history:
                lines.append(f"{e.timestamp}\t{e.command}")
            content = "\n".join(lines)

        return ToolResult(
            content=content,
            metadata={"format": format, "entries": len(self._history)},
        )

    @classmethod
    def add_entry(cls, command: str, result_summary: Optional[str] = None) -> None:
        """Add entry to history."""
        entry = HistoryEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            command=command,
            result_summary=result_summary,
        )
        cls._history.append(entry)


__all__ = ["HistoryTool", "HistoryInput", "HistoryEntry"]