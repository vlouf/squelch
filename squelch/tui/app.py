"""
Main Squelch TUI application.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static, Input, RichLog
from textual.reactive import reactive

from ..config import config
from ..engine import AudioCapture, ChunkType, TranscriberWorker, Session, TranscriptQuality, LLMProcessor


class TranscriptView(RichLog):
    """Displays the live transcript."""

    def add_segment(self, timestamp: str, text: str, refined: bool = False) -> None:
        """Add a transcript segment."""
        if refined:
            # Refined/slow pass: green with checkmark
            self.write(f"[bold green]{timestamp}[/] [green]✓ {text}[/]")
        else:
            # Fast pass: cyan (default)
            self.write(f"[bold cyan]{timestamp}[/] {text}")


class EventLog(RichLog):
    """Displays system events."""

    def log_event(self, message: str) -> None:
        """Add an event with timestamp."""
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{time_str}[/] {message}")


class ResponsePanel(Vertical):
    """Collapsible panel for LLM responses."""

    is_expanded = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("🤖 Response", id="response-title", classes="panel-title")
        yield RichLog(id="response-log", highlight=True, markup=True, wrap=True, auto_scroll=True)

    def watch_is_expanded(self, expanded: bool) -> None:
        """React to expansion state changes."""
        self.set_class(expanded, "expanded")
        self.set_class(not expanded, "collapsed")

    def expand(self) -> None:
        """Expand the panel."""
        self.is_expanded = True

    def collapse(self) -> None:
        """Collapse the panel."""
        self.is_expanded = False

    def toggle(self) -> None:
        """Toggle expansion state."""
        self.is_expanded = not self.is_expanded

    def show_response(self, question: str, answer: str) -> None:
        """Display a Q&A exchange."""
        self.expand()
        try:
            log = self.query_one("#response-log", RichLog)
            log.write(f"[bold yellow]Q:[/] {question}")
            log.write(f"[bold white]A:[/] {answer}")
            log.write("")  # Blank line between exchanges
        except Exception:
            pass

    def show_loading(self, question: str) -> None:
        """Show loading state."""
        self.expand()
        try:
            log = self.query_one("#response-log", RichLog)
            log.write(f"[bold yellow]Q:[/] {question}")
            log.write("[dim]Thinking...[/]")
        except Exception:
            pass

    def clear_loading(self) -> None:
        """Remove the loading indicator (by clearing last line)."""
        # RichLog doesn't support removing lines easily, so we just let the answer overwrite
        pass


class SquelchApp(App):
    """Main Squelch application."""

    TITLE = "Squelch"
    CSS = """
    #main-container {
        height: 1fr;
    }

    #left-panel {
        width: 3fr;
    }

    #transcript-container {
        height: 1fr;
        border: solid green;
    }

    #event-container {
        width: 1fr;
        border: solid gray;
    }

    .panel-title {
        dock: top;
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
        text-style: bold;
    }

    #transcript-panel {
        padding: 0 1;
    }

    #event-log {
        padding: 0 1;
    }

    #response-log {
        padding: 0 1;
    }

    #ask-input {
        dock: bottom;
        margin: 1 0;
    }

    Header {
        background: $primary;
    }

    /* Response panel styles */
    ResponsePanel {
        height: auto;
        border: solid $primary;
        display: none;
    }

    ResponsePanel.expanded {
        display: block;
        height: auto;
        min-height: 5;
        max-height: 15;
    }

    ResponsePanel.collapsed {
        display: none;
    }

    #response-title {
        background: $primary;
        color: $text;
    }
    """

    BINDINGS = [
        Binding("f5", "toggle_recording", "Start/Stop"),
        Binding("f10", "end_meeting", "End & Generate"),
        Binding("f3", "toggle_response", "Response"),
        Binding("f2", "show_options", "Options"),
        Binding("escape", "collapse_response", "Close", show=False),
        Binding("q", "quit", "Quit"),
    ]

    # Reactive state
    is_recording = reactive(False)

    def __init__(self):
        super().__init__()
        self.session = Session()
        self.transcriber: TranscriberWorker | None = None
        self.audio: AudioCapture | None = None
        self.llm: LLMProcessor | None = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()

        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                with Vertical(id="transcript-container"):
                    yield Static("Transcript", classes="panel-title")
                    yield TranscriptView(id="transcript-panel", highlight=True, markup=True, wrap=True, auto_scroll=True)
                yield ResponsePanel(id="response-panel")
            with Vertical(id="event-container"):
                yield Static("Event Log", classes="panel-title")
                yield EventLog(id="event-log", highlight=True, markup=True, wrap=True, auto_scroll=True)

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

        # Initialize LLM processor
        self.llm = LLMProcessor()
        self.log_event(f"LLM: {config.llm.model}")

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

    def action_toggle_response(self) -> None:
        """Toggle the response panel."""
        try:
            panel = self.query_one("#response-panel", ResponsePanel)
            panel.toggle()
        except Exception:
            pass

    def action_collapse_response(self) -> None:
        """Collapse the response panel."""
        try:
            panel = self.query_one("#response-panel", ResponsePanel)
            panel.collapse()
        except Exception:
            pass

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
        if not query:
            return

        event.input.value = ""
        self.log_event(f"Ask: {query[:30]}...")

        if not self.llm:
            self.notify("LLM not initialized", title="Error")
            return

        # Get recent transcript for context
        transcript = self.session.get_recent_transcript(last_n=config.llm.context_segments)

        if not transcript:
            self.notify("No transcript yet. Start recording first!", title="Ask")
            return

        # Show loading state
        try:
            panel = self.query_one("#response-panel", ResponsePanel)
            panel.show_loading(query)
        except Exception:
            pass

        # Make async LLM call
        response = await self.llm.ask(query, transcript)

        # Show response
        try:
            panel = self.query_one("#response-panel", ResponsePanel)
            # Clear the loading message and show actual response
            log = panel.query_one("#response-log", RichLog)
            log.clear()

            # Show full history
            for exchange in self.llm.history:
                log.write(f"[bold yellow]Q:[/] {exchange['question']}")
                log.write(f"[bold white]A:[/] {exchange['answer']}")
                log.write("")

            panel.expand()
        except Exception as e:
            self.log_event(f"Error displaying response: {e}")