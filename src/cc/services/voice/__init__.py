"""Voice Service - Async voice recognition and synthesis.

Async voice services for STT/TTS.
"""

from __future__ import annotations
from .stt import (
    VoiceService,
    VoiceConfig,
    VoiceStreamProcessor,
    TranscriptionResult,
    SpeechConfig,
)
from .stream import (
    AudioFormat,
    AudioChunk,
    VoiceStreamConfig,
    StreamTranscriptionResult,
    VoiceActivityDetector,
    AudioBuffer,
)
from .keywords import (
    KeywordType,
    KeywordMatch,
    ExtractionResult,
    KeywordExtractor,
    VoiceCommandParser,
)

__all__ = [
    # STT
    "VoiceService",
    "VoiceConfig",
    "VoiceStreamProcessor",
    "TranscriptionResult",
    "SpeechConfig",
    # Stream
    "AudioFormat",
    "AudioChunk",
    "VoiceStreamConfig",
    "StreamTranscriptionResult",
    "VoiceActivityDetector",
    "AudioBuffer",
    # Keywords
    "KeywordType",
    "KeywordMatch",
    "ExtractionResult",
    "KeywordExtractor",
    "VoiceCommandParser",
]