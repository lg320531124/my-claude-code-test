"""Tests for full context collection."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import json

from cc.context.full_context import (
    AsyncContextCollector,
    EnvironmentInfo,
    GitInfo,
    ProjectInfo,
    ContextInfo,
    build_system_prompt_from_context,
    get_full_context,
    get_context_sync,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_environment_info():
    """Test environment info."""
    info = EnvironmentInfo(
        python_version="3.12.0",
        platform="Linux",
        os_name="Linux",
        architecture="x86_64",
        cwd="/tmp",
        home="/home/user",
    )

    assert info.python_version == "3.12.0"
    assert info.os_name == "Linux"


def test_git_info():
    """Test git info."""
    info = GitInfo(
        in_repo=True,
        branch="main",
        remote="https://github.com/user/repo",
        recent_commits=["abc123 First commit"],
    )

    assert info.in_repo is True
    assert info.branch == "main"


def test_project_info():
    """Test project info."""
    info = ProjectInfo(
        type="python",
        name="my-project",
        dependencies=["requests", "click"],
        source_dirs=["src"],
    )

    assert info.type == "python"
    assert "requests" in info.dependencies


def test_context_info():
    """Test context info."""
    context = ContextInfo(
        environment=EnvironmentInfo(
            python_version="3.12",
            platform="Linux",
            os_name="Linux",
            architecture="x86_64",
            cwd="/tmp",
            home="/home",
        ),
        git=GitInfo(in_repo=False),
        project=ProjectInfo(type="unknown"),
    )

    assert context.environment.python_version == "3.12"
    assert context.timestamp > 0


@pytest.mark.asyncio
async def test_async_context_collector(temp_dir):
    """Test async context collection."""
    collector = AsyncContextCollector(temp_dir)
    context = await collector.collect_all()

    assert context.environment.cwd == str(temp_dir)
    assert context.project.type == "unknown"


@pytest.mark.asyncio
async def test_collect_environment(temp_dir):
    """Test environment collection."""
    collector = AsyncContextCollector(temp_dir)
    env = await collector._collect_environment()

    assert env.cwd == str(temp_dir)
    assert env.python_version  # Should have value


@pytest.mark.asyncio
async def test_collect_git_not_repo(temp_dir):
    """Test git collection when not in repo."""
    collector = AsyncContextCollector(temp_dir)
    git = await collector._collect_git()

    assert git.in_repo is False


@pytest.mark.asyncio
async def test_detect_project_type(temp_dir):
    """Test project type detection."""
    collector = AsyncContextCollector(temp_dir)

    # No config files
    type = await collector._detect_project_type()
    assert type == "unknown"

    # Create pyproject.toml
    (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'")
    type = await collector._detect_project_type()
    assert type == "python"


@pytest.mark.asyncio
async def test_detect_javascript_project(temp_dir):
    """Test JavaScript project detection."""
    (temp_dir / "package.json").write_text("{\"name\": \"test\"}")

    collector = AsyncContextCollector(temp_dir)
    type = await collector._detect_project_type()

    assert type == "javascript"


@pytest.mark.asyncio
async def test_find_entry_points(temp_dir):
    """Test finding entry points."""
    (temp_dir / "main.py").write_text("")
    (temp_dir / "app.py").write_text("")

    collector = AsyncContextCollector(temp_dir)
    entries = await collector._find_entry_points()

    assert "main.py" in entries
    assert "app.py" in entries


@pytest.mark.asyncio
async def test_find_test_files(temp_dir):
    """Test finding test files."""
    (temp_dir / "test_main.py").write_text("")
    (temp_dir / "utils_test.py").write_text("")

    collector = AsyncContextCollector(temp_dir)
    tests = await collector._find_test_files()

    assert len(tests) >= 2


@pytest.mark.asyncio
async def test_find_source_dirs(temp_dir):
    """Test finding source directories."""
    (temp_dir / "src").mkdir()

    collector = AsyncContextCollector(temp_dir)
    dirs = await collector._find_source_dirs()

    assert "src" in dirs


@pytest.mark.asyncio
async def test_collect_python_project(temp_dir):
    """Test Python project collection."""
    pyproject = temp_dir / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-project"
version = "1.0.0"
dependencies = ["requests", "click"]
""")

    collector = AsyncContextCollector(temp_dir)
    info = await collector._collect_python_project()

    assert info.get("name") == "test-project"
    assert info.get("version") == "1.0.0"


@pytest.mark.asyncio
async def test_collect_javascript_project(temp_dir):
    """Test JavaScript project collection."""
    package_json = temp_dir / "package.json"
    package_json.write_text(json.dumps({
        "name": "js-project",
        "version": "2.0.0",
        "dependencies": {"express": "4.0"},
        "devDependencies": {"jest": "29.0"},
    }))

    collector = AsyncContextCollector(temp_dir)
    info = await collector._collect_javascript_project()

    assert info.get("name") == "js-project"
    assert "express" in info.get("dependencies", [])


def test_build_system_prompt():
    """Test building system prompt."""
    context = ContextInfo(
        environment=EnvironmentInfo(
            python_version="3.12",
            platform="Linux",
            os_name="Linux",
            architecture="x86_64",
            cwd="/project",
            home="/home",
        ),
        git=GitInfo(
            in_repo=True,
            branch="main",
            status="",
            recent_commits=["abc123 First"],
        ),
        project=ProjectInfo(
            type="python",
            name="my-project",
        ),
    )

    prompt = build_system_prompt_from_context(context)

    assert "Python: 3.12" in prompt
    assert "Branch: main" in prompt
    assert "python" in prompt.lower()


def test_build_system_prompt_review():
    """Test building review prompt."""
    context = ContextInfo(
        environment=EnvironmentInfo(
            python_version="3.12",
            platform="Linux",
            os_name="Linux",
            architecture="x86_64",
            cwd="/tmp",
            home="/home",
        ),
        git=GitInfo(),
        project=ProjectInfo(),
    )

    prompt = build_system_prompt_from_context(context, scenario="review")

    assert "Review Guidelines" in prompt


def test_get_context_sync(temp_dir):
    """Test sync context wrapper."""
    context = get_context_sync(temp_dir)

    assert context.environment.cwd == str(temp_dir)


@pytest.mark.asyncio
async def test_get_full_context(temp_dir):
    """Test async full context."""
    context = await get_full_context(temp_dir)

    assert isinstance(context, ContextInfo)
    assert context.environment.cwd == str(temp_dir)


@pytest.mark.asyncio
async def test_context_with_git_repo(temp_dir):
    """Test context in git repo."""
    # Initialize git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_dir, capture_output=True)

    collector = AsyncContextCollector(temp_dir)
    git = await collector._collect_git()

    assert git.in_repo is True