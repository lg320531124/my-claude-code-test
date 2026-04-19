"""Tests for Services."""

from __future__ import annotations
import pytest

from cc.services.cache.cache import CacheService, CacheConfig, get_cache_service
from cc.services.prompt.prompt import PromptService, PromptConfig, get_prompt
from cc.services.storage.storage import StorageService, StorageConfig, get_storage_service


@pytest.fixture
def cache_service():
    """Create CacheService instance."""
    config = CacheConfig(max_entries=100)
    return CacheService(config)


def test_cache_set_get(cache_service):
    """Test Cache set and get."""
    cache_service.set("test_key", "test_value")
    result = cache_service.get("test_key")
    assert result == "test_value"


def test_cache_missing_key(cache_service):
    """Test Cache missing key."""
    result = cache_service.get("nonexistent")
    assert result is None


def test_cache_delete(cache_service):
    """Test Cache delete."""
    cache_service.set("test_key", "test_value")
    deleted = cache_service.delete("test_key")
    assert deleted == True
    assert cache_service.get("test_key") is None


def test_cache_clear(cache_service):
    """Test Cache clear."""
    cache_service.set("key1", "value1")
    cache_service.set("key2", "value2")
    count = cache_service.clear()
    assert count == 2
    assert cache_service.get("key1") is None


def test_cache_stats(cache_service):
    """Test Cache stats."""
    cache_service.set("key1", "value1")
    stats = cache_service.stats()
    assert stats["entries"] >= 1


def test_cache_ttl(cache_service):
    """Test Cache TTL."""
    import time
    cache_service.set("test_key", "test_value", ttl=1)
    result = cache_service.get("test_key")
    assert result == "test_value"

    time.sleep(2)
    result = cache_service.get("test_key")
    assert result is None


@pytest.fixture
def prompt_service():
    """Create PromptService instance."""
    return PromptService()


def test_prompt_get_default(prompt_service):
    """Test getting default prompt."""
    prompt = prompt_service.get_prompt("default")
    assert prompt  # Should have content


def test_prompt_get_code_review(prompt_service):
    """Test getting code review prompt."""
    prompt = prompt_service.get_prompt("code_review")
    assert "review" in prompt.lower()


def test_prompt_with_variables(prompt_service):
    """Test prompt with variables."""
    prompt = prompt_service.get_prompt(
        "explain",
        variables={"topic": "Python", "level": "beginner"},
    )
    assert "Python" in prompt or "beginner" in prompt


def test_prompt_list_templates(prompt_service):
    """Test listing templates."""
    templates = prompt_service.list_templates()
    assert len(templates) > 0


def test_get_prompt_function():
    """Test convenience get_prompt function."""
    prompt = get_prompt("default")
    assert prompt


@pytest.fixture
def storage_service():
    """Create StorageService instance."""
    config = StorageConfig(storage_path="~/.claude/test_storage")
    return StorageService(config)


def test_storage_setting(storage_service):
    """Test storage setting."""
    storage_service.set_setting("test_key", "test_value")
    result = storage_service.get_setting("test_key")
    assert result == "test_value"


def test_storage_session(storage_service):
    """Test storage session."""
    data = {"cwd": "/tmp", "messages": []}
    storage_service.save_session("test-session", data)

    loaded = storage_service.load_session("test-session")
    assert loaded is not None
    assert loaded["cwd"] == "/tmp"


def test_storage_list_sessions(storage_service):
    """Test listing sessions."""
    storage_service.save_session("test-1", {"cwd": "/tmp"})
    storage_service.save_session("test-2", {"cwd": "/tmp"})
    sessions = storage_service.list_sessions()
    assert len(sessions) >= 2