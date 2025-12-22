"""
Squelch engine - audio capture and transcription.
"""

from .types import ChunkType, TranscriptQuality
from .audio import AudioCapture
from .transcriber import TranscriberWorker
from .session import Session
from .llm import create_llm_processor, LLMProcessor, OllamaProcessor, LiteLLMProcessor
from .summarizer import Summarizer, SummaryResult

__all__ = [
    "AudioCapture",
    "ChunkType",
    "TranscriberWorker",
    "Session",
    "TranscriptQuality",
    "create_llm_processor",
    "LLMProcessor",
    "OllamaProcessor",
    "LiteLLMProcessor",
    "Summarizer",
    "SummaryResult",
]