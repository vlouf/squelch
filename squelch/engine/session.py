"""
Session state management for a meeting transcription.
"""

from dataclasses import dataclass, field
from datetime import datetime

from .types import TranscriptQuality


@dataclass
class TranscriptSegment:
    """A single transcribed segment."""

    text: str
    start_time: float  # Seconds from start of recording
    end_time: float
    quality: TranscriptQuality = TranscriptQuality.FAST
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class Session:
    """
    Holds the state for a single meeting/recording session.

    This is the central data structure that the audio capture writes to,
    the transcriber updates, and the UI reads from.

    Supports dual-pass transcription:
    - Fast pass: displayed immediately in UI
    - Slow pass: replaces fast pass segments for final export
    """

    started_at: datetime = field(default_factory=datetime.now)
    segments: list[TranscriptSegment] = field(default_factory=list)
    is_recording: bool = False

    # Running counters
    audio_chunks_captured: int = 0
    fast_chunks_transcribed: int = 0
    slow_chunks_transcribed: int = 0

    def add_segment(
        self,
        text: str,
        start_time: float,
        end_time: float,
        quality: TranscriptQuality = TranscriptQuality.FAST,
    ) -> None:
        """Add a new transcript segment."""
        segment = TranscriptSegment(
            text=text.strip(),
            start_time=start_time,
            end_time=end_time,
            quality=quality,
        )

        if quality == TranscriptQuality.FAST:
            self.segments.append(segment)
            self.fast_chunks_transcribed += 1
        else:
            # Refined segment - replace corresponding fast segments
            self._replace_with_refined(segment)
            self.slow_chunks_transcribed += 1

    def _replace_with_refined(self, refined: TranscriptSegment) -> None:
        """Replace fast segments that fall within the refined segment's time range."""
        # Find segments that overlap with the refined segment
        # and are still marked as FAST
        new_segments = []
        replaced = False

        for seg in self.segments:
            # Check if this segment overlaps with the refined one
            overlaps = seg.start_time < refined.end_time and seg.end_time > refined.start_time

            if overlaps and seg.quality == TranscriptQuality.FAST:
                # This fast segment is covered by the refined one
                if not replaced:
                    # Add the refined segment in place of the first overlapping fast segment
                    new_segments.append(refined)
                    replaced = True
                # Skip adding the fast segment (it's being replaced)
            else:
                new_segments.append(seg)

        # If no overlap found (shouldn't happen), just append
        if not replaced:
            new_segments.append(refined)

        self.segments = new_segments

    def get_full_transcript(self, quality: TranscriptQuality | None = None) -> str:
        """
        Return the complete transcript as a single string.

        Args:
            quality: If specified, only include segments of this quality.
                     If None, use best available (refined if available, else fast).
        """
        if quality is not None:
            segments = [s for s in self.segments if s.quality == quality]
        else:
            segments = self.segments

        return "\n".join(seg.text for seg in segments if seg.text)

    def get_recent_transcript(self, last_n: int = 5) -> str:
        """Return the last N segments, useful for LLM context."""
        recent = self.segments[-last_n:] if self.segments else []
        return "\n".join(seg.text for seg in recent if seg.text)

    def get_best_transcript(self) -> str:
        """
        Get the best quality transcript for export.

        Uses refined segments where available, falls back to fast segments
        for recent audio that hasn't been refined yet.
        """
        # Segments are already stored with refined replacing fast where available
        return "\n".join(seg.text for seg in self.segments if seg.text)

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

    @property
    def refined_percentage(self) -> float:
        """Percentage of transcript that has been refined."""
        if not self.segments:
            return 0.0
        refined = sum(1 for s in self.segments if s.quality == TranscriptQuality.REFINED)
        return (refined / len(self.segments)) * 100
