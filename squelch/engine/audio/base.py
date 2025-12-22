"""
Abstract base class for audio capture implementations.
"""

import threading
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

    Subclasses should:
    1. Call _init_buffers() in their __init__
    2. Call _add_audio(audio_data) when audio is captured
    3. Call _start_process_loop() after starting their audio stream
    4. Call _stop_process_loop() in their stop() method
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

        # Buffer state (initialized by _init_buffers)
        self._fast_buffer: list[np.ndarray] = []
        self._fast_buffer_duration: float = 0.0
        self._fast_position: float = 0.0
        self._slow_buffer: list[np.ndarray] = []
        self._slow_buffer_duration: float = 0.0
        self._slow_position: float = 0.0
        self._buffer_lock = threading.Lock()

        # Process loop state
        self._process_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Counters
        self.fast_chunks_emitted: int = 0
        self.slow_chunks_emitted: int = 0

    def _init_buffers(self) -> None:
        """Reset all buffers. Call this at the start of start()."""
        with self._buffer_lock:
            self._fast_buffer = []
            self._fast_buffer_duration = 0.0
            self._fast_position = 0.0
            self._slow_buffer = []
            self._slow_buffer_duration = 0.0
            self._slow_position = 0.0

        self.fast_chunks_emitted = 0
        self.slow_chunks_emitted = 0
        self._stop_event.clear()

    def _add_audio(self, audio: np.ndarray) -> None:
        """
        Add audio data to both buffers. Call this from audio callback.

        Args:
            audio: Audio data as float32 numpy array (already resampled to config.sample_rate)
        """
        with self._buffer_lock:
            self._fast_buffer.append(audio.copy())
            self._fast_buffer_duration += len(audio) / self.config.sample_rate
            self._slow_buffer.append(audio.copy())
            self._slow_buffer_duration += len(audio) / self.config.sample_rate

    def _start_process_loop(self) -> None:
        """Start the background thread that emits chunks. Call after starting audio stream."""
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()

    def _stop_process_loop(self) -> None:
        """Stop the process loop thread. Call in stop()."""
        self._stop_event.set()
        if self._process_thread is not None:
            self._process_thread.join(timeout=1.0)
            self._process_thread = None

    def _process_loop(self) -> None:
        """Background thread that checks for complete chunks and emits them."""
        while not self._stop_event.is_set():
            with self._buffer_lock:
                # Check fast buffer
                if self._fast_buffer_duration >= self.config.fast_chunk_duration:
                    chunk = np.concatenate(self._fast_buffer)
                    chunk_start = self._fast_position
                    chunk_end = chunk_start + self._fast_buffer_duration

                    self._fast_buffer = []
                    self._fast_position = chunk_end
                    self._fast_buffer_duration = 0.0
                    self.fast_chunks_emitted += 1

                    if self.on_chunk_ready:
                        self.on_chunk_ready(chunk, chunk_start, chunk_end, ChunkType.FAST)

                # Check slow buffer
                if self._slow_buffer_duration >= self.config.slow_chunk_duration:
                    chunk = np.concatenate(self._slow_buffer)
                    chunk_start = self._slow_position
                    chunk_end = chunk_start + self._slow_buffer_duration

                    self._slow_buffer = []
                    self._slow_position = chunk_end
                    self._slow_buffer_duration = 0.0
                    self.slow_chunks_emitted += 1

                    if self.on_chunk_ready:
                        self.on_chunk_ready(chunk, chunk_start, chunk_end, ChunkType.SLOW)

            # Small sleep to prevent busy-waiting
            self._stop_event.wait(0.1)

        # Flush remaining buffers on stop
        self._flush_buffers()

    def _flush_buffers(self) -> None:
        """Flush any remaining audio in buffers."""
        with self._buffer_lock:
            if self._fast_buffer and self.on_chunk_ready:
                chunk = np.concatenate(self._fast_buffer)
                chunk_start = self._fast_position
                chunk_end = chunk_start + self._fast_buffer_duration
                self.on_chunk_ready(chunk, chunk_start, chunk_end, ChunkType.FAST)
                self._fast_buffer = []

            if self._slow_buffer and self.on_chunk_ready:
                chunk = np.concatenate(self._slow_buffer)
                chunk_start = self._slow_position
                chunk_end = chunk_start + self._slow_buffer_duration
                self.on_chunk_ready(chunk, chunk_start, chunk_end, ChunkType.SLOW)
                self._slow_buffer = []

    @staticmethod
    def resample(audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        """
        Simple resampling using linear interpolation.

        Args:
            audio: Input audio array
            orig_rate: Original sample rate
            target_rate: Target sample rate

        Returns:
            Resampled audio array
        """
        if orig_rate == target_rate:
            return audio

        duration = len(audio) / orig_rate
        target_length = int(duration * target_rate)

        indices = np.linspace(0, len(audio) - 1, target_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

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

    def terminate(self) -> None:
        """Clean up resources. Default implementation just calls stop()."""
        self.stop()