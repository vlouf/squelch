"""
Whisper transcription worker using faster-whisper.

Runs in a separate process to avoid blocking the main asyncio loop
during CPU/GPU-intensive transcription.
"""

import multiprocessing as mp
from multiprocessing import Queue
from dataclasses import dataclass
from typing import Any
import numpy as np

from ..config import WhisperConfig
from .types import ChunkType


@dataclass
class TranscriptionRequest:
    """A request to transcribe audio."""
    audio: np.ndarray
    start_time: float
    end_time: float
    chunk_type: ChunkType = ChunkType.FAST


@dataclass
class TranscriptionResult:
    """Result from transcription."""
    text: str
    start_time: float
    end_time: float
    segments: list[dict]  # Detailed segment info from Whisper
    chunk_type: ChunkType = ChunkType.FAST


class TranscriberWorker:
    """
    Manages a worker process that runs faster-whisper.

    Audio chunks are sent via a queue, results come back via another queue.
    This keeps the heavy lifting off the main thread/process.
    """

    def __init__(self, model_size: str, config: WhisperConfig, name: str = "whisper"):
        """
        Args:
            model_size: Whisper model to load (tiny, base, small, medium, large-v2, large-v3)
            config: Whisper configuration (device, compute_type, language)
            name: Name for logging purposes
        """
        self.model_size = model_size
        self.config = config
        self.name = name
        self._input_queue: Queue = mp.Queue()
        self._output_queue: Queue = mp.Queue()
        self._process: mp.Process | None = None

    def start(self) -> None:
        """Start the worker process."""
        if self._process is not None and self._process.is_alive():
            raise RuntimeError("Worker already running")

        self._process = mp.Process(
            target=_worker_loop,
            args=(self.model_size, self.config, self._input_queue, self._output_queue, self.name),
            daemon=True,
        )
        self._process.start()

    def stop(self) -> None:
        """Stop the worker process."""
        if self._process is None:
            return

        # Check if process is even alive
        if not self._process.is_alive():
            self._process = None
            return

        # Send sentinel to stop the worker
        try:
            self._input_queue.put(None, timeout=1.0)
        except:
            pass

        self._process.join(timeout=2.0)

        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)

        if self._process.is_alive():
            self._process.kill()

        self._process = None

    def submit(self, audio: np.ndarray, start_time: float, end_time: float, chunk_type: ChunkType = ChunkType.FAST) -> None:
        """Submit audio for transcription."""
        request = TranscriptionRequest(
            audio=audio,
            start_time=start_time,
            end_time=end_time,
            chunk_type=chunk_type,
        )
        self._input_queue.put(request)

    def get_result(self, timeout: float | None = None) -> TranscriptionResult | None:
        """
        Get a transcription result if available.

        Args:
            timeout: How long to wait. None = don't block, 0 = block forever.

        Returns:
            TranscriptionResult or None if no result available.
        """
        try:
            if timeout is None:
                return self._output_queue.get_nowait()
            else:
                return self._output_queue.get(timeout=timeout)
        except:
            return None

    @property
    def has_results(self) -> bool:
        """Check if there are results waiting."""
        return not self._output_queue.empty()


def _worker_loop(model_size: str, config: WhisperConfig, input_queue: Queue, output_queue: Queue, name: str = "whisper") -> None:
    """
    The actual worker process loop.

    This runs in a separate process and loads the Whisper model.
    """
    import os
    # Workaround for OpenMP conflict when multiple libraries bundle their own runtime
    # (common with conda environments mixing numpy, torch, etc.)
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    from faster_whisper import WhisperModel

    # Determine device - try CUDA, fall back to CPU
    device = config.device
    compute_type = config.compute_type

    if device == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16" if compute_type == "auto" else compute_type
            else:
                device = "cpu"
                compute_type = "int8" if compute_type == "auto" else compute_type
        except ImportError:
            device = "cpu"
            compute_type = "int8" if compute_type == "auto" else compute_type

    if compute_type == "auto":
        compute_type = "int8" if device == "cpu" else "float16"

    # Load the model (this can take a few seconds)
    try:
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        print(f"[Whisper:{name}] Model '{model_size}' loaded on {device} with {compute_type}")
    except Exception as e:
        # If CUDA fails, fall back to CPU
        print(f"[Whisper:{name}] Failed to load on {device}: {e}")
        print(f"[Whisper:{name}] Falling back to CPU...")
        device = "cpu"
        compute_type = "int8"
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        print(f"[Whisper:{name}] Model '{model_size}' loaded on {device} with {compute_type}")

    while True:
        try:
            request = input_queue.get(timeout=1.0)
        except:
            # Timeout - check if we should exit (parent process died, etc.)
            continue

        # None is our sentinel to stop
        if request is None:
            break

        try:
            # Run transcription
            segments, info = model.transcribe(
                request.audio,
                language=config.language,
                beam_size=5,
                vad_filter=True,  # Filter out silence
            )

            # Collect all segments
            segment_list = []
            full_text_parts = []

            for segment in segments:
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                })
                full_text_parts.append(segment.text)

            full_text = " ".join(full_text_parts).strip()

            result = TranscriptionResult(
                text=full_text,
                start_time=request.start_time,
                end_time=request.end_time,
                segments=segment_list,
                chunk_type=request.chunk_type,
            )

            output_queue.put(result)

        except Exception as e:
            # Put error result
            result = TranscriptionResult(
                text=f"[Transcription error: {e}]",
                start_time=request.start_time,
                end_time=request.end_time,
                segments=[],
                chunk_type=request.chunk_type,
            )
            output_queue.put(result)
