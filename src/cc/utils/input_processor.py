"""Input Processing - Handle user input with validation and parsing."""

from __future__ import annotations
import re
import shlex
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .log import get_logger

logger = get_logger(__name__)


class InputType(Enum):
    """Types of input."""
    COMMAND = "command"       # Slash command like /commit
    QUESTION = "question"     # Direct question
    TASK = "task"             # Task instruction
    CODE = "code"             # Code snippet
    FILE_PATH = "file_path"   # File path reference
    URL = "url"               # URL reference
    MIXED = "mixed"           # Mixed content
    EMPTY = "empty"           # Empty input


@dataclass
class ParsedInput:
    """Parsed input result."""
    raw: str
    type: InputType
    content: str = ""
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    file_paths: List[Path] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InputConfig:
    """Input processing configuration."""
    max_length: int = 100000
    allowed_commands: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r"rm\s+-rf\s+/",  # Dangerous rm
        r">\s*/dev/sda",  # Disk write
        r":()\s*{\s*:\s*&\s*};\s*:",  # Fork bomb
    ])
    sanitize_html: bool = True
    extract_files: bool = True
    extract_urls: bool = True


class InputProcessor:
    """Process and validate user input."""

    # Command pattern: starts with /
    COMMAND_PATTERN = re.compile(r"^/([a-zA-Z0-9_-]+)(?:\s+(.*))?$")

    # File path patterns
    FILE_PATH_PATTERNS = [
        re.compile(r"(?:^|\s)([./][a-zA-Z0-9_/.-]+(?:\.[a-zA-Z0-9]+)?)(?:\s|$)"),
        re.compile(r"(?:^|\s)([a-zA-Z0-9_/.-]+/[a-zA-Z0-9_/.-]+)(?:\s|$)"),
        re.compile(r"`([^`]+)`"),  # Backtick paths
    ]

    # URL pattern
    URL_PATTERN = re.compile(r"https?://[^\s<>\"']+[^\s<>\"'.]")

    def __init__(self, config: Optional[InputConfig] = None):
        self.config = config or InputConfig()

    def process(self, raw_input: str) -> ParsedInput:
        """Process raw input."""
        # Handle empty input
        if not raw_input or not raw_input.strip():
            return ParsedInput(raw=raw_input, type=InputType.EMPTY)

        # Trim and normalize
        raw_input = raw_input.strip()
        raw_input = self._normalize_whitespace(raw_input)

        # Check max length
        if len(raw_input) > self.config.max_length:
            raw_input = raw_input[:self.config.max_length]
            logger.warning(f"Input truncated to {self.config.max_length} chars")

        # Check for blocked patterns
        if self._has_blocked_pattern(raw_input):
            return ParsedInput(
                raw=raw_input,
                type=InputType.MIXED,
                content="[BLOCKED] Input contains potentially dangerous pattern",
                metadata={"blocked": True},
            )

        # Detect type and parse
        parsed = self._detect_and_parse(raw_input)

        # Sanitize if needed
        if self.config.sanitize_html:
            parsed.content = self._sanitize_html(parsed.content)

        return parsed

    def _detect_and_parse(self, input_str: str) -> ParsedInput:
        """Detect input type and parse."""
        # Check for command
        command_match = self.COMMAND_PATTERN.match(input_str)
        if command_match:
            command = command_match.group(1)
            args_str = command_match.group(2) or ""

            # Parse args
            try:
                args = shlex.split(args_str)
            except ValueError:
                args = args_str.split()

            return ParsedInput(
                raw=input_str,
                type=InputType.COMMAND,
                content=args_str,
                command=command,
                args=args,
            )

        # Extract file paths
        file_paths = []
        if self.config.extract_files:
            file_paths = self._extract_file_paths(input_str)

        # Extract URLs
        urls = []
        if self.config.extract_urls:
            urls = self._extract_urls(input_str)

        # Determine type based on content
        if file_paths and urls:
            return ParsedInput(
                raw=input_str,
                type=InputType.MIXED,
                content=input_str,
                file_paths=file_paths,
                urls=urls,
            )
        elif file_paths:
            return ParsedInput(
                raw=input_str,
                type=InputType.FILE_PATH if len(file_paths) == 1 and input_str.strip() == str(file_paths[0]) else InputType.MIXED,
                content=input_str,
                file_paths=file_paths,
            )
        elif urls:
            return ParsedInput(
                raw=input_str,
                type=InputType.URL if len(urls) == 1 and input_str.strip() == urls[0] else InputType.MIXED,
                content=input_str,
                urls=urls,
            )

        # Check if it looks like a question
        if self._is_question(input_str):
            return ParsedInput(
                raw=input_str,
                type=InputType.QUESTION,
                content=input_str,
            )

        # Check if it looks like code
        if self._looks_like_code(input_str):
            return ParsedInput(
                raw=input_str,
                type=InputType.CODE,
                content=input_str,
            )

        # Default to task
        return ParsedInput(
            raw=input_str,
            type=InputType.TASK,
            content=input_str,
        )

    def _normalize_whitespace(self, input_str: str) -> str:
        """Normalize whitespace."""
        # Replace multiple spaces with single
        return re.sub(r"\s+", " ", input_str)

    def _has_blocked_pattern(self, input_str: str) -> bool:
        """Check for blocked patterns."""
        for pattern in self.config.blocked_patterns:
            if re.search(pattern, input_str):
                return True
        return False

    def _extract_file_paths(self, input_str: str) -> List[Path]:
        """Extract file paths from input."""
        paths = []

        for pattern in self.FILE_PATH_PATTERNS:
            matches = pattern.findall(input_str)
            for match in matches:
                try:
                    path = Path(match)
                    # Only include if looks like valid path
                    if path.suffix or path.name.startswith(".") or "/" in match:
                        paths.append(path)
                except Exception:
                    continue

        return paths

    def _extract_urls(self, input_str: str) -> List[str]:
        """Extract URLs from input."""
        return self.URL_PATTERN.findall(input_str)

    def _is_question(self, input_str: str) -> bool:
        """Check if input is a question."""
        question_markers = [
            "?",
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
            "which",
            "can you",
            "could you",
            "would you",
            "is there",
            "are there",
            "does",
            "do",
        ]

        input_lower = input_str.lower()

        for marker in question_markers:
            if marker in input_lower:
                return True

        return False

    def _looks_like_code(self, input_str: str) -> bool:
        """Check if input looks like code."""
        code_markers = [
            r"def\s+\w+\s*\(",  # Python function
            r"function\s+\w+\s*\(",  # JS function
            r"class\s+\w+",  # Class definition
            r"import\s+\w+",  # Import statement
            r"from\s+\w+\s+import",  # Python import
            r"const\s+\w+\s*=",  # JS const
            r"let\s+\w+\s*=",  # JS let
            r"var\s+\w+\s*=",  # JS var
            r"{\s*\".*\":\s*.*\s*}",  # JSON-like
            r"<\w+>",  # HTML tag
            r"\(\s*\)\s*=>",  # Arrow function
            r"async\s+def",  # Async function
        ]

        for pattern in code_markers:
            if re.search(pattern, input_str):
                return True

        return False

    def _sanitize_html(self, content: str) -> str:
        """Sanitize HTML content."""
        # Remove script tags
        content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL)

        # Remove dangerous attributes
        content = re.sub(r"\s*on\w+\s*=\s*['\"].*?['\"]", "", content, flags=re.IGNORECASE)

        return content

    def validate_command(self, command: str) -> bool:
        """Validate a command name."""
        if not self.config.allowed_commands:
            return True  # Allow all if not restricted

        return command in self.config.allowed_commands

    def split_multiline(self, input_str: str) -> List[str]:
        """Split multi-line input into separate inputs."""
        lines = input_str.strip().split("\n")
        return [line.strip() for line in lines if line.strip()]


def process_input(input_str: str, config: Optional[InputConfig] = None) -> ParsedInput:
    """Process input with default configuration."""
    processor = InputProcessor(config)
    return processor.process(input_str)


def is_command(input_str: str) -> bool:
    """Check if input is a slash command."""
    return bool(InputProcessor.COMMAND_PATTERN.match(input_str.strip()))


def extract_command(input_str: str) -> Optional[Tuple[str, List[str]]]:
    """Extract command and args from input."""
    match = InputProcessor.COMMAND_PATTERN.match(input_str.strip())
    if match:
        command = match.group(1)
        args_str = match.group(2) or ""
        try:
            args = shlex.split(args_str)
        except ValueError:
            args = args_str.split()
        return (command, args)
    return None


__all__ = [
    "InputType",
    "ParsedInput",
    "InputConfig",
    "InputProcessor",
    "process_input",
    "is_command",
    "extract_command",
]