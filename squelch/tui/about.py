"""
About/Help modal screen for Squelch.
"""

from textual.app import ComposeResult
from textual.containers import Vertical, Center, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Markdown
from textual.binding import Binding


ABOUT_TEXT = """\
# Squelch

**Meeting transcription tool with AI-powered summaries**

Version 0.1.0

---

## Keybindings

| Key | Action |
|-----|--------|
| **F5** | Start/Stop recording |
| **F10** | End meeting & export |
| **F3** | Toggle response panel |
| **F2** | Options menu |
| **F1** | This help screen |
| **Ctrl+P** | Command palette |
| **Escape** | Close panels |
| **Q** | Quit |

---

## How It Works

1. Press **F5** to start recording system audio
2. Watch the **live transcript** appear (cyan = fast, green ✓ = refined)
3. **Ask questions** about the meeting in the input box
4. Press **F10** to end and generate a summary

---

## Tips

- Use **Ctrl+P** to access themes and commands
- Change Whisper models in **F2 Options** for speed vs accuracy
- The slow pass refines transcripts for better export quality

---

Made with ❤️ by Valentin Louf & Claude

Built with [Textual](https://textual.textualize.io/) and [faster-whisper](https://github.com/guillaumekln/faster-whisper)

© 2025 Valentin Louf
"""


class AboutScreen(ModalScreen[None]):
    """Modal screen showing about/help information."""

    CSS = """
    AboutScreen {
        align: center middle;
    }

    #about-container {
        width: 70;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #title-bar {
        width: 100%;
        height: 1;
        margin-bottom: 1;
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

    #about-content {
        height: auto;
        max-height: 100%;
        overflow-y: auto;
    }

    #about-content Markdown {
        margin: 0 1;
    }

    #button-row {
        margin-top: 1;
        padding-top: 1;
        border-top: solid $primary;
        align: center middle;
        height: auto;
        width: 100%;
    }

    #close-btn {
        min-width: 16;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False, priority=True),
        Binding("f1", "close", "Close", show=False, priority=True),
        Binding("enter", "close", "Close", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="about-container"):
            with Horizontal(id="title-bar"):
                yield Button("✕", id="close-x", variant="default")
            with Vertical(id="about-content"):
                yield Markdown(ABOUT_TEXT)
            with Center(id="button-row"):
                yield Button("Close", variant="primary", id="close-btn")

    def on_mount(self) -> None:
        """Focus the close button on mount."""
        self.query_one("#close-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("close-btn", "close-x"):
            self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)