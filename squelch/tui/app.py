"""
Main Squelch TUI application.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static, Input, RichLog
from textual.reactive import reactive

from ..config import config
from ..engine import AudioCapture, ChunkType, TranscriberWorker, Session, TranscriptQuality


class StatusIndicator(Static):
    """Shows recording status."""

    status = reactive("stopped")

    def render(self) -> str:
        icons = {
            "stopped": "⚫ Stopped",
            "recording": "🔴 Recording",
            "paused": "⏸ Paused",
        }
        return icons.get(self.status, "⚫ Unknown")


class TranscriptView(RichLog):
    """Displays the live transcript."""

    def add_segment(self, timestamp: str, text: str, refined: bool = False) -> None:
        """Add a transcript segment."""
        marker = " ✓" if refined else ""
        self.write(f"[bold cyan]{timestamp}[/]{marker} {text}")


class EventLog(RichLog):
    """Displays system events."""

    def log_event(self, message: str) -> None:
        """Add an event with timestamp."""
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{time_str}[/] {message}")


class SquelchApp(App):
    """Main Squelch application."""

    TITLE = "Squelch"
    CSS = """
    #main-container {
        height: 1fr;
    }

    #transcript-panel {
        width: 3fr;
        border: solid green;
        padding: 0 1;
    }

    #event-log {
        width: 1fr;
        border: solid gray;
        padding: 0 1;
    }

    #ask-input {
        dock: bottom;
        margin: 1 0;
    }

    #status {
        dock: right;
        width: auto;
        padding: 0 1;
    }

    Header {
        background: $primary;
    }
    """

    BINDINGS = [
        Binding("f5", "toggle_recording", "Start/Stop"),
        Binding("f10", "end_meeting", "End & Generate"),
        Binding("f2", "show_options", "Options"),
        Binding("q", "quit", "Quit"),
    ]

    # Reactive state
    is_recording = reactive(False)

    def __init__(self):
        super().__init__()
        self.session = Session()
        self.transcriber: TranscriberWorker | None = None
        self.audio: AudioCapture | None = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()

        with Horizontal(id="main-container"):
            yield TranscriptView(id="transcript-panel", highlight=True, markup=True)
            yield EventLog(id="event-log", highlight=True, markup=True)

        yield Input(placeholder="💬 Ask about the transcript...", id="ask-input")
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.log_event("Squelch ready")
        self.log_event(f"Fast: {config.audio.fast_chunk_duration}s | Slow: {config.audio.slow_chunk_duration}s")

        # Initialize transcriber
        self.log_event(f"Loading Whisper '{config.whisper.model_size}'...")
        self.transcriber = TranscriberWorker(config.whisper)
        self.transcriber.start()
        self.log_event("Whisper ready")

        # Set up polling for transcription results
        self.set_interval(0.1, self.poll_transcriptions)

    def log_event(self, message: str) -> None:
        """Log an event to the event panel."""
        try:
            event_log = self.query_one("#event-log", EventLog)
            event_log.log_event(message)
        except Exception:
            pass

    def add_transcript(self, timestamp: str, text: str, refined: bool = False) -> None:
        """Add a transcript segment to the panel."""
        try:
            transcript = self.query_one("#transcript-panel", TranscriptView)
            transcript.add_segment(timestamp, text, refined)
        except Exception:
            pass

    def on_chunk_ready(self, audio_data, start_time: float, end_time: float, chunk_type: ChunkType) -> None:
        """Called when an audio chunk is ready for transcription."""
        self.session.audio_chunks_captured += 1
        duration = end_time - start_time
        type_label = "FAST" if chunk_type.value == "fast" else "SLOW"
        self.log_event(f"{type_label} {duration:.1f}s")

        if self.transcriber:
            self.transcriber.submit(audio_data, start_time, end_time, chunk_type)

    def poll_transcriptions(self) -> None:
        """Poll for transcription results."""
        if not self.transcriber:
            return

        result = self.transcriber.get_result(timeout=None)
        if result:
            is_fast = result.chunk_type.value == "fast"
            quality = TranscriptQuality.FAST if is_fast else TranscriptQuality.REFINED
            self.session.add_segment(result.text, result.start_time, result.end_time, quality)

            # Format timestamp
            minutes = int(result.start_time // 60)
            seconds = int(result.start_time % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"

            if result.text:
                self.add_transcript(timestamp, result.text, refined=not is_fast)

    def action_toggle_recording(self) -> None:
        """Toggle recording on/off."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        """Start audio capture."""
        if self.audio is not None:
            return

        try:
            self.audio = AudioCapture(config.audio, on_chunk_ready=self.on_chunk_ready)
            self.audio.start()
            self.is_recording = True
            self.session.is_recording = True
            self.log_event("Recording started")
            self.update_status("recording")
        except Exception as e:
            self.log_event(f"Error: {e}")

    def stop_recording(self) -> None:
        """Stop audio capture."""
        if self.audio is None:
            return

        try:
            self.audio.stop()
            self.audio = None
            self.is_recording = False
            self.session.is_recording = False
            self.log_event("Recording stopped")
            self.update_status("stopped")
        except Exception as e:
            self.log_event(f"Error: {e}")

    def update_status(self, status: str) -> None:
        """Update the header status indicator."""
        self.sub_title = {"recording": "🔴 Recording", "stopped": "⚫ Stopped", "paused": "⏸ Paused"}.get(status, "")

    def action_end_meeting(self) -> None:
        """End the meeting and generate summary."""
        self.stop_recording()
        self.log_event("Meeting ended")
        self.log_event(f"Duration: {self.session.duration:.1f}s")
        self.log_event(f"Words: {self.session.word_count}")
        # TODO: Phase 4 - Generate summary and export markdown
        self.notify("Summary generation coming in Phase 4!", title="End Meeting")

    def action_show_options(self) -> None:
        """Show options menu."""
        self.notify("Options coming in Phase 5!", title="Options")

    def action_quit(self) -> None:
        """Quit the application."""
        self.stop_recording()
        if self.transcriber:
            self.transcriber.stop()
        self.exit()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle ask input submission."""
        query = event.value.strip()
        if query:
            self.log_event(f"Ask: {query[:30]}...")
            # TODO: Phase 3 - Send to LLM
            self.notify("LLM integration coming in Phase 3!", title="Ask")
            event.input.value = ""