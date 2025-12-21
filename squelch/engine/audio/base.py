"""
Abstract base class for audio capture implementations.
"""

from abc import ABC, abstractmethod
from typing import Callable
import numpy as np

from ...config import AudioConfig
from ..types import ChunkType


# Type alias for the chunk callback
ChunkCallback = Callable[[np.ndarray, float, float, ChunkType], None]


class AudioCaptureBase(ABC):
    """
    Abstract base class for platform-specific audio capture.

    Implementations must capture audio from the system's audio output
    (loopback capture) and call the on_chunk_ready callback when
    audio chunks are ready for transcription.
    """

    def __init__(self, config: AudioConfig, on_chunk_ready: ChunkCallback | None = None):
        """
        Initialize audio capture.

        Args:
            config: Audio configuration (sample rate, chunk durations, etc.)
            on_chunk_ready: Callback called when audio chunk is ready.
                           Signature: (audio_data, start_time, end_time, chunk_type)
        """
        self.config = config
        self.on_chunk_ready = on_chunk_ready

    @abstractmethod
    def start(self) -> None:
        """Start audio capture."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop audio capture."""
        pass

    @staticmethod
    @abstractmethod
    def list_devices() -> list[dict]:
        """
        List available audio devices.

        Returns:
            List of dicts with device info. Each dict should have:
            - index: int
            - name: str
            - is_loopback: bool
        """
        pass

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """
        Check if this audio capture implementation is available on the current platform.

        Returns:
            True if available, False otherwise.
        """
        pass
