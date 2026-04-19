"""Tests for Skill system."""

import pytest
import asyncio
from pathlib import Path
import tempfile

from cc.tools.skill_system import (
    SkillLoader,
    SkillExecutor,
    SkillManager,
    SkillMetadata,
    SkillDefinition,
    SkillValidationError,
    SkillSchema,
    get_skill_manager,
)


@pytest.fixture
def temp_skill_dir():
    """Create temporary skill directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_skill_metadata():
    """Test skill metadata."""
    metadata = SkillMetadata(
        name="test_skill",
        description="A test skill",
        version="1.0",
        tags=["python", "test"],
    )

    assert metadata.name == "test_skill"
    assert "python" in metadata.tags


def test_skill_definition():
    """Test skill definition."""
    skill = SkillDefinition(
        metadata=SkillMetadata(name="test", description="Test"),
        prompt="Test prompt",
        examples=["Example 1"],
    )

    assert skill.prompt == "Test prompt"
    assert len(skill.examples) == 1


def test_skill_schema():
    """Test skill schema validation."""
    schema = SkillSchema(
        name="valid_skill",
        description="Valid description",
        prompt="Valid prompt",
    )

    assert schema.name == "valid_skill"


def test_skill_schema_validation():
    """Test schema validation fails."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SkillSchema(name="", description="", prompt="")


def test_skill_loader_init():
    """Test loader initialization."""
    loader = SkillLoader()

    assert len(loader.skill_dirs) > 0


def test_skill_loader_custom_dirs(temp_skill_dir):
    """Test loader with custom directories."""
    loader = SkillLoader([temp_skill_dir])

    assert loader.skill_dirs == [temp_skill_dir]


@pytest.mark.asyncio
async def test_skill_loader_load_empty(temp_skill_dir):
    """Test loading from empty directory."""
    loader = SkillLoader([temp_skill_dir])
    skills = await loader.load_all()

    assert len(skills) == 0


@pytest.mark.asyncio
async def test_skill_loader_load_simple(temp_skill_dir):
    """Test loading simple skill file."""
    skill_file = temp_skill_dir / "simple_skill.md"
    skill_file.write_text("""
---
name: simple
description: A simple skill
---

This is the skill prompt.
""")

    loader = SkillLoader([temp_skill_dir])
    skills = await loader.load_all()

    assert "simple" in skills


@pytest.mark.asyncio
async def test_skill_loader_load_no_frontmatter(temp_skill_dir):
    """Test loading file without frontmatter."""
    skill_file = temp_skill_dir / "no_frontmatter.md"
    skill_file.write_text("Just a prompt without frontmatter")

    loader = SkillLoader([temp_skill_dir])
    skills = await loader.load_all()

    assert "no_frontmatter" in skills


def test_skill_loader_parse_frontmatter():
    """Test frontmatter parsing."""
    loader = SkillLoader()

    frontmatter = """
name: test
description: Test skill
version: "2.0"
tags: [python, async]
"""

    result = loader._parse_frontmatter(frontmatter)

    assert result["name"] == "test"
    assert result["version"] == "2.0"
    assert "python" in result["tags"]


@pytest.mark.asyncio
async def test_skill_loader_get_skill(temp_skill_dir):
    """Test getting loaded skill."""
    skill_file = temp_skill_dir / "get_test.md"
    skill_file.write_text("---\nname: get_test\ndescription: Test\n---\nPrompt")

    loader = SkillLoader([temp_skill_dir])
    await loader.load_all()

    skill = loader.get_skill("get_test")

    assert skill is not None
    assert skill.metadata.name == "get_test"


@pytest.mark.asyncio
async def test_skill_loader_search(temp_skill_dir):
    """Test skill search."""
    skill_file = temp_skill_dir / "searchable.md"
    skill_file.write_text("---\nname: searchable\ndescription: Python async skill\n---\nPrompt")

    loader = SkillLoader([temp_skill_dir])
    await loader.load_all()

    results = loader.search_skills("python")

    assert len(results) > 0


@pytest.mark.asyncio
async def test_skill_executor_execute(temp_skill_dir):
    """Test skill execution."""
    skill_file = temp_skill_dir / "exec_test.md"
    skill_file.write_text("---\nname: exec_test\ndescription: Test\n---\nTest prompt")

    loader = SkillLoader([temp_skill_dir])
    await loader.load_all()

    executor = SkillExecutor(loader)
    result = await executor.execute("exec_test", {"cwd": "/tmp"}, args="extra args")

    assert "Test prompt" in result
    assert "extra args" in result


def test_skill_executor_history():
    """Test execution history."""
    loader = SkillLoader()
    executor = SkillExecutor(loader)

    asyncio.run(executor.execute("test", {}, "args"))

    history = executor.get_history()

    assert len(history) > 0


@pytest.mark.asyncio
async def test_skill_manager_initialize():
    """Test manager initialization."""
    manager = SkillManager()

    await manager.initialize()

    assert manager._loaded is True


@pytest.mark.asyncio
async def test_skill_manager_list():
    """Test listing skills."""
    manager = SkillManager()
    await manager.initialize()

    skills = manager.list_skills()

    assert isinstance(skills, list)


def test_skill_manager_template():
    """Test skill template generation."""
    manager = SkillManager()

    template = manager.create_skill_template("new_skill")

    assert "---" in template
    assert "name: new_skill" in template


@pytest.mark.asyncio
async def test_skill_manager_reload(temp_skill_dir):
    """Test skill reload."""
    manager = SkillManager()
    manager.loader = SkillLoader([temp_skill_dir])

    skill_file = temp_skill_dir / "reload_test.md"
    skill_file.write_text("---\nname: reload_test\n---\nPrompt")

    await manager.reload()

    skills = manager.list_skills()
    assert len(skills) > 0


def test_get_skill_manager():
    """Test global manager."""
    manager1 = get_skill_manager()
    manager2 = get_skill_manager()

    assert manager1 is manager2


def test_skill_tool():
    """Test skill tool."""
    from cc.tools.skill_system import SkillTool

    tool = SkillTool()
    schema = tool.get_schema()

    assert schema["name"] == "Skill"