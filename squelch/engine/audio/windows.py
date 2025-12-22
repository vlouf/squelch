"""
Audio capture using PyAudioWPatch for WASAPI loopback on Windows.
"""

import sys
import numpy as np

from ...config import AudioConfig
from ..types import ChunkType
from .base import AudioCaptureBase, ChunkCallback


class WindowsAudioCapture(AudioCaptureBase):
    """
    Captures audio from a WASAPI loopback device on Windows.

    Uses PyAudioWPatch for WASAPI loopback support.
    """

    def __init__(self, config: AudioConfig, on_chunk_ready: ChunkCallback | None = None):
        super().__init__(config, on_chunk_ready)

        import pyaudiowpatch as pyaudio
        self._pyaudio_module = pyaudio

        self._pyaudio = pyaudio.PyAudio()
        self._stream = None

        # Find the device
        self._device_info = self._find_device()

    def _find_device(self) -> dict:
        """Find the appropriate WASAPI loopback device."""
        pyaudio = self._pyaudio_module

        # If a specific device name is requested, search for it
        if self.config.device_name:
            for i in range(self._pyaudio.get_device_count()):
                info = self._pyaudio.get_device_info_by_index(i)
                if self.config.device_name.lower() in info["name"].lower():
                    if info.get("isLoopbackDevice", False):
                        return info

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
                if info["name"].startswith(default_device["name"].split(" (")[0]):
                    return info

        raise RuntimeError(
            "Could not find a WASAPI loopback device. "
            "Make sure you have an audio output device active."
        )

    @staticmethod
    def list_devices() -> list[dict]:
        """List all available audio devices, highlighting loopback devices."""
        import pyaudiowpatch as pyaudio
        p = pyaudio.PyAudio()
        devices = []

        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            devices.append({
                "index": i,
                "name": info["name"],
                "is_loopback": info.get("isLoopbackDevice", False),
                "max_input_channels": info["maxInputChannels"],
                "max_output_channels": info["maxOutputChannels"],
                "default_sample_rate": info["defaultSampleRate"],
            })

        p.terminate()
        return devices

    @staticmethod
    def is_available() -> bool:
        """Check if WASAPI loopback is available (Windows only)."""
        if sys.platform != "win32":
            return False
        try:
            import pyaudiowpatch
            return True
        except ImportError:
            return False

    def start(self) -> None:
        """Start capturing audio."""
        pyaudio = self._pyaudio_module

        if self._process_thread is not None and self._process_thread.is_alive():
            raise RuntimeError("Already capturing")

        # Reset buffers
        self._init_buffers()

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
        self._start_process_loop()

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

        self._stop_process_loop()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Called by PyAudio when audio data is available."""
        pyaudio = self._pyaudio_module

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
            audio_data = self.resample(audio_data, device_rate, self.config.sample_rate)

        # Add to buffers (handled by base class)
        self._add_audio(audio_data)

        return (None, pyaudio.paContinue)

    def terminate(self) -> None:
        """Clean up PyAudio resources."""
        self.stop()
        try:
            self._pyaudio.terminate()
        except Exception:
            pass