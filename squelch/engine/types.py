"""
Shared types for the Squelch engine.
"""

from enum import Enum


class ChunkType(Enum):
    """Type of audio chunk for dual-pass transcription."""

    FAST = "fast"
    SLOW = "slow"


class TranscriptQuality(Enum):
    """Quality level of a transcript segment."""

    FAST = "fast"  # Quick transcription, may have boundary artifacts
    REFINED = "refined"  # Slow pass, higher quality
