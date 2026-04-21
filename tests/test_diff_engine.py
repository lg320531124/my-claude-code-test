"""Tests for Diff Engine."""

import pytest

from cc.utils.diff_engine import (
    DiffType,
    ChangeType,
    DiffLine,
    DiffHunk,
    DiffResult,
    DiffConfig,
    DiffEngine,
    diff_contents,
    format_diff,
    apply_patch,
)


class TestDiffType:
    """Test DiffType enum."""

    def test_all_types(self):
        """Test all diff types."""
        assert DiffType.UNIFIED.value == "unified"
        assert DiffType.CONTEXT.value == "context"
        assert DiffType.SIDE_BY_SIDE.value == "side_by_side"


class TestChangeType:
    """Test ChangeType enum."""

    def test_all_types(self):
        """Test all change types."""
        assert ChangeType.ADD.value == "add"
        assert ChangeType.DELETE.value == "delete"
        assert ChangeType.MODIFY.value == "modify"
        assert ChangeType.CONTEXT.value == "context"


class TestDiffLine:
    """Test DiffLine."""

    def test_create(self):
        """Test creating diff line."""
        line = DiffLine(type=ChangeType.ADD, content="hello")
        assert line.type == ChangeType.ADD
        assert line.content == "hello"


class TestDiffHunk:
    """Test DiffHunk."""

    def test_create(self):
        """Test creating diff hunk."""
        hunk = DiffHunk(old_start=1, old_count=5, new_start=1, new_count=5)
        assert hunk.old_start == 1
        assert len(hunk.lines) == 0


class TestDiffResult:
    """Test DiffResult."""

    def test_create(self):
        """Test creating diff result."""
        result = DiffResult()
        assert result.has_changes is False
        assert result.additions == 0
        assert result.deletions == 0

    def test_has_changes(self):
        """Test has_changes."""
        hunk = DiffHunk(old_start=1, old_count=1, new_start=1, new_count=1)
        hunk.lines.append(DiffLine(type=ChangeType.ADD, content="x"))
        result = DiffResult(hunks=[hunk])
        assert result.has_changes is True

    def test_additions(self):
        """Test counting additions."""
        hunk = DiffHunk(old_start=1, old_count=0, new_start=1, new_count=3)
        hunk.lines.append(DiffLine(type=ChangeType.ADD, content="a"))
        hunk.lines.append(DiffLine(type=ChangeType.ADD, content="b"))
        hunk.lines.append(DiffLine(type=ChangeType.ADD, content="c"))
        result = DiffResult(hunks=[hunk])
        assert result.additions == 3

    def test_deletions(self):
        """Test counting deletions."""
        hunk = DiffHunk(old_start=1, old_count=3, new_start=1, new_count=0)
        hunk.lines.append(DiffLine(type=ChangeType.DELETE, content="a"))
        hunk.lines.append(DiffLine(type=ChangeType.DELETE, content="b"))
        result = DiffResult(hunks=[hunk])
        assert result.deletions == 2


class TestDiffConfig:
    """Test DiffConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = DiffConfig()
        assert config.context_lines == 3
        assert config.ignore_whitespace is False

    def test_custom(self):
        """Test custom configuration."""
        config = DiffConfig(context_lines=5, ignore_whitespace=True)
        assert config.context_lines == 5
        assert config.ignore_whitespace is True


class TestDiffEngine:
    """Test DiffEngine."""

    def test_init(self):
        """Test initialization."""
        engine = DiffEngine()
        assert engine.config is not None

    def test_diff_no_changes(self):
        """Test diff with no changes."""
        engine = DiffEngine()
        result = engine.diff("hello\nworld", "hello\nworld")
        assert result.has_changes is False

    def test_diff_additions(self):
        """Test diff with additions."""
        engine = DiffEngine()
        result = engine.diff("", "hello\nworld")
        assert result.has_changes is True
        assert result.additions == 2

    def test_diff_deletions(self):
        """Test diff with deletions."""
        engine = DiffEngine()
        result = engine.diff("hello\nworld", "")
        assert result.has_changes is True
        assert result.deletions == 2

    def test_diff_modifications(self):
        """Test diff with modifications."""
        engine = DiffEngine()
        result = engine.diff("hello", "world")
        assert result.has_changes is True
        assert result.deletions == 1
        assert result.additions == 1

    def test_diff_with_paths(self):
        """Test diff with file paths."""
        engine = DiffEngine()
        result = engine.diff("a", "b", old_path="old.txt", new_path="new.txt")
        assert result.old_path == "old.txt"
        assert result.new_path == "new.txt"

    def test_format_diff(self):
        """Test formatting diff."""
        engine = DiffEngine()
        result = engine.diff("hello", "world", "old.txt", "new.txt")
        formatted = engine.format_diff(result)
        assert "--- old.txt" in formatted
        assert "+++ new.txt" in formatted
        assert "@@" in formatted

    def test_parse_diff(self):
        """Test parsing diff."""
        engine = DiffEngine()
        diff_text = "--- a.txt\n+++ b.txt\n@@ -1,1 +1,1 @@\n-hello\n+world"
        result = engine.parse_diff(diff_text)
        assert result.old_path == "a.txt"
        assert result.new_path == "b.txt"
        assert len(result.hunks) == 1

    def test_apply_patch(self):
        """Test applying patch."""
        engine = DiffEngine()
        old_content = "hello\nworld"
        new_content = "hello\npython"
        diff_result = engine.diff(old_content, new_content)
        patched = engine.apply_patch(old_content, diff_result)
        assert patched == new_content

    def test_apply_patch_with_add(self):
        """Test applying patch with additions."""
        engine = DiffEngine()
        old_content = "hello"
        new_content = "hello\nworld"
        diff_result = engine.diff(old_content, new_content)
        patched = engine.apply_patch(old_content, diff_result)
        assert patched == new_content

    def test_apply_patch_with_delete(self):
        """Test applying patch with deletions."""
        engine = DiffEngine()
        old_content = "hello\nworld"
        new_content = "hello"
        diff_result = engine.diff(old_content, new_content)
        patched = engine.apply_patch(old_content, diff_result)
        assert patched == new_content

    def test_reverse_diff(self):
        """Test reversing diff."""
        engine = DiffEngine()
        old_content = "hello"
        new_content = "world"
        diff_result = engine.diff(old_content, new_content)
        reversed_result = engine.reverse_diff(diff_result)
        assert reversed_result.old_path == diff_result.new_path
        assert reversed_result.new_path == diff_result.old_path

    def test_merge_diffs(self):
        """Test merging diffs."""
        engine = DiffEngine()
        diff1 = engine.diff("a", "b")
        diff2 = engine.diff("c", "d")
        merged = engine.merge_diffs(diff1, diff2)
        assert len(merged.hunks) == len(diff1.hunks) + len(diff2.hunks)


class TestHelperFunctions:
    """Test helper functions."""

    def test_diff_contents(self):
        """Test diff_contents function."""
        result = diff_contents("hello", "world")
        assert result.has_changes is True

    def test_format_diff(self):
        """Test format_diff function."""
        result = diff_contents("hello", "world", "old.txt", "new.txt")
        formatted = format_diff(result)
        assert "--- old.txt" in formatted

    def test_apply_patch(self):
        """Test apply_patch function."""
        diff_text = "--- a\n+++ b\n@@ -1,1 +1,1 @@\n-hello\n+world"
        patched = apply_patch("hello", diff_text)
        assert patched == "world"