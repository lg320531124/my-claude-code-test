"""Compression Utilities - Async context compression."""

from __future__ import annotations
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..services.token_estimation import estimate_messages_tokens


class CompressionStrategy(Enum):
    """Compression strategies."""
    SUMMARY = "summary"  # Summarize old messages
    MICRO = "micro"  # Keep only recent
    GROUPED = "grouped"  # Group related messages
    TIME_BASED = "time_based"  # Compress by time intervals


@dataclass
class CompressionConfig:
    """Compression configuration."""
    strategy: CompressionStrategy = CompressionStrategy.SUMMARY
    max_tokens: int = 100000
    target_tokens: int = 50000
    keep_recent: int = 10  # Keep last N messages uncompressed
    preserve_user_requests: bool = True  # Keep user messages


@dataclass
class CompressionResult:
    """Compression result."""
    original_messages: int = 0
    original_tokens: int = 0
    compressed_messages: int = 0
    compressed_tokens: int = 0
    strategy_used: CompressionStrategy = CompressionStrategy.SUMMARY
    summary: Optional[str] = None


class MessageCompressor:
    """Compress message history."""

    def __init__(self, config: CompressionConfig = None):
        self.config = config or CompressionConfig()

    async def compress(self, messages: List[Dict]) -> List[Dict]:
        """Compress messages based on strategy."""
        if not messages:
            return messages

        # Estimate current tokens
        current_tokens = await self._estimate_tokens(messages)

        # Check if compression needed
        if current_tokens <= self.config.target_tokens:
            return messages

        # Apply strategy
        if self.config.strategy == CompressionStrategy.SUMMARY:
            return await self._summarize_messages(messages)
        elif self.config.strategy == CompressionStrategy.MICRO:
            return await self._micro_compress(messages)
        elif self.config.strategy == CompressionStrategy.GROUPED:
            return await self._group_compress(messages)
        elif self.config.strategy == CompressionStrategy.TIME_BASED:
            return await self._time_compress(messages)

        return messages

    async def _estimate_tokens(self, messages: List[Dict]) -> int:
        """Estimate total tokens."""
        usage = await estimate_messages_tokens(messages)
        return usage.input_tokens

    async def _summarize_messages(self, messages: List[Dict]) -> List[Dict]:
        """Summarize old messages."""
        if len(messages) <= self.config.keep_recent:
            return messages

        # Split into old and recent
        old_messages = messages[:-self.config.keep_recent]
        recent_messages = messages[-self.config.keep_recent:]

        # Generate summary of old messages
        summary = await self._generate_summary(old_messages)

        # Create summary message
        summary_message = {
            "role": "user",
            "content": f"[COMPRESSED CONTEXT]\n{summary}\n[END COMPRESSED CONTEXT]",
        }

        return [summary_message] + recent_messages

    async def _generate_summary(self, messages: List[Dict]) -> str:
        """Generate summary of messages."""
        summary_parts = []

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if isinstance(content, str):
                preview = content[:100]
                if len(content) > 100:
                    preview += "..."
                summary_parts.append(f"[{role}] {preview}")
            elif isinstance(content, list):
                # Handle content blocks
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")[:100]
                        if len(block.get("text", "")) > 100:
                            text += "..."
                        summary_parts.append(f"[{role}] {text}")

        return "\n".join(summary_parts[:20])  # Limit summary size

    async def _micro_compress(self, messages: List[Dict]) -> List[Dict]:
        """Keep only recent messages."""
        return messages[-self.config.keep_recent:]

    async def _group_compress(self, messages: List[Dict]) -> List[Dict]:
        """Group related messages."""
        groups: Dict[str, List[Dict]] = {}

        for msg in messages:
            role = msg.get("role", "user")
            if role not in groups:
                groups[role] = []
            groups[role].append(msg)

        compressed = []

        for role, group_messages in groups.items():
            if len(group_messages) > 5:
                # Summarize group
                summary = await self._generate_summary(group_messages[:-5])
                compressed.append({
                    "role": "user",
                    "content": f"[{role} GROUP SUMMARY]\n{summary}",
                })
                compressed.extend(group_messages[-5:])
            else:
                compressed.extend(group_messages)

        return compressed

    async def _time_compress(self, messages: List[Dict]) -> List[Dict]:
        """Compress by time intervals."""
        # Would use timestamps if available
        # For now, use simple segmentation
        chunk_size = 10

        if len(messages) <= chunk_size:
            return messages

        compressed = []

        # Keep first message (often system/user context)
        compressed.append(messages[0])

        # Compress middle chunks
        middle_messages = messages[1:-self.config.keep_recent]

        for i in range(0, len(middle_messages), chunk_size):
            chunk = middle_messages[i:i + chunk_size]
            summary = await self._generate_summary(chunk)
            compressed.append({
                "role": "user",
                "content": f"[TIME CHUNK {i}]\n{summary}",
            })

        # Keep recent messages
        compressed.extend(messages[-self.config.keep_recent:])

        return compressed

    async def get_compression_stats(
        self,
        original: List[Dict],
        compressed: List[Dict]
    ) -> CompressionResult:
        """Get compression statistics."""
        original_tokens = await self._estimate_tokens(original)
        compressed_tokens = await self._estimate_tokens(compressed)

        return CompressionResult(
            original_messages=len(original),
            original_tokens=original_tokens,
            compressed_messages=len(compressed),
            compressed_tokens=compressed_tokens,
            strategy_used=self.config.strategy,
            summary=f"Saved {original_tokens - compressed_tokens} tokens",
        )


async def compress_messages(
    messages: List[Dict],
    strategy: CompressionStrategy = CompressionStrategy.SUMMARY,
    target_tokens: int = 50000,
) -> List[Dict]:
    """Compress messages with specified strategy."""
    config = CompressionConfig(
        strategy=strategy,
        target_tokens=target_tokens,
    )
    compressor = MessageCompressor(config)
    return await compressor.compress(messages)


async def should_compress(messages: List[Dict], max_tokens: int = 100000) -> bool:
    """Check if compression is needed."""
    usage = await estimate_messages_tokens(messages)
    return usage.input_tokens > max_tokens * 0.8


async def estimate_compression_savings(
    messages: List[Dict],
    strategy: CompressionStrategy = CompressionStrategy.SUMMARY
) -> Dict[str, int]:
    """Estimate savings from compression."""
    config = CompressionConfig(strategy=strategy)
    compressor = MessageCompressor(config)

    original_tokens = await compressor._estimate_tokens(messages)

    # Quick estimate based on strategy
    if strategy == CompressionStrategy.SUMMARY:
        # Summary typically saves ~70%
        estimated_compressed = int(original_tokens * 0.3)
    elif strategy == CompressionStrategy.MICRO:
        # Micro keeps only recent
        recent_tokens = await compressor._estimate_tokens(
            messages[-config.keep_recent:]
        )
        estimated_compressed = recent_tokens
    else:
        # Other strategies save ~50%
        estimated_compressed = int(original_tokens * 0.5)

    return {
        "original_tokens": original_tokens,
        "estimated_compressed_tokens": estimated_compressed,
        "estimated_savings": original_tokens - estimated_compressed,
    }


__all__ = [
    "CompressionStrategy",
    "CompressionConfig",
    "CompressionResult",
    "MessageCompressor",
    "compress_messages",
    "should_compress",
    "estimate_compression_savings",
]