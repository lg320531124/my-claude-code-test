"""Tests for Text Formatter."""

import pytest

from cc.utils.text_formatter import (
    TextFormat,
    TextAlign,
    FormatConfig,
    FormattedText,
    TextFormatter,
    format_text,
    truncate_text,
    indent_text,
    compact_text,
    create_table,
)


class TestTextFormat:
    """Test TextFormat enum."""

    def test_all_formats(self):
        """Test all format types exist."""
        assert TextFormat.PLAIN.value == "plain"
        assert TextFormat.MARKDOWN.value == "markdown"
        assert TextFormat.HTML.value == "html"
        assert TextFormat.CODE.value == "code"
        assert TextFormat.JSON.value == "json"


class TestTextAlign:
    """Test TextAlign enum."""

    def test_all_alignments(self):
        """Test all alignment options."""
        assert TextAlign.LEFT.value == "left"
        assert TextAlign.CENTER.value == "center"
        assert TextAlign.RIGHT.value == "right"


class TestFormatConfig:
    """Test FormatConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = FormatConfig()
        assert config.max_width == 80
        assert config.wrap is True
        assert config.format == TextFormat.PLAIN

    def test_custom(self):
        """Test custom configuration."""
        config = FormatConfig(
            max_width=100,
            indent=2,
            wrap=False,
        )
        assert config.max_width == 100
        assert config.indent == 2


class TestFormattedText:
    """Test FormattedText."""

    def test_create(self):
        """Test creating formatted text."""
        result = FormattedText(
            text="test",
            original="test",
            format=TextFormat.PLAIN,
            lines=1,
            width=4,
        )
        assert result.text == "test"
        assert result.lines == 1


class TestTextFormatter:
    """Test TextFormatter."""

    def test_init(self):
        """Test initialization."""
        formatter = TextFormatter()
        assert formatter.config is not None

    def test_format_plain(self):
        """Test formatting plain text."""
        formatter = TextFormatter()
        result = formatter.format("hello world")
        assert result.format == TextFormat.PLAIN
        assert result.text == "hello world"

    def test_format_with_indent(self):
        """Test formatting with indent."""
        config = FormatConfig(indent=2)
        formatter = TextFormatter(config)
        result = formatter.format("hello")
        assert result.text.startswith("  ")

    def test_format_code(self):
        """Test formatting code."""
        formatter = TextFormatter()
        result = formatter.format("print('hello')\nprint('world')", TextFormat.CODE)
        assert "1" in result.text
        assert "2" in result.text

    def test_format_html(self):
        """Test formatting HTML."""
        formatter = TextFormatter()
        result = formatter.format("<script>", TextFormat.HTML)
        assert "&lt;" in result.text

    def test_truncate(self):
        """Test truncation."""
        formatter = TextFormatter()
        result = formatter.truncate("a" * 100, 50)
        assert len(result.text) <= 50 + 3
        assert result.truncated is True

    def test_truncate_no_need(self):
        """Test truncation when not needed."""
        formatter = TextFormatter()
        result = formatter.truncate("short", 50)
        assert result.text == "short"
        assert result.truncated is False

    def test_indent(self):
        """Test indentation."""
        formatter = TextFormatter()
        result = formatter.indent("hello\nworld", level=2)
        assert result.startswith("    ")

    def test_dedent(self):
        """Test dedent."""
        formatter = TextFormatter()
        result = formatter.dedent("    hello\n    world")
        assert result == "hello\nworld"

    def test_center(self):
        """Test center text."""
        formatter = TextFormatter()
        result = formatter.center("hello", width=20)
        assert len(result) == 20
        assert "hello" in result

    def test_justify(self):
        """Test justify text."""
        formatter = TextFormatter()
        result = formatter.justify("hello", width=20)
        assert len(result) == 20

    def test_strip_lines(self):
        """Test strip lines."""
        formatter = TextFormatter()
        result = formatter.strip_lines("  hello  \n  world  ")
        assert result == "hello\nworld"

    def test_normalize_spaces(self):
        """Test normalize spaces."""
        formatter = TextFormatter()
        result = formatter.normalize_spaces("hello    world")
        assert result == "hello world"

    def test_normalize_newlines(self):
        """Test normalize newlines."""
        formatter = TextFormatter()
        result = formatter.normalize_newlines("hello\n\n\n\nworld")
        assert result == "hello\n\nworld"

    def test_remove_empty_lines(self):
        """Test remove empty lines."""
        formatter = TextFormatter()
        result = formatter.remove_empty_lines("hello\n\n\nworld")
        assert result == "hello\nworld"

    def test_compact(self):
        """Test compact."""
        formatter = TextFormatter()
        result = formatter.compact("hello    world\n\n\n")
        assert "    " not in result
        assert "\n\n\n" not in result

    def test_title(self):
        """Test title."""
        formatter = TextFormatter()
        result = formatter.title("Hello")
        assert "Hello" in result
        assert "====" in result

    def test_heading(self):
        """Test heading."""
        formatter = TextFormatter()
        result = formatter.heading("Hello", level=2)
        assert result == "## Hello"

    def test_bullet_list(self):
        """Test bullet list."""
        formatter = TextFormatter()
        result = formatter.bullet_list(["one", "two", "three"])
        assert "- one" in result
        assert "- two" in result

    def test_numbered_list(self):
        """Test numbered list."""
        formatter = TextFormatter()
        result = formatter.numbered_list(["one", "two", "three"])
        assert "1. one" in result
        assert "2. two" in result

    def test_table(self):
        """Test table."""
        formatter = TextFormatter()
        result = formatter.table(
            headers=["Name", "Value"],
            rows=[["Alice", "30"], ["Bob", "25"]],
        )
        assert "Name" in result
        assert "Alice" in result
        assert "|" in result

    def test_highlight(self):
        """Test highlight."""
        formatter = TextFormatter()
        result = formatter.highlight("hello world", "world")
        assert "**world**" in result

    def test_wrap_paragraphs(self):
        """Test wrap paragraphs."""
        formatter = TextFormatter()
        result = formatter.wrap_paragraphs("short line\n\nlong line here", width=10)
        assert len(result.split("\n\n")) >= 2


class TestHelperFunctions:
    """Test helper functions."""

    def test_format_text(self):
        """Test format_text function."""
        result = format_text("hello")
        assert result.text == "hello"

    def test_truncate_text(self):
        """Test truncate_text function."""
        result = truncate_text("a" * 100, 50)
        assert len(result) <= 53

    def test_indent_text(self):
        """Test indent_text function."""
        result = indent_text("hello", level=2)
        assert result.startswith("    ")

    def test_compact_text(self):
        """Test compact_text function."""
        result = compact_text("hello    world")
        assert result == "hello world"

    def test_create_table(self):
        """Test create_table function."""
        result = create_table(["A", "B"], [["1", "2"]])
        assert "A" in result
        assert "1" in result