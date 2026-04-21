"""Tests for memory extraction."""

import pytest
from src.cc.services.memory_extraction import (
    MemoryExtractor,
    MemoryType,
    MemoryPriority,
    ExtractionConfig,
)


@pytest.mark.asyncio
async def test_memory_extractor_init():
    """Test memory extractor initialization."""
    extractor = MemoryExtractor()
    assert extractor.config is not None
    assert extractor._patterns is not None


@pytest.mark.asyncio
async def test_extract_decision():
    """Test decision extraction."""
    extractor = MemoryExtractor()

    conversation = "We decided to use the new approach for this project."
    memories = await extractor.extract(conversation)

    assert len(memories) > 0
    assert any(m.type == MemoryType.DECISION for m in memories)


@pytest.mark.asyncio
async def test_extract_insight():
    """Test insight extraction."""
    extractor = MemoryExtractor()

    conversation = "I found that the performance improved significantly."
    memories = await extractor.extract(conversation)

    assert len(memories) > 0
    assert any(m.type == MemoryType.INSIGHT for m in memories)


@pytest.mark.asyncio
async def test_extract_learning():
    """Test learning extraction."""
    extractor = MemoryExtractor()

    conversation = "I learned that this method works better."
    memories = await extractor.extract(conversation)

    assert len(memories) > 0
    assert any(m.type == MemoryType.LEARNING for m in memories)


@pytest.mark.asyncio
async def test_extract_preference():
    """Test preference extraction."""
    extractor = MemoryExtractor()

    conversation = "I prefer to use Python for this task."
    memories = await extractor.extract(conversation)

    assert len(memories) > 0
    assert any(m.type == MemoryType.PREFERENCE for m in memories)


@pytest.mark.asyncio
async def test_deduplication():
    """Test memory deduplication."""
    extractor = MemoryExtractor(ExtractionConfig(deduplicate=True))

    conversation = """
    We decided to use Python.
    We decided to use Python.
    We decided to use Python.
    """

    memories = await extractor.extract(conversation)

    # Should deduplicate
    content_set = set(m.content.lower() for m in memories)
    assert len(content_set) < len(memories) * 2


@pytest.mark.asyncio
async def test_confidence_filter():
    """Test confidence filtering."""
    extractor = MemoryExtractor(ExtractionConfig(min_confidence=0.7))

    conversation = "We decided to use the new approach."
    memories = await extractor.extract(conversation)

    assert all(m.confidence >= 0.7 for m in memories)


@pytest.mark.asyncio
async def test_categorize():
    """Test categorization."""
    extractor = MemoryExtractor()

    conversation = """
    We decided to use Python.
    I found that it works well.
    I learned something new.
    """

    memories = await extractor.extract(conversation)
    categorized = await extractor.categorize(memories)

    assert isinstance(categorized, dict)
    assert len(categorized) > 0


@pytest.mark.asyncio
async def test_summarize():
    """Test summarization."""
    extractor = MemoryExtractor()

    conversation = "We decided to use Python for this project."
    memories = await extractor.extract(conversation)
    summary = await extractor.summarize(memories)

    assert isinstance(summary, str)
    assert len(summary) > 0


@pytest.mark.asyncio
async def test_export_json():
    """Test JSON export."""
    extractor = MemoryExtractor()

    conversation = "We decided to use Python."
    memories = await extractor.extract(conversation)
    exported = await extractor.export(memories, format="json")

    assert exported.startswith("[")
    assert exported.endswith("]")


@pytest.mark.asyncio
async def test_export_text():
    """Test text export."""
    extractor = MemoryExtractor()

    conversation = "We decided to use Python."
    memories = await extractor.extract(conversation)
    exported = await extractor.export(memories, format="text")

    assert isinstance(exported, str)
    assert "decision" in exported.lower()


@pytest.mark.asyncio
async def test_priority_levels():
    """Test priority determination."""
    extractor = MemoryExtractor()

    # Decision should be high priority
    assert extractor._determine_priority(MemoryType.DECISION) == MemoryPriority.HIGH

    # Insight should be medium
    assert extractor._determine_priority(MemoryType.INSIGHT) == MemoryPriority.MEDIUM


@pytest.mark.asyncio
async def test_max_memories_limit():
    """Test max memories limit."""
    extractor = MemoryExtractor(ExtractionConfig(max_memories=5))

    # Create conversation with many patterns
    conversation = """
    We decided to use Python.
    I found that it works.
    I learned something.
    I prefer this approach.
    This needs to fix.
    We decided again.
    Another finding.
    """

    memories = await extractor.extract(conversation)

    assert len(memories) <= 5