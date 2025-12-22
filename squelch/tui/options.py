"""
Options modal screen for Squelch settings.
"""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static, Switch, Input
from textual.binding import Binding

from ..config import config
from ..engine import AudioCapture


# Whisper model options
WHISPER_MODELS = [
    ("tiny", "tiny"),
    ("base", "base"),
    ("small", "small"),
    ("medium", "medium"),
    ("large-v2", "large-v2"),
    ("large-v3", "large-v3"),
]

# Language options (most common + auto)
WHISPER_LANGUAGES = [
    ("Auto-detect", "auto"),
    ("English", "en"),
    ("French", "fr"),
    ("German", "de"),
    ("Spanish", "es"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
    ("Polish", "pl"),
    ("Russian", "ru"),
    ("Chinese", "zh"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Arabic", "ar"),
    ("Hindi", "hi"),
]


class OptionsScreen(ModalScreen[dict | None]):
    """Modal screen for editing options."""

    CSS = """
    OptionsScreen {
        align: center middle;
    }

    #options-container {
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #title-bar {
        width: 100%;
        height: 3;
    }

    #options-title {
        text-style: bold;
        content-align: center middle;
    }

    #close-x {
        dock: right;
        min-width: 3;
        max-width: 3;
        background: transparent;
        border: none;
    }

    #close-x:hover {
        background: $error;
        color: $text;
    }

    #options-content {
        height: 1fr;
        min-height: 5;
    }

    .section-title {
        text-style: bold;
        margin-top: 1;
        color: $text;
    }

    .option-row {
        height: 3;
        margin-bottom: 0;
    }

    .option-row Label {
        width: 20;
        padding-top: 1;
    }

    .option-row Select {
        width: 1fr;
    }

    .option-row Switch {
        width: auto;
    }

    .option-row Input {
        width: 1fr;
    }

    #button-row {
        margin-top: 1;
        padding-top: 1;
        border-top: solid $primary;
        align: center middle;
        height: 6;
        width: 100%;
    }

    #button-row Button {
        margin: 0 2;
        min-width: 12;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(
        self,
        audio_devices: list[tuple[str, str]],
        llm_models: list[tuple[str, str]],
        current_audio_device: str | None,
        current_llm_model: str | None,
        current_fast_whisper: str,
        current_slow_whisper: str,
        current_language: str | None,
        current_output_dir: str,
        dark_mode: bool,
    ):
        super().__init__()
        self.audio_devices = audio_devices
        self.llm_models = llm_models
        self.current_audio_device = current_audio_device
        self.current_llm_model = current_llm_model
        self.current_fast_whisper = current_fast_whisper
        self.current_slow_whisper = current_slow_whisper
        self.current_language = current_language if current_language else "auto"
        self.current_output_dir = current_output_dir
        self.dark_mode = dark_mode

    def compose(self) -> ComposeResult:
        with Vertical(id="options-container"):
            with Horizontal(id="title-bar"):
                yield Static("⚙ Options", id="options-title")
                yield Button("✕", id="close-x", variant="default")

            with VerticalScroll(id="options-content"):
                # Appearance section
                yield Static("Appearance", classes="section-title")
                with Horizontal(classes="option-row"):
                    yield Label("Dark mode:")
                    yield Switch(value=self.dark_mode, id="dark-mode")

                # Audio section
                yield Static("Audio", classes="section-title")
                with Horizontal(classes="option-row"):
                    yield Label("Device:")
                    yield Select(
                        self.audio_devices,
                        id="audio-device",
                        value=self.current_audio_device,
                        allow_blank=False,
                    )

                # Whisper section
                yield Static("Whisper", classes="section-title")
                with Horizontal(classes="option-row"):
                    yield Label("Language:")
                    yield Select(
                        WHISPER_LANGUAGES,
                        id="whisper-language",
                        value=self.current_language,
                        allow_blank=False,
                    )
                with Horizontal(classes="option-row"):
                    yield Label("Fast model:")
                    yield Select(
                        WHISPER_MODELS,
                        id="whisper-fast",
                        value=self.current_fast_whisper,
                        allow_blank=False,
                    )
                with Horizontal(classes="option-row"):
                    yield Label("Slow model:")
                    yield Select(
                        WHISPER_MODELS,
                        id="whisper-slow",
                        value=self.current_slow_whisper,
                        allow_blank=False,
                    )

                # LLM section
                yield Static("LLM (Ollama)", classes="section-title")
                with Horizontal(classes="option-row"):
                    yield Label("Model:")
                    if self.llm_models:
                        yield Select(
                            self.llm_models,
                            id="llm-model",
                            value=self.current_llm_model,
                            allow_blank=False,
                        )
                    else:
                        yield Static("No models available", id="llm-model-none")

                # Output section
                yield Static("Output", classes="section-title")
                with Horizontal(classes="option-row"):
                    yield Label("Directory:")
                    yield Input(value=self.current_output_dir, id="output-dir")

            # Buttons outside scroll area - always visible
            with Horizontal(id="button-row"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Reset", variant="warning", id="reset-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.save_and_close()
        elif event.button.id == "reset-btn":
            self.reset_to_defaults()
        elif event.button.id in ("cancel-btn", "close-x"):
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def reset_to_defaults(self) -> None:
        """Reset all options to default values."""
        try:
            # Reset UI widgets to defaults
            self.query_one("#dark-mode", Switch).value = True
            self.query_one("#audio-device", Select).value = "__default__"
            self.query_one("#whisper-language", Select).value = "en"
            self.query_one("#whisper-fast", Select).value = "base"
            self.query_one("#whisper-slow", Select).value = "small"

            # Reset output dir
            from pathlib import Path
            default_output = str(Path.home() / "Documents" / "Squelch")
            self.query_one("#output-dir", Input).value = default_output

            # Reset LLM if available
            try:
                llm_select = self.query_one("#llm-model", Select)
                if self.llm_models:
                    llm_select.value = self.llm_models[0][1]  # First available
            except Exception:
                pass

            self.notify("Reset to defaults (click Save to apply)", title="Options")
        except Exception as e:
            self.notify(f"Error resetting: {e}", severity="error")

    def save_and_close(self) -> None:
        """Save settings and close."""
        from pathlib import Path

        try:
            audio_select = self.query_one("#audio-device", Select)
            fast_select = self.query_one("#whisper-fast", Select)
            slow_select = self.query_one("#whisper-slow", Select)
            language_select = self.query_one("#whisper-language", Select)
            output_input = self.query_one("#output-dir", Input)
            dark_switch = self.query_one("#dark-mode", Switch)

            # Update config
            if audio_select.value != Select.BLANK:
                config.audio.device_name = audio_select.value if audio_select.value != "__default__" else None

            if fast_select.value != Select.BLANK:
                config.whisper.fast_model = fast_select.value

            if slow_select.value != Select.BLANK:
                config.whisper.slow_model = slow_select.value

            if language_select.value != Select.BLANK:
                config.whisper.language = None if language_select.value == "auto" else language_select.value

            # Output directory
            if output_input.value.strip():
                config.output.output_dir = Path(output_input.value.strip())

            # LLM model (if available)
            try:
                llm_select = self.query_one("#llm-model", Select)
                if llm_select.value != Select.BLANK:
                    config.llm.model = llm_select.value
            except Exception:
                pass  # No LLM models available

            # Return result with dark mode setting
            self.dismiss({"saved": True, "dark_mode": dark_switch.value})
        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error")

    @staticmethod
    def get_audio_devices() -> list[tuple[str, str]]:
        """Get list of audio devices for the select widget."""
        devices = [("Default", "__default__")]
        try:
            for device in AudioCapture.list_devices():
                if device["is_loopback"]:
                    name = device["name"]
                    # Truncate long names
                    display_name = name[:35] + "..." if len(name) > 38 else name
                    devices.append((display_name, name))
        except Exception:
            pass
        return devices