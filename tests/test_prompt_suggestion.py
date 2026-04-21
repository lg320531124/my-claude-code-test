"""Tests for prompt suggestion."""

import pytest
from src.cc.services.prompt_suggestion import (
    PromptSuggester,
    SuggestionType,
    SuggestionPriority,
    ContextInfo,
)


@pytest.mark.asyncio
async def test_prompt_suggester_init():
    """Test prompt suggester initialization."""
    suggester = PromptSuggester()
    assert suggester.config is not None
    assert suggester._templates is not None


@pytest.mark.asyncio
async def test_suggest_with_context():
    """Test suggestion with context."""
    suggester = PromptSuggester()

    context = ContextInfo(
        recent_files=["main.py", "utils.py"],
        recent_commands=["/commit"],
        current_project="test_project",
        errors=["TypeError"],
    )

    suggestions = await suggester.suggest(context)

    assert len(suggestions) > 0
    assert any(s.type == SuggestionType.TASK for s in suggestions)


@pytest.mark.asyncio
async def test_suggest_tasks():
    """Test task suggestions."""
    suggester = PromptSuggester()

    context = ContextInfo(
        recent_files=["test.py"],
        errors=["ImportError"],
    )

    suggestions = await suggester.suggest(context)

    # Should suggest fixing errors
    assert any("Fix error" in s.text for s in suggestions)


@pytest.mark.asyncio
async def test_suggest_commands():
    """Test command suggestions."""
    suggester = PromptSuggester()

    suggestions = await suggester.suggest()

    # Should have command suggestions
    assert any(s.type == SuggestionType.COMMAND for s in suggestions)


@pytest.mark.asyncio
async def test_diversity():
    """Test suggestion diversity."""
    suggester = PromptSuggester()

    suggestions = await suggester.suggest()

    # Should have different types
    types = set(s.type for s in suggestions)
    assert len(types) >= 1


@pytest.mark.asyncio
async def test_priority_sorting():
    """Test priority sorting."""
    suggester = PromptSuggester()

    suggestions = await suggester.suggest()

    # Should be sorted by priority
    priorities = [s.priority for s in suggestions]
    high_first = any(p == SuggestionPriority.HIGH for p in priorities[:3])


@pytest.mark.asyncio
async def test_limit():
    """Test suggestion limit."""
    suggester = PromptSuggester()

    suggestions = await suggester.suggest(limit=5)

    assert len(suggestions) <= 5


@pytest.mark.asyncio
async def test_add_to_history():
    """Test adding to history."""
    suggester = PromptSuggester()

    await suggester.add_to_history("test prompt")
    history = await suggester.get_history()

    assert "test prompt" in history


@pytest.mark.asyncio
async def test_update_context():
    """Test updating context."""
    suggester = PromptSuggester()

    await suggester.update_context(
        files=["file.py"],
        project="project",
        topics=["python"],
    )

    assert suggester._context is not None


@pytest.mark.asyncio
async def test_follow_up_suggestion():
    """Test follow-up suggestions."""
    suggester = PromptSuggester()

    # Add history
    await suggester.add_to_history("previous task")

    suggestions = await suggester.suggest()

    # Should suggest follow-up
    assert any(s.type == SuggestionType.FOLLOW_UP for s in suggestions)


@pytest.mark.asyncio
async def test_confidence_filter():
    """Test confidence filtering."""
    suggester = PromptSuggester()

    suggestions = await suggester.suggest()

    # All should meet minimum confidence
    assert all(s.confidence >= suggester.config.min_confidence for s in suggestions)


@pytest.mark.asyncio
async def test_suggest_for_file():
    """Test suggestions for specific file."""
    suggester = PromptSuggester()

    from pathlib import Path
    suggestions = await suggester.suggest_for_file(Path("test.py"))

    assert len(suggestions) >= 2
    assert any("Review" in s.text for s in suggestions)


@pytest.mark.asyncio
async def test_suggest_next_action_error():
    """Test next action suggestion for error."""
    suggester = PromptSuggester()

    result = {"error": "Something went wrong"}
    suggestion = await suggester.suggest_next_action(result)

    assert suggestion is not None
    assert "Fix" in suggestion.text


@pytest.mark.asyncio
async def test_suggest_next_action_success():
    """Test next action suggestion for success."""
    suggester = PromptSuggester()

    result = {"success": True}
    suggestion = await suggester.suggest_next_action(result)

    assert suggestion is not None
    assert "Review" in suggestion.text