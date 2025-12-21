"""
Audio capture using PyAudioWPatch for WASAPI loopback on Windows.
"""

import threading
import numpy as np
import pyaudiowpatch as pyaudio
from typing import Callable
from enum import Enum

from ..config import AudioConfig


class ChunkType(Enum):
    """Type of audio chunk for dual-pass transcription."""

    FAST = "fast"
    SLOW = "slow"


class AudioCapture:
    """
    Captures audio from a WASAPI loopback device.

    Runs in a dedicated thread to ensure isochronous capture
    without dropping samples.

    Supports dual-pass chunking:
    - Fast chunks: emitted frequently for low-latency display
    - Slow chunks: emitted less frequently for higher quality transcription
    """

    def __init__(
        self,
        config: AudioConfig,
        on_chunk_ready: Callable[[np.ndarray, float, float, ChunkType], None] | None = None,
    ):
        """
        Args:
            config: Audio configuration
            on_chunk_ready: Callback when a chunk is ready (audio_data, start_time, end_time, chunk_type)
        """
        self.config = config
        self.on_chunk_ready = on_chunk_ready

        self._pyaudio = pyaudio.PyAudio()
        self._stream = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Fast buffer - drains frequently for low latency
        self._fast_buffer: list[np.ndarray] = []
        self._fast_buffer_duration: float = 0.0
        self._fast_position: float = 0.0

        # Slow buffer - accumulates for higher quality transcription
        self._slow_buffer: list[np.ndarray] = []
        self._slow_buffer_duration: float = 0.0
        self._slow_position: float = 0.0

        # Lock for thread-safe buffer access
        self._buffer_lock = threading.Lock()

        # Counters
        self.fast_chunks_emitted: int = 0
        self.slow_chunks_emitted: int = 0

        # Find the device
        self._device_info = self._find_device()

    def _find_device(self) -> dict:
        """Find the appropriate WASAPI loopback device."""

        # If a specific device name is requested, search for it
        if self.config.device_name:
            for i in range(self._pyaudio.get_device_count()):
                info = self._pyaudio.get_device_info_by_index(i)
                if self.config.device_name.lower() in info["name"].lower():
                    if info.get("isLoopbackDevice", False):
                        return info

            # Didn't find a loopback version, try to find the regular device
            # and get its loopback counterpart
            raise ValueError(
                f"Could not find loopback device matching '{self.config.device_name}'. "
                f"Use list_devices() to see available devices."
            )

        # Default: find the default WASAPI loopback device
        try:
            wasapi_info = self._pyaudio.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            raise RuntimeError("WASAPI not available on this system")

        default_device_idx = wasapi_info["defaultOutputDevice"]
        default_device = self._pyaudio.get_device_info_by_index(default_device_idx)

        # Find the loopback device for the default output
        for i in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(i)
            if info.get("isLoopbackDevice", False):
                # Check if this is the loopback for our target device
                if info["name"].startswith(default_device["name"].split(" (")[0]):
                    return info

        raise RuntimeError(
            "Could not find a WASAPI loopback device. " "Make sure you have an audio output device active."
        )

    @classmethod
    def list_devices(cls) -> list[dict]:
        """List all available audio devices, highlighting loopback devices."""
        p = pyaudio.PyAudio()
        devices = []

        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            devices.append(
                {
                    "index": i,
                    "name": info["name"],
                    "is_loopback": info.get("isLoopbackDevice", False),
                    "max_input_channels": info["maxInputChannels"],
                    "max_output_channels": info["maxOutputChannels"],
                    "default_sample_rate": info["defaultSampleRate"],
                }
            )

        p.terminate()
        return devices

    def start(self) -> None:
        """Start capturing audio."""
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Already capturing")

        self._stop_event.clear()

        # Reset buffers
        with self._buffer_lock:
            self._fast_buffer = []
            self._fast_buffer_duration = 0.0
            self._fast_position = 0.0
            self._slow_buffer = []
            self._slow_buffer_duration = 0.0
            self._slow_position = 0.0

        self.fast_chunks_emitted = 0
        self.slow_chunks_emitted = 0

        # Calculate frames per buffer (smaller = lower latency, but more CPU)
        frames_per_buffer = int(self._device_info["defaultSampleRate"] * 0.1)  # 100ms

        self._stream = self._pyaudio.open(
            format=pyaudio.paFloat32,
            channels=int(self._device_info["maxInputChannels"]),
            rate=int(self._device_info["defaultSampleRate"]),
            input=True,
            input_device_index=self._device_info["index"],
            frames_per_buffer=frames_per_buffer,
            stream_callback=self._audio_callback,
        )

        self._stream.start_stream()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop capturing audio."""
        self._stop_event.set()

        if self._stream is not None:
            try:
                self._stream.stop_stream()
            except Exception:
                pass
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            # Thread is daemon, so it will die when main process exits anyway
            self._thread = None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Called by PyAudio when audio data is available."""
        if status:
            print(f"[AudioCapture] Status: {status}")

        # Convert to numpy array
        audio_data = np.frombuffer(in_data, dtype=np.float32)

        # If stereo, convert to mono by averaging channels
        device_channels = int(self._device_info["maxInputChannels"])
        if device_channels > 1:
            audio_data = audio_data.reshape(-1, device_channels).mean(axis=1)

        # Resample if needed (device rate -> 16kHz for Whisper)
        device_rate = int(self._device_info["defaultSampleRate"])
        if device_rate != self.config.sample_rate:
            audio_data = self._resample(audio_data, device_rate, self.config.sample_rate)

        # Add to both buffers
        with self._buffer_lock:
            self._fast_buffer.append(audio_data.copy())
            self._fast_buffer_duration += len(audio_data) / self.config.sample_rate

            self._slow_buffer.append(audio_data.copy())
            self._slow_buffer_duration += len(audio_data) / self.config.sample_rate

        return (None, pyaudio.paContinue)

    def _resample(self, audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        """Simple resampling using linear interpolation."""
        if orig_rate == target_rate:
            return audio

        duration = len(audio) / orig_rate
        target_length = int(duration * target_rate)

        indices = np.linspace(0, len(audio) - 1, target_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _process_loop(self) -> None:
        """Background thread that checks for complete chunks."""
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
        with self._buffer_lock:
            if self._fast_buffer and self.on_chunk_ready:
                chunk = np.concatenate(self._fast_buffer)
                chunk_start = self._fast_position
                chunk_end = chunk_start + self._fast_buffer_duration
                self.on_chunk_ready(chunk, chunk_start, chunk_end, ChunkType.FAST)

            # Also flush slow buffer as a final refined pass
            if self._slow_buffer and self.on_chunk_ready:
                chunk = np.concatenate(self._slow_buffer)
                chunk_start = self._slow_position
                chunk_end = chunk_start + self._slow_buffer_duration
                self.on_chunk_ready(chunk, chunk_start, chunk_end, ChunkType.SLOW)

    def terminate(self) -> None:
        """Clean up PyAudio resources."""
        self.stop()
        try:
            self._pyaudio.terminate()
        except Exception:
            pass
