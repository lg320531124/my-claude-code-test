"""Tests for workspace manager."""

import pytest
from pathlib import Path
from src.cc.services.workspace_manager import (
    WorkspaceManager,
    WorkspaceConfig,
    WorkspaceType,
    WorkspaceInfo,
)


@pytest.mark.asyncio
async def test_workspace_manager_init():
    """Test manager initialization."""
    manager = WorkspaceManager()
    assert manager.config is not None


@pytest.mark.asyncio
async def test_create_workspace():
    """Test creating workspace."""
    manager = WorkspaceManager()

    workspace = await manager.create(
        "test_workspace",
        WorkspaceType.PROJECT
    )

    assert workspace.name == "test_workspace"
    assert workspace.type == WorkspaceType.PROJECT


@pytest.mark.asyncio
async def test_get_workspace():
    """Test getting workspace."""
    manager = WorkspaceManager()

    created = await manager.create("test")
    workspace = await manager.get(created.id)

    assert workspace is not None
    assert workspace.name == "test"


@pytest.mark.asyncio
async def test_get_by_name():
    """Test getting by name."""
    manager = WorkspaceManager()

    await manager.create("my_workspace")
    workspace = await manager.get_by_name("my_workspace")

    assert workspace is not None


@pytest.mark.asyncio
async def test_set_current():
    """Test setting current."""
    manager = WorkspaceManager()

    workspace = await manager.create("current_test")
    result = await manager.set_current(workspace.id)

    assert result is True


@pytest.mark.asyncio
async def test_get_current():
    """Test getting current."""
    manager = WorkspaceManager()

    workspace = await manager.create("current_test")
    await manager.set_current(workspace.id)

    current = await manager.get_current()
    assert current is not None


@pytest.mark.asyncio
async def test_list_workspaces():
    """Test listing workspaces."""
    manager = WorkspaceManager()

    await manager.create("ws1")
    await manager.create("ws2")

    workspaces = await manager.list_workspaces()
    assert len(workspaces) == 2


@pytest.mark.asyncio
async def test_list_by_type():
    """Test listing by type."""
    manager = WorkspaceManager()

    await manager.create("project", WorkspaceType.PROJECT)
    await manager.create("temp", WorkspaceType.TEMP)

    projects = await manager.list_workspaces(WorkspaceType.PROJECT)
    assert len(projects) == 1


@pytest.mark.asyncio
async def test_delete_workspace():
    """Test deleting workspace."""
    manager = WorkspaceManager()

    workspace = await manager.create("delete_test")
    result = await manager.delete(workspace.id)

    assert result is True


@pytest.mark.asyncio
async def test_exists():
    """Test exists check."""
    manager = WorkspaceManager()

    workspace = await manager.create("exist_test")
    result = await manager.exists(workspace.path)

    assert result is True


@pytest.mark.asyncio
async def test_get_stats():
    """Test getting stats."""
    manager = WorkspaceManager()

    await manager.create("test1")
    await manager.create("test2")

    stats = await manager.get_stats()
    assert stats["total_workspaces"] == 2


@pytest.mark.asyncio
async def test_workspace_type_enum():
    """Test workspace type enum."""
    assert WorkspaceType.PROJECT.value == "project"
    assert WorkspaceType.TEMP.value == "temp"


@pytest.mark.asyncio
async def test_workspace_config():
    """Test workspace config."""
    config = WorkspaceConfig(
        max_workspaces=5,
        auto_cleanup=True,
    )

    assert config.max_workspaces == 5


@pytest.mark.asyncio
async def test_save_read_file():
    """Test saving and reading file."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        config = WorkspaceConfig(root_path=Path(tmpdir))
        manager = WorkspaceManager(config)

        workspace = await manager.create("file_test")

        result = await manager.save_file(
            workspace.id,
            "test.txt",
            "test content"
        )

        assert result is True

        content = await manager.read_file(workspace.id, "test.txt")
        assert content == "test content"