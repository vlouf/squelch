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
    chunk_duration: float = 6.0  # Seconds of audio per transcription chunk
    device_name: str | None = None  # None = use default, or specify e.g. "CABLE Output"


@dataclass
class WhisperConfig:
    """Whisper transcription settings."""
    model_size: str = "base"  # tiny, base, small, medium, large-v2, large-v3
    device: str = "auto"  # auto, cpu, cuda
    compute_type: str = "auto"  # auto, int8, float16, float32
    language: str | None = "en"  # None = auto-detect


@dataclass
class OutputConfig:
    """Output settings."""
    output_dir: Path = field(default_factory=lambda: Path("./meetings"))


@dataclass
class Config:
    """Main configuration container."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


# Default config instance
config = Config()
