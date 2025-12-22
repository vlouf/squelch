"""
Audio capture using PipeWire/PulseAudio on Linux.

Uses pw-loopback to create a loopback node, then captures from it via sounddevice.
"""

import os
import sys
import time
import shutil
import subprocess

import numpy as np

from ...config import AudioConfig
from .base import AudioCaptureBase, ChunkCallback


class LinuxAudioCapture(AudioCaptureBase):
    """
    Captures audio from PipeWire/PulseAudio on Linux.

    Creates a pw-loopback node to capture system audio output,
    then records from it using sounddevice.
    """

    def __init__(self, config: AudioConfig, on_chunk_ready: ChunkCallback | None = None):
        super().__init__(config, on_chunk_ready)

        if not shutil.which("pw-loopback"):
            raise RuntimeError(
                "pw-loopback not found. Install PipeWire: "
                "sudo apt install pipewire pipewire-pulse"
            )

        import sounddevice as sd
        self._sd = sd

        self._pw_proc: subprocess.Popen | None = None
        self._stream = None
        self._device_rate: int = 0

        # Unique node name to avoid conflicts with other instances
        self._node_name = f"squelch_loopback_{os.getpid()}"

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio devices."""
        import sounddevice as sd

        devices = []
        for i, d in enumerate(sd.query_devices()):
            name = d["name"]
            # PulseAudio monitor sources end with .monitor
            # PipeWire loopback nodes contain "loopback" in name
            is_loopback = (
                name.endswith(".monitor") or
                "loopback" in name.lower() or
                "monitor" in name.lower()
            )
            devices.append({
                "index": i,
                "name": name,
                "is_loopback": is_loopback,
                "max_input_channels": d.get("max_input_channels", 0),
                "default_sample_rate": d.get("default_samplerate", 0),
            })
        return devices

    @staticmethod
    def is_available() -> bool:
        """Check if PipeWire loopback is available."""
        return sys.platform == "linux" and shutil.which("pw-loopback") is not None

    def _start_pw_loopback(self) -> None:
        """Start pw-loopback subprocess."""
        cmd = [
            "pw-loopback",
            "--capture-props", f"node.name={self._node_name}",
            "--capture-props", f"node.description={self._node_name}",
        ]
        self._pw_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Check if it started successfully
        time.sleep(0.1)
        if self._pw_proc.poll() is not None:
            raise RuntimeError(
                f"pw-loopback failed to start (exit code {self._pw_proc.returncode}). "
                "Check that PipeWire is running."
            )

    def _find_loopback_device(self) -> tuple[int, dict]:
        """Find the pw-loopback device we created."""
        deadline = time.time() + 3.0

        while time.time() < deadline:
            for i, d in enumerate(self._sd.query_devices()):
                # Look for our specific node name
                if self._node_name.lower() in d["name"].lower():
                    return i, d
            time.sleep(0.1)

        # Fallback: look for any loopback device
        for i, d in enumerate(self._sd.query_devices()):
            if "loopback" in d["name"].lower():
                return i, d

        raise RuntimeError(
            f"Could not find loopback device '{self._node_name}'. "
            "Check that PipeWire session is running."
        )

    def start(self) -> None:
        """Start capturing audio."""
        if self._process_thread is not None and self._process_thread.is_alive():
            raise RuntimeError("Already capturing")

        # Reset buffers
        self._init_buffers()

        # Start pw-loopback and find the device
        self._start_pw_loopback()
        dev_index, dev_info = self._find_loopback_device()

        self._device_rate = int(dev_info["default_samplerate"]) or 48000
        frames_per_buffer = int(self._device_rate * 0.1)  # 100ms

        # Create the audio callback
        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"[AudioCapture:Linux] {status}")

            # Convert to mono float32
            if indata.ndim > 1:
                audio = indata.mean(axis=1).astype(np.float32)
            else:
                audio = indata.flatten().astype(np.float32)

            # Resample if needed
            if self._device_rate != self.config.sample_rate:
                audio = self.resample(audio, self._device_rate, self.config.sample_rate)

            # Add to buffers (handled by base class)
            self._add_audio(audio)

        # Open the stream
        self._stream = self._sd.InputStream(
            device=dev_index,
            channels=1,
            samplerate=self._device_rate,
            blocksize=frames_per_buffer,
            dtype='float32',
            callback=audio_callback,
        )
        self._stream.start()
        self._start_process_loop()

    def stop(self) -> None:
        """Stop capturing audio."""
        self._stop_event.set()

        # Stop the audio stream
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        # Kill the pw-loopback process
        if self._pw_proc is not None:
            try:
                self._pw_proc.terminate()
                self._pw_proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self._pw_proc.kill()
                self._pw_proc.wait()
            except Exception:
                pass
            self._pw_proc = None

        self._stop_process_loop()