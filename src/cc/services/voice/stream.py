"""Voice Stream - Async streaming voice recognition."""

from __future__ import annotations
import asyncio
import audioop
import wave
import io
from typing import AsyncIterator, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum


class AudioFormat(Enum):
    """Audio format types."""
    PCM_16 = "pcm_16"
    WAV = "wav"
    FLAC = "flac"
    MP3 = "mp3"


@dataclass
class AudioChunk:
    """Audio chunk."""
    data: bytes
    timestamp: float
    duration_ms: float
    format: AudioFormat = AudioFormat.PCM_16
    sample_rate: int = 16000


@dataclass
class VoiceStreamConfig:
    """Voice stream configuration."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    buffer_size: int = 10
    silence_threshold: int = 500
    silence_duration_ms: int = 1000
    vad_enabled: bool = True


@dataclass
class StreamTranscriptionResult:
    """Stream transcription result."""
    text: str
    is_final: bool = False
    confidence: float = 0.0
    words: List[Dict] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0


class VoiceStreamProcessor:
    """Process streaming audio for transcription."""

    def __init__(self, config: Optional[VoiceStreamConfig] = None):
        self.config = config or VoiceStreamConfig()
        self._buffer: List[AudioChunk] = []
        self._silence_start: Optional[float] = None
        self._is_speaking: bool = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._result_queue: asyncio.Queue = asyncio.Queue()
        self._running: bool = False

    async def start(self) -> None:
        """Start stream processing."""
        self._running = True
        asyncio.create_task(self._process_loop())

    async def stop(self) -> None:
        """Stop stream processing."""
        self._running = False
        # Process remaining buffer
        if self._buffer:
            await self._process_buffer()

    async def add_chunk(self, chunk: AudioChunk) -> None:
        """Add audio chunk to queue."""
        await self._audio_queue.put(chunk)

    async def get_results(self) -> AsyncIterator[StreamTranscriptionResult]:
        """Get transcription results."""
        while self._running:
            try:
                result = await asyncio.wait_for(
                    self._result_queue.get(),
                    timeout=1.0,
                )
                yield result
            except asyncio.TimeoutError:
                continue

    async def _process_loop(self) -> None:
        """Process audio chunks."""
        while self._running:
            try:
                chunk = await asyncio.wait_for(
                    self._audio_queue.get(),
                    timeout=0.5,
                )
                await self._process_chunk(chunk)
            except asyncio.TimeoutError:
                # Check for silence timeout
                if self._is_speaking and self._silence_start:
                    silence_duration = asyncio.get_event_loop().time() - self._silence_start
                    if silence_duration * 1000 > self.config.silence_duration_ms:
                        await self._process_buffer()
                        self._is_speaking = False
                        self._silence_start = None

    async def _process_chunk(self, chunk: AudioChunk) -> None:
        """Process single audio chunk."""
        # Voice Activity Detection (simple energy-based)
        if self.config.vad_enabled:
            energy = self._calculate_energy(chunk.data)

            if energy > self.config.silence_threshold:
                self._is_speaking = True
                self._silence_start = None
            else:
                if self._is_speaking and self._silence_start is None:
                    self._silence_start = asyncio.get_event_loop().time()

        self._buffer.append(chunk)

        # Check buffer size
        if len(self._buffer) >= self.config.buffer_size:
            await self._process_buffer()

    def _calculate_energy(self, data: bytes) -> int:
        """Calculate audio energy."""
        try:
            return audioop.rms(data, 2)  # 16-bit samples
        except Exception:
            return 0

    async def _process_buffer(self) -> None:
        """Process accumulated buffer."""
        if not self._buffer:
            return

        # Combine chunks
        combined_data = b"".join(c.data for c in self._buffer)

        # Convert to WAV format
        wav_data = self._to_wav(combined_data)

        # Send for transcription (placeholder)
        result = await self._transcribe(wav_data)

        if result:
            await self._result_queue.put(result)

        # Clear buffer
        self._buffer.clear()

    def _to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM to WAV format."""
        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(self.config.channels)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(self.config.sample_rate)
            wav.writeframes(pcm_data)

        return buffer.getvalue()

    async def _transcribe(self, audio_data: bytes) -> Optional[StreamTranscriptionResult]:
        """Transcribe audio data."""
        # Placeholder - actual implementation would call STT service
        return StreamTranscriptionResult(
            text="[transcription placeholder]",
            is_final=True,
            confidence=0.8,
        )


class VoiceActivityDetector:
    """Voice Activity Detection."""

    def __init__(self, threshold: int = 500, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._history: List[int] = []
        self._history_size: int = 10

    def is_speech(self, audio_chunk: bytes) -> bool:
        """Check if chunk contains speech."""
        try:
            energy = audioop.rms(audio_chunk, 2)
            self._history.append(energy)

            if len(self._history) > self._history_size:
                self._history.pop(0)

            # Use adaptive threshold based on history
            avg_energy = sum(self._history) / len(self._history)
            adaptive_threshold = max(self.threshold, avg_energy * 1.5)

            return energy > adaptive_threshold
        except Exception:
            return False

    def reset(self) -> None:
        """Reset detector state."""
        self._history.clear()


class AudioBuffer:
    """Buffer for audio chunks."""

    def __init__(self, max_duration_ms: int = 30000):
        self.max_duration_ms = max_duration_ms
        self._chunks: List[AudioChunk] = []
        self._total_duration: float = 0.0

    def add(self, chunk: AudioChunk) -> Optional[List[AudioChunk]]:
        """Add chunk, return evicted if overflow."""
        evicted = None

        self._total_duration += chunk.duration_ms

        while self._total_duration > self.max_duration_ms and self._chunks:
            evicted_chunk = self._chunks.pop(0)
            self._total_duration -= evicted_chunk.duration_ms
            if evicted is None:
                evicted = []
            evicted.append(evicted_chunk)

        self._chunks.append(chunk)
        return evicted

    def get_all(self) -> List[AudioChunk]:
        """Get all chunks."""
        return self._chunks.copy()

    def clear(self) -> None:
        """Clear buffer."""
        self._chunks.clear()
        self._total_duration = 0.0

    def get_duration_ms(self) -> float:
        """Get total duration."""
        return self._total_duration


__all__ = [
    "AudioFormat",
    "AudioChunk",
    "VoiceStreamConfig",
    "StreamTranscriptionResult",
    "VoiceStreamProcessor",
    "VoiceActivityDetector",
    "AudioBuffer",
]