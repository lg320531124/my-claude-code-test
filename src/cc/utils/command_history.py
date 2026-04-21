"""Command History - Track and manage command history."""

from __future__ import annotations
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import deque
import json

from .log import get_logger

logger = get_logger(__name__)


@dataclass
class HistoryEntry:
    """A single history entry."""
    command: str
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    success: bool = True
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoryConfig:
    """History configuration."""
    max_entries: int = 1000
    persist: bool = True
    history_file: str = ".claude_history.json"
    deduplicate: bool = True
    deduplicate_window: int = 10  # Check last N entries for duplicates


class CommandHistory:
    """Manage command history with persistence."""

    def __init__(self, config: Optional[HistoryConfig] = None):
        self.config = config or HistoryConfig()
        self._entries: deque[HistoryEntry] = deque(maxlen=self.config.max_entries)
        self._history_path: Optional[Path] = None
        self._loaded = False

    def initialize(self, cwd: Optional[Path] = None) -> None:
        """Initialize history, optionally loading from file."""
        if cwd:
            self._history_path = cwd / self.config.history_file

        if self.config.persist and self._history_path:
            self._load_from_file()

    def add(
        self,
        command: str,
        success: bool = True,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HistoryEntry:
        """Add a command to history."""
        # Check for duplicate in recent entries
        if self.config.deduplicate:
            recent = list(self._entries)[-self.config.deduplicate_window:]
            for entry in recent:
                if entry.command == command:
                    # Update timestamp, don't add duplicate
                    entry.timestamp = time.time()
                    return entry

        entry = HistoryEntry(
            command=command,
            timestamp=time.time(),
            success=success,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        self._entries.append(entry)

        # Persist if enabled
        if self.config.persist:
            self._save_to_file()

        return entry

    def get_recent(self, limit: int = 50) -> List[HistoryEntry]:
        """Get recent history entries."""
        return list(self._entries)[-limit:]

    def search(self, query: str, limit: int = 20) -> List[HistoryEntry]:
        """Search history for matching commands."""
        results = []
        query_lower = query.lower()

        for entry in reversed(self._entries):
            if query_lower in entry.command.lower():
                results.append(entry)
                if len(results) >= limit:
                    break

        return results

    def get_last_successful(self) -> Optional[HistoryEntry]:
        """Get last successful command."""
        for entry in reversed(self._entries):
            if entry.success:
                return entry
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics."""
        if not self._entries:
            return {
                "total_entries": 0,
                "successful": 0,
                "failed": 0,
                "avg_duration_ms": 0.0,
                "unique_commands": 0,
            }

        successful = sum(1 for e in self._entries if e.success)
        durations = [e.duration_ms for e in self._entries if e.duration_ms > 0]
        unique = len(set(e.command for e in self._entries))

        return {
            "total_entries": len(self._entries),
            "successful": successful,
            "failed": len(self._entries) - successful,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "unique_commands": unique,
        }

    def clear(self) -> None:
        """Clear history."""
        self._entries.clear()

        if self.config.persist and self._history_path:
            self._save_to_file()

    def _load_from_file(self) -> None:
        """Load history from file."""
        if not self._history_path or not self._history_path.exists():
            return

        try:
            with open(self._history_path, 'r') as f:
                data = json.load(f)

            for entry_data in data.get("entries", []):
                entry = HistoryEntry(
                    command=entry_data.get("command", ""),
                    timestamp=entry_data.get("timestamp", 0.0),
                    success=entry_data.get("success", True),
                    duration_ms=entry_data.get("duration_ms", 0.0),
                    metadata=entry_data.get("metadata", {}),
                )
                # Don't exceed max_entries
                if len(self._entries) < self.config.max_entries:
                    self._entries.append(entry)

            self._loaded = True
            logger.debug(f"Loaded {len(self._entries)} history entries")

        except Exception as e:
            logger.warning(f"Failed to load history: {e}")

    def _save_to_file(self) -> None:
        """Save history to file."""
        if not self._history_path:
            return

        try:
            # Create parent directory if needed
            self._history_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "entries": [
                    {
                        "command": e.command,
                        "timestamp": e.timestamp,
                        "success": e.success,
                        "duration_ms": e.duration_ms,
                        "metadata": e.metadata,
                    }
                    for e in self._entries
                ],
                "version": 1,
            }

            with open(self._history_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save history: {e}")

    def export(self) -> str:
        """Export history as JSON string."""
        data = {
            "entries": [
                {
                    "command": e.command,
                    "timestamp": e.timestamp,
                    "success": e.success,
                    "duration_ms": e.duration_ms,
                    "metadata": e.metadata,
                }
                for e in self._entries
            ],
        }
        return json.dumps(data, indent=2)

    def import_(self, json_data: str) -> int:
        """Import history from JSON string."""
        try:
            data = json.loads(json_data)
            imported = 0

            for entry_data in data.get("entries", []):
                entry = HistoryEntry(
                    command=entry_data.get("command", ""),
                    timestamp=entry_data.get("timestamp", 0.0),
                    success=entry_data.get("success", True),
                    duration_ms=entry_data.get("duration_ms", 0.0),
                    metadata=entry_data.get("metadata", {}),
                )
                if len(self._entries) < self.config.max_entries:
                    self._entries.append(entry)
                    imported += 1

            return imported

        except Exception as e:
            logger.warning(f"Failed to import history: {e}")
            return 0


# Auto-completion support
class AutoCompleter:
    """Auto-completion for commands."""

    def __init__(self, history: Optional[CommandHistory] = None):
        self.history = history
        self._commands: Dict[str, Callable] = {}
        self._aliases: Dict[str, str] = {}

    def register_command(self, name: str, handler: Callable, aliases: Optional[List[str]] = None) -> None:
        """Register a command for completion."""
        self._commands[name] = handler

        if aliases:
            for alias in aliases:
                self._aliases[alias] = name

    def get_completions(self, partial: str) -> List[str]:
        """Get completions for a partial command."""
        completions = []

        # Check registered commands
        for cmd in self._commands:
            if cmd.startswith(partial):
                completions.append(cmd)

        # Check aliases
        for alias in self._aliases:
            if alias.startswith(partial):
                completions.append(alias)

        # Check history
        if self.history:
            for entry in self.history.get_recent(20):
                if entry.command.startswith(partial) and entry.command not in completions:
                    completions.append(entry.command)

        # Sort by frequency (history entries come first)
        return completions[:20]


# Global instance
_history: Optional[CommandHistory] = None


def get_history() -> CommandHistory:
    """Get global history instance."""
    global _history
    if _history is None:
        _history = CommandHistory()
    return _history


def init_history(cwd: Optional[Path] = None) -> CommandHistory:
    """Initialize global history."""
    global _history
    _history = CommandHistory()
    _history.initialize(cwd)
    return _history


__all__ = [
    "HistoryEntry",
    "HistoryConfig",
    "CommandHistory",
    "AutoCompleter",
    "get_history",
    "init_history",
]