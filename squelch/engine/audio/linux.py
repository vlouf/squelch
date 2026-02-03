"""
Audio capture on Linux using PulseAudio/PipeWire monitor sources.

On Linux, capturing system audio requires using a "monitor" source.
We use parec (PulseAudio recording) to capture from monitor sources,
as sounddevice/PortAudio often doesn't see PipeWire sources properly.
"""

import os
import sys
import subprocess
import threading
import shutil
from typing import Callable

import numpy as np

from ...config import AudioConfig
from .base import AudioCaptureBase, ChunkCallback


def _get_pulseaudio_sources() -> list[dict]:
    """Get all sources from PulseAudio/PipeWire via pactl."""
    sources = []

    try:
        result = subprocess.run(
            ["pactl", "list", "sources", "short"],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        if result.returncode != 0:
            return sources

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                index = parts[0]
                name = parts[1]
                is_monitor = ".monitor" in name.lower()
                sources.append({
                    "index": index,
                    "name": name,
                    "is_monitor": is_monitor,
                })
    except Exception:
        pass

    return sources


def _get_default_sink_monitor() -> str | None:
    """Get the monitor source for the default sink."""
    try:
        # Get default sink name
        result = subprocess.run(
            ["pactl", "get-default-sink"],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        if result.returncode != 0:
            return None

        default_sink = result.stdout.strip()
        if default_sink:
            return f"{default_sink}.monitor"
    except Exception:
        pass

    return None


class LinuxAudioCapture(AudioCaptureBase):
    """
    Captures audio on Linux using parec (PulseAudio/PipeWire).

    Uses parec to capture from monitor sources, which reliably
    captures system audio output.
    """

    def __init__(self, config: AudioConfig, on_chunk_ready: ChunkCallback | None = None):
        super().__init__(config, on_chunk_ready)

        # Check for parec
        if not shutil.which("parec"):
            raise RuntimeError(
                "parec not found. Install PulseAudio tools: "
                "sudo apt install pulseaudio-utils"
            )

        self._parec_proc: subprocess.Popen | None = None
        self._reader_thread: threading.Thread | None = None
        self._source_name: str | None = None

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio sources, prioritizing monitors."""
        sources = _get_pulseaudio_sources()

        devices = []
        for src in sources:
            devices.append({
                "index": src["index"],
                "name": src["name"],
                "is_loopback": src["is_monitor"],
                "max_input_channels": 2,
                "default_sample_rate": 48000,
            })

        return devices

    @staticmethod
    def is_available() -> bool:
        """Check if Linux audio capture is available."""
        if sys.platform != "linux":
            return False
        return shutil.which("parec") is not None

    def _find_monitor_source(self) -> str:
        """Find the best monitor source for capturing."""
        sources = _get_pulseaudio_sources()

        # If a specific device is configured, use it
        if self.config.device_name:
            for src in sources:
                if self.config.device_name.lower() in src["name"].lower():
                    return src["name"]

        # Try to get the default sink's monitor
        default_monitor = _get_default_sink_monitor()
        if default_monitor:
            for src in sources:
                if src["name"] == default_monitor:
                    return src["name"]

        # Fall back to any monitor source
        for src in sources:
            if src["is_monitor"]:
                return src["name"]

        raise RuntimeError(
            "No monitor source found. Make sure PulseAudio/PipeWire is running. "
            "Check available sources with: pactl list sources short"
        )

    def _read_audio_loop(self) -> None:
        """Read audio data from parec process."""
        if self._parec_proc is None:
            return

        # parec outputs raw audio - we read in chunks
        # At 48kHz, 16-bit stereo: 48000 * 2 * 2 = 192000 bytes/sec
        # Read 100ms at a time: 19200 bytes
        chunk_bytes = 19200

        try:
            while not self._stop_event.is_set():
                data = self._parec_proc.stdout.read(chunk_bytes)
                if not data:
                    break

                # Convert bytes to numpy array (signed 16-bit little-endian stereo)
                audio_int16 = np.frombuffer(data, dtype=np.int16)

                # Reshape to stereo and convert to mono float32
                if len(audio_int16) >= 2:
                    audio_stereo = audio_int16.reshape(-1, 2)
                    audio_mono = audio_stereo.mean(axis=1)
                else:
                    audio_mono = audio_int16.astype(np.float32)

                # Normalize to [-1, 1]
                audio = (audio_mono / 32768.0).astype(np.float32)

                # Resample from 48kHz to 16kHz
                if self.config.sample_rate != 48000:
                    audio = self.resample(audio, 48000, self.config.sample_rate)

                # Add to buffers
                self._add_audio(audio)

        except Exception as e:
            if not self._stop_event.is_set():
                print(f"[AudioCapture:Linux] Read error: {e}")

    def start(self) -> None:
        """Start capturing audio."""
        if self._parec_proc is not None:
            raise RuntimeError("Already capturing")

        # Reset buffers
        self._init_buffers()

        # Find a monitor source
        self._source_name = self._find_monitor_source()
        print(f"[AudioCapture:Linux] Using source: {self._source_name}")

        # Start parec process
        # Format: signed 16-bit little-endian, stereo, 48kHz
        cmd = [
            "parec",
            "--device", self._source_name,
            "--format", "s16le",
            "--channels", "2",
            "--rate", "48000",
            "--raw",
        ]

        self._parec_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        # Start reader thread
        self._reader_thread = threading.Thread(target=self._read_audio_loop, daemon=True)
        self._reader_thread.start()

        # Start the chunk processing loop
        self._start_process_loop()

    def stop(self) -> None:
        """Stop capturing audio."""
        self._stop_event.set()

        # Stop parec process
        if self._parec_proc is not None:
            try:
                self._parec_proc.terminate()
                self._parec_proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self._parec_proc.kill()
                self._parec_proc.wait()
            except Exception:
                pass
            self._parec_proc = None

        # Wait for reader thread
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=1.0)
            self._reader_thread = None

        self._stop_process_loop()