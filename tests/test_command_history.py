"""Tests for Command History."""

import pytest
from pathlib import Path
import tempfile

from cc.utils.command_history import (
    HistoryEntry,
    HistoryConfig,
    CommandHistory,
    AutoCompleter,
    get_history,
    init_history,
)


class TestHistoryEntry:
    """Test HistoryEntry."""

    def test_create(self):
        """Test creating entry."""
        entry = HistoryEntry(command="test command")
        assert entry.command == "test command"
        assert entry.timestamp > 0
        assert entry.success is True

    def test_with_metadata(self):
        """Test entry with metadata."""
        entry = HistoryEntry(
            command="test",
            metadata={"key": "value"},
        )
        assert entry.metadata["key"] == "value"


class TestCommandHistory:
    """Test CommandHistory."""

    def test_init(self):
        """Test initialization."""
        history = CommandHistory()
        assert len(history._entries) == 0

    def test_add(self):
        """Test adding entry."""
        history = CommandHistory()
        entry = history.add("test command")

        assert len(history._entries) == 1
        assert history._entries[0].command == "test command"

    def test_add_multiple(self):
        """Test adding multiple entries."""
        history = CommandHistory()
        history.add("cmd1")
        history.add("cmd2")
        history.add("cmd3")

        assert len(history._entries) == 3

    def test_deduplicate(self):
        """Test deduplication."""
        config = HistoryConfig(deduplicate=True)
        history = CommandHistory(config)

        history.add("repeat")
        history.add("repeat")
        history.add("repeat")

        # Should only have 1 entry due to dedup
        assert len(history._entries) == 1

    def test_get_recent(self):
        """Test getting recent entries."""
        history = CommandHistory()
        for i in range(10):
            history.add(f"cmd{i}")

        recent = history.get_recent(5)
        assert len(recent) == 5
        assert recent[-1].command == "cmd9"

    def test_search(self):
        """Test searching history."""
        history = CommandHistory()
        history.add("ls -la")
        history.add("cat file.txt")
        history.add("ls -lh")
        history.add("grep pattern")

        results = history.search("ls")
        assert len(results) == 2

    def test_get_stats(self):
        """Test getting statistics."""
        history = CommandHistory()
        history.add("cmd1", success=True, duration_ms=100)
        history.add("cmd2", success=False, duration_ms=200)
        history.add("cmd3", success=True, duration_ms=150)

        stats = history.get_stats()
        assert stats["total_entries"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1

    def test_clear(self):
        """Test clearing history."""
        history = CommandHistory()
        history.add("cmd1")
        history.add("cmd2")

        history.clear()
        assert len(history._entries) == 0

    def test_max_entries(self):
        """Test max entries limit."""
        config = HistoryConfig(max_entries=5)
        history = CommandHistory(config)

        for i in range(10):
            history.add(f"cmd{i}")

        assert len(history._entries) <= 5

    def test_persistence(self):
        """Test persistence to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HistoryConfig(
                persist=True,
                history_file="test_history.json",
            )
            history = CommandHistory(config)
            history.initialize(Path(tmpdir))

            history.add("cmd1")
            history.add("cmd2")

            # Create new history instance to load
            history2 = CommandHistory(config)
            history2.initialize(Path(tmpdir))

            assert len(history2._entries) == 2

    def test_export_import(self):
        """Test export and import."""
        history = CommandHistory()
        history.add("cmd1")
        history.add("cmd2")

        exported = history.export()

        history2 = CommandHistory()
        imported = history2.import_(exported)

        assert imported == 2
        assert len(history2._entries) == 2


class TestAutoCompleter:
    """Test AutoCompleter."""

    def test_init(self):
        """Test initialization."""
        completer = AutoCompleter()
        assert len(completer._commands) == 0

    def test_register_command(self):
        """Test registering command."""
        completer = AutoCompleter()
        completer.register_command("test", lambda: None)

        assert "test" in completer._commands

    def test_register_with_aliases(self):
        """Test registering with aliases."""
        completer = AutoCompleter()
        completer.register_command("commit", lambda: None, aliases=["c", "co"])

        assert "commit" in completer._commands
        assert completer._aliases["c"] == "commit"

    def test_get_completions(self):
        """Test getting completions."""
        completer = AutoCompleter()
        completer.register_command("commit", lambda: None)
        completer.register_command("checkout", lambda: None)

        completions = completer.get_completions("c")
        assert len(completions) >= 2

    def test_completions_with_history(self):
        """Test completions with history."""
        history = CommandHistory()
        history.add("custom command")

        completer = AutoCompleter(history=history)
        completer.register_command("commit", lambda: None)

        completions = completer.get_completions("c")
        assert "custom command" in completions


class TestGlobals:
    """Test global functions."""

    def test_get_history(self):
        """Test getting global history."""
        history = get_history()
        assert history is not None

    def test_init_history(self):
        """Test initializing global history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = init_history(Path(tmpdir))
            assert history is not None
            assert history._history_path is not None