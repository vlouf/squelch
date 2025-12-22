"""
Squelch configuration.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AudioConfig:
    """Audio capture settings."""

    sample_rate: int = 16000  # Whisper expects 16kHz
    channels: int = 1  # Mono is fine for speech
    device_name: str | None = None  # None = use default, or specify e.g. "CABLE Output"

    # Dual-pass chunking for better transcription quality
    # Fast pass: low latency, shown immediately in UI
    # Slow pass: higher quality, used for final export
    fast_chunk_duration: float = 6.0  # Seconds per fast transcription chunk
    slow_chunk_duration: float = 60.0  # Seconds per slow transcription chunk


@dataclass
class WhisperConfig:
    """Whisper transcription settings."""

    # Separate models for fast and slow passes
    fast_model: str = "base"  # Fast pass: speed matters (tiny, base)
    slow_model: str = "small"  # Slow pass: quality matters (small, medium, large-v2)

    device: str = "auto"  # auto, cpu, cuda
    compute_type: str = "auto"  # auto, int8, float16, float32
    language: str | None = "en"  # None = auto-detect


@dataclass
class OutputConfig:
    """Output settings."""

    output_dir: Path = field(default_factory=lambda: Path.home() / "Documents" / "Squelch")


@dataclass
class LLMConfig:
    """LLM configuration."""

    endpoint: str = "http://localhost:11434/v1/chat/completions"
    model: str | None = None  # None = auto-detect first available
    max_tokens: int = 500
    temperature: float = 0.7
    context_segments: int = 20  # How many recent segments to include as context


@dataclass
class Config:
    """Main configuration container."""

    audio: AudioConfig = field(default_factory=AudioConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


# Default config instance
config = Config()
