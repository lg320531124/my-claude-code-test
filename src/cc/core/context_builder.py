"""Context Builder - Build context for API calls."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..utils.log import get_logger

logger = get_logger(__name__)


class ContextType(Enum):
    """Context types."""
    SYSTEM = "system"
    PROJECT = "project"
    FILE = "file"
    CONVERSATION = "conversation"
    USER = "user"


class ContextPriority(Enum):
    """Context priority."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ContextBlock:
    """Context block."""
    type: ContextType
    content: str
    priority: ContextPriority
    token_estimate: int = 0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextConfig:
    """Context configuration."""
    max_tokens: int = 100000
    include_system: bool = True
    include_project: bool = True
    include_files: bool = True
    include_history: bool = True
    compression_threshold: float = 0.8


@dataclass
class BuiltContext:
    """Built context."""
    blocks: List[ContextBlock]
    total_tokens: int
    compressed: bool = False
    truncated: bool = False
    sources: List[str] = field(default_factory=list)


class ContextBuilder:
    """Build context for API calls."""

    def __init__(self, config: Optional[ContextConfig] = None):
        self.config = config or ContextConfig()
        self._blocks: List[ContextBlock] = []
        self._token_counter = None

    async def add_system_context(
        self,
        content: str,
        priority: Optional[ContextPriority] = None
    ) -> ContextBlock:
        """Add system context."""
        block = ContextBlock(
            type=ContextType.SYSTEM,
            content=content,
            priority=priority or ContextPriority.CRITICAL,
            token_estimate=len(content) // 4,
            source="system",
        )

        self._blocks.append(block)
        return block

    async def add_project_context(
        self,
        project_path: Path,
        include_claude_md: bool = True
    ) -> List[ContextBlock]:
        """Add project context."""
        blocks = []

        # Add CLAUDE.md if exists
        if include_claude_md:
            claude_md = project_path / "CLAUDE.md"

            if claude_md.exists():
                content = claude_md.read_text()

                block = ContextBlock(
                    type=ContextType.PROJECT,
                    content=content,
                    priority=ContextPriority.HIGH,
                    token_estimate=len(content) // 4,
                    source=str(claude_md),
                )

                blocks.append(block)
                self._blocks.append(block)

        return blocks

    async def add_file_context(
        self,
        file_path: Path,
        priority: ContextPriority = ContextPriority.MEDIUM
    ) -> Optional[ContextBlock]:
        """Add file context."""
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text()

            # Limit file size
            max_file_tokens = 5000
            if len(content) > max_file_tokens * 4:
                content = content[:max_file_tokens * 4]

            block = ContextBlock(
                type=ContextType.FILE,
                content=content,
                priority=priority,
                token_estimate=len(content) // 4,
                source=str(file_path),
            )

            self._blocks.append(block)
            return block

        except Exception as e:
            logger.error(f"Failed to add file context: {e}")
            return None

    async def add_conversation_context(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[ContextBlock]:
        """Add conversation context."""
        blocks = []

        for msg in messages[-10:]:  # Last 10 messages
            content = msg.get("content", "")

            if isinstance(content, str):
                block = ContextBlock(
                    type=ContextType.CONVERSATION,
                    content=content,
                    priority=ContextPriority.MEDIUM,
                    token_estimate=len(content) // 4,
                    source="conversation",
                )

                blocks.append(block)
                self._blocks.append(block)

        return blocks

    async def add_user_context(
        self,
        user_input: str,
        priority: Optional[ContextPriority] = None
    ) -> ContextBlock:
        """Add user context."""
        block = ContextBlock(
            type=ContextType.USER,
            content=user_input,
            priority=priority or ContextPriority.HIGH,
            token_estimate=len(user_input) // 4,
            source="user",
        )

        self._blocks.append(block)
        return block

    async def build(
        self,
        compress: bool = False
    ) -> BuiltContext:
        """Build final context."""
        # Sort by priority
        priority_order = {
            ContextPriority.CRITICAL: 0,
            ContextPriority.HIGH: 1,
            ContextPriority.MEDIUM: 2,
            ContextPriority.LOW: 3,
        }

        sorted_blocks = sorted(
            self._blocks,
            key=lambda b: priority_order.get(b.priority, 2)
        )

        # Calculate total tokens
        total_tokens = sum(b.token_estimate for b in sorted_blocks)

        # Check if needs truncation
        truncated = False

        if total_tokens > self.config.max_tokens:
            truncated = True
            sorted_blocks = await self._truncate_blocks(sorted_blocks)
            total_tokens = sum(b.token_estimate for b in sorted_blocks)

        # Compress if needed
        compressed = False

        if compress and total_tokens > self.config.max_tokens * self.config.compression_threshold:
            compressed = True
            sorted_blocks = await self._compress_blocks(sorted_blocks)
            total_tokens = sum(b.token_estimate for b in sorted_blocks)

        sources = [b.source for b in sorted_blocks]

        return BuiltContext(
            blocks=sorted_blocks,
            total_tokens=total_tokens,
            compressed=compressed,
            truncated=truncated,
            sources=sources,
        )

    async def _truncate_blocks(
        self,
        blocks: List[ContextBlock]
    ) -> List[ContextBlock]:
        """Truncate blocks to fit limit."""
        result = []
        current_tokens = 0

        for block in blocks:
            if current_tokens + block.token_estimate <= self.config.max_tokens:
                result.append(block)
                current_tokens += block.token_estimate
            elif block.priority == ContextPriority.CRITICAL:
                # Always keep critical
                result.append(block)
                current_tokens += block.token_estimate
            else:
                # Partial include
                remaining = self.config.max_tokens - current_tokens

                if remaining > 100:
                    partial_content = block.content[:remaining * 4]
                    partial_block = ContextBlock(
                        type=block.type,
                        content=partial_content,
                        priority=block.priority,
                        token_estimate=remaining,
                        source=block.source,
                        metadata={"truncated": True},
                    )

                    result.append(partial_block)
                    break

        return result

    async def _compress_blocks(
        self,
        blocks: List[ContextBlock]
    ) -> List[ContextBlock]:
        """Compress blocks."""
        compressed = []

        for block in blocks:
            # Simple compression - shorten content
            if block.token_estimate > 1000:
                # Keep first and last parts
                content = block.content
                half = len(content) // 2
                compressed_content = content[:half // 2] + "\n...\n" + content[-half // 2:]

                compressed_block = ContextBlock(
                    type=block.type,
                    content=compressed_content,
                    priority=block.priority,
                    token_estimate=len(compressed_content) // 4,
                    source=block.source,
                    metadata={"compressed": True},
                )

                compressed.append(compressed_block)
            else:
                compressed.append(block)

        return compressed

    def clear(self) -> None:
        """Clear blocks."""
        self._blocks.clear()

    def get_blocks(self) -> List[ContextBlock]:
        """Get current blocks."""
        return self._blocks

    async def get_token_estimate(self) -> int:
        """Get token estimate."""
        return sum(b.token_estimate for b in self._blocks)


__all__ = [
    "ContextType",
    "ContextPriority",
    "ContextBlock",
    "ContextConfig",
    "BuiltContext",
    "ContextBuilder",
]