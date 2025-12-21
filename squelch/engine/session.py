"""
Session state management for a meeting transcription.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TranscriptSegment:
    """A single transcribed segment."""
    text: str
    start_time: float
    end_time: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Session:
    """
    Holds the state for a single meeting/recording session.

    This is the central data structure that the audio capture writes to,
    the transcriber updates, and the UI reads from.
    """
    started_at: datetime = field(default_factory=datetime.now)
    segments: list[TranscriptSegment] = field(default_factory=list)
    is_recording: bool = False

    # Running counters
    audio_chunks_captured: int = 0
    audio_chunks_transcribed: int = 0

    def add_segment(self, text: str, start_time: float, end_time: float) -> None:
        """Add a new transcript segment."""
        segment = TranscriptSegment(
            text=text.strip(),
            start_time=start_time,
            end_time=end_time,
        )
        self.segments.append(segment)
        self.audio_chunks_transcribed += 1

    def get_full_transcript(self) -> str:
        """Return the complete transcript as a single string."""
        return "\n".join(seg.text for seg in self.segments if seg.text)

    def get_recent_transcript(self, last_n: int = 5) -> str:
        """Return the last N segments, useful for LLM context."""
        recent = self.segments[-last_n:] if self.segments else []
        return "\n".join(seg.text for seg in recent if seg.text)

    @property
    def duration(self) -> float:
        """Total duration of transcribed audio in seconds."""
        if not self.segments:
            return 0.0
        return self.segments[-1].end_time

    @property
    def word_count(self) -> int:
        """Approximate word count."""
        return sum(len(seg.text.split()) for seg in self.segments)