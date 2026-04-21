"""Output Handler - Handle command output."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

from ...utils.log import get_logger

logger = get_logger(__name__)


class OutputType(Enum):
    """Output types."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    CODE = "code"
    TABLE = "table"
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"
    INFO = "info"


class OutputFormat(Enum):
    """Output formats."""
    PLAIN = "plain"
    PRETTY = "pretty"
    COMPACT = "compact"
    RAW = "raw"


@dataclass
class OutputChunk:
    """Output chunk."""
    type: OutputType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    index: int = 0


@dataclass
class OutputConfig:
    """Output configuration."""
    format: OutputFormat = OutputFormat.PRETTY
    colorize: bool = True
    max_width: int = 80
    indent: int = 2
    show_timestamps: bool = False
    buffer_size: int = 100


@dataclass
class OutputResult:
    """Output result."""
    chunks: List[OutputChunk] = field(default_factory=list)
    total_length: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = True


class OutputHandler:
    """Handle command output."""

    def __init__(self, config: Optional[OutputConfig] = None):
        self.config = config or OutputConfig()
        self._buffer: List[OutputChunk] = []
        self._callbacks: List[callable] = []
        self._stream_active: bool = False

    async def handle(
        self,
        content: str,
        type: OutputType = OutputType.TEXT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OutputChunk:
        """Handle output content."""
        import time

        chunk = OutputChunk(
            type=type,
            content=content,
            metadata=metadata or {},
            timestamp=time.time(),
            index=len(self._buffer),
        )

        # Format content
        formatted = await self._format_content(chunk)

        # Buffer
        self._buffer.append(chunk)

        # Trim buffer
        if len(self._buffer) > self.config.buffer_size:
            self._buffer = self._buffer[-self.config.buffer_size:]

        # Call callbacks
        await self._call_callbacks(chunk)

        return chunk

    async def _format_content(
        self,
        chunk: OutputChunk
    ) -> str:
        """Format content based on config."""
        content = chunk.content

        if self.config.format == OutputFormat.RAW:
            return content

        if chunk.type == OutputType.JSON:
            import json

            try:
                data = json.loads(content)
                formatted = json.dumps(
                    data,
                    indent=self.config.indent if self.config.format == OutputFormat.PRETTY else None
                )
                return formatted
            except:
                return content

        if chunk.type == OutputType.CODE:
            # Indent code
            lines = content.split("\n")
            return "\n".join(lines)

        if chunk.type == OutputType.TABLE:
            # Format as table
            return await self._format_table(content)

        return content

    async def _format_table(
        self,
        content: str
    ) -> str:
        """Format table content."""
        import json

        try:
            data = json.loads(content)

            if isinstance(data, list) and len(data) > 0:
                headers = list(data[0].keys())
                rows = [headers]

                for item in data:
                    row = [str(item.get(h, "")) for h in headers]
                    rows.append(row)

                # Calculate widths
                widths = [
                    max(len(row[i]) for row in rows)
                    for i in range(len(headers))
                ]

                # Build table
                lines = []

                for row in rows:
                    cells = [
                        row[i].ljust(widths[i])
                        for i in range(len(row))
                    ]
                    lines.append(" | ".join(cells))

                if len(rows) > 1:
                    separator = "-+-".join(
                        "-" * w for w in widths
                    )
                    lines.insert(1, separator)

                return "\n".join(lines)
        except:
            pass

        return content

    async def _call_callbacks(
        self,
        chunk: OutputChunk
    ) -> None:
        """Call registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(chunk)
                else:
                    callback(chunk)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def stream(
        self,
        iterator: AsyncIterator[str]
    ) -> OutputResult:
        """Stream output."""
        result = OutputResult()
        self._stream_active = True

        try:
            index = 0

            async for content in iterator:
                if not self._stream_active:
                    break

                chunk = await self.handle(
                    content,
                    OutputType.TEXT
                )

                chunk.index = index
                result.chunks.append(chunk)
                result.total_length += len(content)
                index += 1

        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        self._stream_active = False
        return result

    async def stop_stream(self) -> None:
        """Stop streaming."""
        self._stream_active = False

    async def error(
        self,
        message: str,
        code: Optional[str] = None
    ) -> OutputChunk:
        """Handle error output."""
        return await self.handle(
            message,
            OutputType.ERROR,
            {"code": code}
        )

    async def success(
        self,
        message: str
    ) -> OutputChunk:
        """Handle success output."""
        return await self.handle(
            message,
            OutputType.SUCCESS
        )

    async def warning(
        self,
        message: str
    ) -> OutputChunk:
        """Handle warning output."""
        return await self.handle(
            message,
            OutputType.WARNING
        )

    async def info(
        self,
        message: str
    ) -> OutputChunk:
        """Handle info output."""
        return await self.handle(
            message,
            OutputType.INFO
        )

    async def code(
        self,
        content: str,
        language: Optional[str] = None
    ) -> OutputChunk:
        """Handle code output."""
        return await self.handle(
            content,
            OutputType.CODE,
            {"language": language}
        )

    async def table(
        self,
        data: List[Dict[str, Any]]
    ) -> OutputChunk:
        """Handle table output."""
        import json

        return await self.handle(
            json.dumps(data),
            OutputType.TABLE
        )

    async def json(
        self,
        data: Dict[str, Any]
    ) -> OutputChunk:
        """Handle JSON output."""
        import json

        return await self.handle(
            json.dumps(data),
            OutputType.JSON
        )

    async def markdown(
        self,
        content: str
    ) -> OutputChunk:
        """Handle markdown output."""
        return await self.handle(
            content,
            OutputType.MARKDOWN
        )

    async def get_buffer(
        self,
        limit: int = 50
    ) -> List[OutputChunk]:
        """Get buffered output."""
        return self._buffer[-limit:]

    async def clear_buffer(self) -> int:
        """Clear buffer."""
        count = len(self._buffer)
        self._buffer.clear()
        return count

    async def get_result(self) -> OutputResult:
        """Get output result."""
        return OutputResult(
            chunks=self._buffer,
            total_length=sum(len(c.content) for c in self._buffer),
            success=True,
        )

    def register_callback(
        self,
        callback: callable
    ) -> None:
        """Register output callback."""
        self._callbacks.append(callback)


__all__ = [
    "OutputType",
    "OutputFormat",
    "OutputChunk",
    "OutputConfig",
    "OutputResult",
    "OutputHandler",
]