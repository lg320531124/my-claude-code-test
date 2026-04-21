"""Process Input - Process and sanitize input."""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

from ..utils.log import get_logger

logger = get_logger(__name__)


class InputType(Enum):
    """Input types."""
    TEXT = "text"
    COMMAND = "command"
    CODE = "code"
    FILE = "file"
    IMAGE = "image"
    URL = "url"


class InputStatus(Enum):
    """Input processing status."""
    RAW = "raw"
    SANITIZED = "sanitized"
    VALIDATED = "validated"
    READY = "ready"
    ERROR = "error"


@dataclass
class InputConfig:
    """Input processing configuration."""
    max_length: int = 100000
    allow_code: bool = True
    allow_files: bool = True
    allow_images: bool = True
    allow_urls: bool = True
    sanitize_html: bool = True


@dataclass
class ProcessedInput:
    """Processed input result."""
    original: str
    processed: str
    type: InputType
    status: InputStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class InputProcessor:
    """Process and sanitize user input."""

    def __init__(self, config: Optional[InputConfig] = None):
        self.config = config or InputConfig()
        self._patterns: Dict[str, re.Pattern] = {
            "url": re.compile(r'https?://[^\s]+'),
            "file": re.compile(r'^/[\w/.-]+$|^[A-Za-z]:\\[\w\\.-]+$'),
            "command": re.compile(r'^[a-zA-Z0-9_-]+\s+'),
        }

    async def process(
        self,
        input_str: str,
        detect_type: bool = True
    ) -> ProcessedInput:
        """Process input string."""
        result = ProcessedInput(
            original=input_str,
            processed=input_str,
            type=InputType.TEXT,
            status=InputStatus.RAW,
        )

        # Validate length
        if len(input_str) > self.config.max_length:
            result.errors.append(f"Input too long: {len(input_str)} > {self.config.max_length}")
            result.status = InputStatus.ERROR
            return result

        # Detect type
        if detect_type:
            result.type = self._detect_type(input_str)
            result.metadata["detected_type"] = result.type.value

        # Sanitize
        result.processed = await self._sanitize(input_str)
        result.status = InputStatus.SANITIZED

        # Validate
        validation_errors = await self._validate(result.processed, result.type)
        if validation_errors:
            result.errors.extend(validation_errors)
            result.status = InputStatus.ERROR
        else:
            result.status = InputStatus.VALIDATED

        # Ready if no errors
        if not result.errors:
            result.status = InputStatus.READY

        return result

    def _detect_type(self, input_str: str) -> InputType:
        """Detect input type."""
        # Check for URL
        if self._patterns["url"].search(input_str):
            return InputType.URL

        # Check for file path
        if self._patterns["file"].match(input_str.strip()):
            return InputType.FILE

        # Check for code (looks like code)
        code_indicators = ["def ", "class ", "function ", "import ", "from ", "const ", "let ", "var "]
        if any(ind in input_str for ind in code_indicators):
            return InputType.CODE

        # Check for command
        if self._patterns["command"].match(input_str.strip()):
            return InputType.COMMAND

        return InputType.TEXT

    async def _sanitize(self, input_str: str) -> str:
        """Sanitize input."""
        sanitized = input_str

        # Remove dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+=',
        ]

        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

        # Trim whitespace
        sanitized = sanitized.strip()

        return sanitized

    async def _validate(
        self,
        input_str: str,
        type: InputType
    ) -> List[str]:
        """Validate input."""
        errors = []

        # Type-specific validation
        if type == InputType.URL:
            if not self.config.allow_urls:
                errors.append("URLs not allowed")

        elif type == InputType.FILE:
            if not self.config.allow_files:
                errors.append("File paths not allowed")

        elif type == InputType.IMAGE:
            if not self.config.allow_images:
                errors.append("Images not allowed")

        elif type == InputType.CODE:
            if not self.config.allow_code:
                errors.append("Code blocks not allowed")

        return errors

    async def process_stream(
        self,
        stream: AsyncIterator[str]
    ) -> AsyncIterator[ProcessedInput]:
        """Process input stream."""
        buffer = ""

        for chunk in stream:
            buffer += chunk

            # Process complete lines
            if "\n" in buffer:
                lines = buffer.split("\n")
                buffer = lines[-1]

                for line in lines[:-1]:
                    if line.strip():
                        result = await self.process(line)
                        yield result

        # Process remaining buffer
        if buffer.strip():
            result = await self.process(buffer)
            yield result

    async def split_commands(self, input_str: str) -> List[str]:
        """Split input into individual commands."""
        # Split by &&, ||, ;, newlines
        separators = ["&&", "||", ";", "\n"]

        commands = [input_str]

        for sep in separators:
            new_commands = []
            for cmd in commands:
                parts = cmd.split(sep)
                new_commands.extend([p.strip() for p in parts if p.strip()])
            commands = new_commands

        return commands

    async def extract_code_blocks(
        self,
        input_str: str
    ) -> List[Dict[str, Any]]:
        """Extract code blocks from input."""
        blocks = []

        # Match ```language code ```
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, input_str, re.DOTALL)

        for lang, code in matches:
            blocks.append({
                "language": lang or "text",
                "code": code.strip(),
            })

        return blocks

    async def extract_urls(self, input_str: str) -> List[str]:
        """Extract URLs from input."""
        return self._patterns["url"].findall(input_str)

    async def extract_file_paths(self, input_str: str) -> List[str]:
        """Extract file paths from input."""
        return self._patterns["file"].findall(input_str)


__all__ = [
    "InputType",
    "InputStatus",
    "InputConfig",
    "ProcessedInput",
    "InputProcessor",
]