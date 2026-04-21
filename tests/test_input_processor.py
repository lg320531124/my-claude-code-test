"""Tests for Input Processor."""

import pytest
from pathlib import Path

from cc.utils.input_processor import (
    InputType,
    ParsedInput,
    InputConfig,
    InputProcessor,
    process_input,
    is_command,
    extract_command,
)


class TestInputType:
    """Test InputType enum."""

    def test_all_types(self):
        """Test all input types exist."""
        assert InputType.COMMAND.value == "command"
        assert InputType.QUESTION.value == "question"
        assert InputType.TASK.value == "task"
        assert InputType.CODE.value == "code"
        assert InputType.FILE_PATH.value == "file_path"
        assert InputType.URL.value == "url"
        assert InputType.MIXED.value == "mixed"
        assert InputType.EMPTY.value == "empty"


class TestParsedInput:
    """Test ParsedInput."""

    def test_create(self):
        """Test creating parsed input."""
        parsed = ParsedInput(raw="test", type=InputType.TASK)
        assert parsed.raw == "test"
        assert parsed.type == InputType.TASK

    def test_with_metadata(self):
        """Test with metadata."""
        parsed = ParsedInput(
            raw="test",
            type=InputType.TASK,
            metadata={"key": "value"},
        )
        assert parsed.metadata["key"] == "value"


class TestInputProcessor:
    """Test InputProcessor."""

    def test_init(self):
        """Test initialization."""
        processor = InputProcessor()
        assert processor.config is not None

    def test_empty_input(self):
        """Test empty input."""
        processor = InputProcessor()
        parsed = processor.process("")
        assert parsed.type == InputType.EMPTY

    def test_whitespace_input(self):
        """Test whitespace input."""
        processor = InputProcessor()
        parsed = processor.process("   ")
        assert parsed.type == InputType.EMPTY

    def test_command_input(self):
        """Test command input."""
        processor = InputProcessor()
        parsed = processor.process("/commit")
        assert parsed.type == InputType.COMMAND
        assert parsed.command == "commit"

    def test_command_with_args(self):
        """Test command with args."""
        processor = InputProcessor()
        parsed = processor.process("/review src/main.py")
        assert parsed.type == InputType.COMMAND
        assert parsed.command == "review"
        assert len(parsed.args) == 1

    def test_question_input(self):
        """Test question input."""
        processor = InputProcessor()
        parsed = processor.process("What does this function do?")
        assert parsed.type == InputType.QUESTION

    def test_task_input(self):
        """Test task input."""
        processor = InputProcessor()
        parsed = processor.process("Fix the bug in main.py")
        assert parsed.type == InputType.TASK

    def test_code_input(self):
        """Test code input."""
        processor = InputProcessor()
        parsed = processor.process("def hello():\n    return 'world'")
        assert parsed.type == InputType.CODE

    def test_url_input(self):
        """Test URL input."""
        processor = InputProcessor()
        parsed = processor.process("https://example.com/path")
        assert parsed.type == InputType.URL
        assert len(parsed.urls) == 1

    def test_file_path_input(self):
        """Test file path input."""
        processor = InputProcessor()
        parsed = processor.process("./src/main.py")
        # Could be FILE_PATH or MIXED depending on detection
        assert parsed.type in (InputType.FILE_PATH, InputType.MIXED)
        assert len(parsed.file_paths) >= 1

    def test_mixed_input(self):
        """Test mixed input."""
        processor = InputProcessor()
        parsed = processor.process("Check https://example.com and ./file.py")
        assert parsed.type == InputType.MIXED
        assert len(parsed.urls) >= 1

    def test_blocked_pattern(self):
        """Test blocked pattern detection."""
        processor = InputProcessor()
        parsed = processor.process("rm -rf /something")
        assert parsed.metadata.get("blocked") is True

    def test_max_length(self):
        """Test max length truncation."""
        config = InputConfig(max_length=100)
        processor = InputProcessor(config)
        parsed = processor.process("a" * 200)
        assert len(parsed.raw) == 100

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        processor = InputProcessor()
        parsed = processor.process("hello    world")
        assert parsed.raw == "hello world"

    def test_split_multiline(self):
        """Test splitting multiline input."""
        processor = InputProcessor()
        lines = processor.split_multiline("line1\nline2\nline3")
        assert len(lines) == 3

    def test_validate_command(self):
        """Test command validation."""
        config = InputConfig(allowed_commands=["commit", "review"])
        processor = InputProcessor(config)

        assert processor.validate_command("commit") is True
        assert processor.validate_command("unknown") is False


class TestHelperFunctions:
    """Test helper functions."""

    def test_process_input(self):
        """Test process_input function."""
        parsed = process_input("/help")
        assert parsed.type == InputType.COMMAND

    def test_is_command(self):
        """Test is_command function."""
        assert is_command("/commit") is True
        assert is_command("regular text") is False

    def test_extract_command(self):
        """Test extract_command function."""
        result = extract_command("/review file.py")
        assert result is not None
        assert result[0] == "review"
        assert result[1] == ["file.py"]

    def test_extract_command_none(self):
        """Test extract_command with non-command."""
        result = extract_command("regular text")
        assert result is None


class TestInputConfig:
    """Test InputConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = InputConfig()
        assert config.max_length == 100000
        assert config.sanitize_html is True

    def test_custom(self):
        """Test custom configuration."""
        config = InputConfig(
            max_length=500,
            allowed_commands=["test"],
        )
        assert config.max_length == 500
        assert "test" in config.allowed_commands