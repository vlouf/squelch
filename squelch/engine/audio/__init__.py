"""
Platform-specific audio capture.

Auto-selects the appropriate implementation based on the current platform.
"""

import sys

from .base import AudioCaptureBase, ChunkCallback

# Platform detection and implementation selection
_implementation = None
_implementation_name = None

if sys.platform == "win32":
    try:
        from .windows import WindowsAudioCapture
        _implementation = WindowsAudioCapture
        _implementation_name = "Windows (WASAPI)"
    except ImportError as e:
        raise ImportError(
            f"Windows audio capture requires PyAudioWPatch. "
            f"Install it with: pip install PyAudioWPatch\n"
            f"Original error: {e}"
        )

elif sys.platform == "linux":
    try:
        from .linux import LinuxAudioCapture
        _implementation = LinuxAudioCapture
        _implementation_name = "Linux (PipeWire)"
    except ImportError as e:
        raise ImportError(
            f"Linux audio capture requires sounddevice and PipeWire. "
            f"Install with: pip install sounddevice && sudo apt install pipewire\n"
            f"Original error: {e}"
        )

elif sys.platform == "darwin":
    # macOS implementation placeholder
    raise NotImplementedError(
        "macOS audio capture is not yet implemented. "
        "Contributions welcome! See engine/audio/base.py for the interface."
    )

else:
    raise NotImplementedError(
        f"Unsupported platform: {sys.platform}. "
        f"Supported platforms: win32, linux, darwin"
    )


# Export the selected implementation as AudioCapture
AudioCapture = _implementation

__all__ = ["AudioCapture", "AudioCaptureBase", "ChunkCallback"]