"""Tests for file watcher and project structure."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import time

from cc.context.watcher import (
    FileWatcher,
    FileEvent,
    FileEventType,
    ContextUpdater,
    ProjectStructure,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_file_event():
    """Test file event."""
    event = FileEvent(
        type=FileEventType.MODIFIED,
        path=Path("/tmp/test.py"),
    )

    assert event.type == FileEventType.MODIFIED
    assert event.timestamp > 0


def test_file_watcher_init():
    """Test watcher initialization."""
    watcher = FileWatcher(
        watch_paths=[Path("/tmp")],
        poll_interval=0.5,
    )

    assert len(watcher.watch_paths) == 1
    assert watcher.poll_interval == 0.5


def test_file_watcher_add_path():
    """Test adding watch path."""
    watcher = FileWatcher()

    watcher.add_path(Path("/tmp"))
    watcher.add_path(Path("/var"))

    assert len(watcher.watch_paths) == 2


def test_file_watcher_remove_path():
    """Test removing watch path."""
    watcher = FileWatcher()
    watcher.add_path(Path("/tmp"))

    watcher.remove_path(Path("/tmp"))

    assert len(watcher.watch_paths) == 0


def test_file_watcher_callback():
    """Test adding callback."""
    watcher = FileWatcher()

    def callback(event): pass

    watcher.add_callback(callback)

    assert callback in watcher._callbacks


def test_file_watcher_exclude():
    """Test exclude patterns."""
    watcher = FileWatcher(exclude_patterns=["__pycache__", "*.pyc"])

    assert watcher._should_exclude(Path("/tmp/__pycache__/test.pyc"))
    assert not watcher._should_exclude(Path("/tmp/test.py"))


@pytest.mark.asyncio
async def test_file_watcher_start_stop():
    """Test watcher start and stop."""
    watcher = FileWatcher(poll_interval=0.1)

    await watcher.start()
    assert watcher._running is True

    await asyncio.sleep(0.2)

    await watcher.stop()
    assert watcher._running is False


@pytest.mark.asyncio
async def test_file_watcher_detect_new_file(temp_dir):
    """Test detecting new file."""
    watcher = FileWatcher([temp_dir], poll_interval=0.1)

    results = []
    watcher.add_callback(lambda e: results.append(e))

    # Start watcher - this takes initial snapshot
    await watcher.start()

    # Create new file
    new_file = temp_dir / "new.txt"
    new_file.write_text("content")

    # Wait for watch loop to detect
    await asyncio.sleep(0.5)

    await watcher.stop()

    assert len(results) > 0
    assert results[0].type == FileEventType.CREATED


@pytest.mark.asyncio
async def test_file_watcher_detect_modification(temp_dir):
    """Test detecting modification."""
    # Create file first
    test_file = temp_dir / "test.txt"
    test_file.write_text("original")

    watcher = FileWatcher([temp_dir], poll_interval=0.1)

    results = []
    watcher.add_callback(lambda e: results.append(e))

    await watcher.start()

    # Modify file
    test_file.write_text("modified")

    # Wait for watch loop to detect
    await asyncio.sleep(0.5)

    await watcher.stop()

    assert len(results) > 0
    assert results[0].type == FileEventType.MODIFIED


def test_context_updater():
    """Test context updater."""
    watcher = FileWatcher()
    updater = ContextUpdater(None)
    updater.watcher = watcher

    assert updater.update_interval == 5.0


@pytest.mark.asyncio
async def test_context_updater_start_stop(temp_dir):
    """Test updater start/stop."""
    updater = ContextUpdater(None)
    updater.watcher = FileWatcher([temp_dir])

    await updater.start(temp_dir)
    assert updater.watcher._running is True

    await updater.stop()
    assert updater.watcher._running is False


def test_project_structure(temp_dir):
    """Test project structure."""
    # Create files
    (temp_dir / "main.py").write_text("print('hello')")
    (temp_dir / "test.txt").write_text("")

    structure = ProjectStructure(temp_dir)

    result = asyncio.run(structure.analyze())

    assert result["type"] == "unknown"  # No pyproject.toml
    assert result["files"][".py"] >= 1


@pytest.mark.asyncio
async def test_project_structure_detect_type(temp_dir):
    """Test project type detection."""
    # Create pyproject.toml
    (temp_dir / "pyproject.toml").write_text("""
[project]
name = "test"
""")

    structure = ProjectStructure(temp_dir)
    type = await structure._detect_project_type()

    assert type == "python"


@pytest.mark.asyncio
async def test_project_structure_count_files(temp_dir):
    """Test file counting."""
    (temp_dir / "a.py").write_text("")
    (temp_dir / "b.py").write_text("")
    (temp_dir / "c.js").write_text("")

    structure = ProjectStructure(temp_dir)
    counts = await structure._count_files()

    assert counts[".py"] >= 2
    assert counts[".js"] >= 1


@pytest.mark.asyncio
async def test_project_structure_find_entry_points(temp_dir):
    """Test finding entry points."""
    (temp_dir / "main.py").write_text("")
    (temp_dir / "app.py").write_text("")

    structure = ProjectStructure(temp_dir)
    entries = await structure._find_entry_points()

    assert "main.py" in entries


@pytest.mark.asyncio
async def test_project_structure_dependencies(temp_dir):
    """Test dependency extraction."""
    (temp_dir / "pyproject.toml").write_text("""
[project]
dependencies = ["requests", "click"]
""")

    structure = ProjectStructure(temp_dir)
    deps = await structure._get_dependencies()

    assert "requests" in deps


def test_file_watcher_get_file_info(temp_dir):
    """Test getting file info."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("content")

    watcher = FileWatcher()
    info = asyncio.run(watcher._get_file_info(test_file))

    assert info["exists"] is True
    assert info["size"] > 0