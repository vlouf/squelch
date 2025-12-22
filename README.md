# Squelch

Meeting transcription tool with live transcription and AI-powered summaries.

## Features

- 🎤 **Live audio capture** from system audio (Windows WASAPI, Linux PipeWire)
- 📝 **Real-time transcription** using faster-whisper
- 🔄 **Dual-pass transcription** — fast model for low latency, better model for accuracy
- 🤖 **AI-powered Q&A** during meetings via Ollama (auto-detects available models)
- 📋 **Automatic summary generation** with key themes and action items
- 📄 **Markdown export** with collapsible full transcript
- ⚙️ **Options menu** — change settings without editing config files
- 🎨 **Theming** — Command palette with multiple built-in themes
- 💻 **Terminal UI** using Textual

## Screenshots

```
┌─ Squelch ─────────────────────────────── Recording 🔴 ─┐
│ Transcript                              │ Event Log   │
│                                         │             │
│ [00:01] To build a textual app, you     │ 20:11:02    │
│ need to define a class that inherits... │ FAST 6.1s   │
│                                         │             │
│ [00:07] ✓ The Widgets module is where   │ 20:11:08    │
│ you find a rich set of widgets...       │ SLOW 60.0s  │
│                                         │             │
├─────────────────────────────────────────┤             │
│ 🤖 Response                             │             │
│ Q: What are the main topics?            │             │
│ A: The discussion covers building       │             │
│    Textual apps and widget modules...   │             │
├─────────────────────────────────────────┴─────────────┤
│ 💬 Ask about the transcript...                        │
├───────────────────────────────────────────────────────┤
│ f5 Start/Stop  f10 End & Generate  f2 Options  q Quit │
└───────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

1. **Python 3.11+**

2. **Ollama** (for LLM features): Install from [ollama.ai](https://ollama.ai), then pull any model:
   ```bash
   ollama pull llama3.1:8b
   ollama serve
   ```
   Squelch auto-detects available models — use whichever you prefer.

3. **CUDA** (optional): For GPU-accelerated transcription, install CUDA toolkit and cuDNN.

4. **Linux only**: PipeWire is required for audio capture:
   ```bash
   # Debian/Ubuntu
   sudo apt install pipewire pipewire-pulse
   
   # Fedora
   sudo dnf install pipewire pipewire-pulseaudio
   ```

### Install Squelch

```bash
# Clone the repository
git clone https://github.com/vlouf/squelch.git
cd squelch

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev,llm]"
```

## Usage

### Launch the TUI

```bash
python -m squelch
```

### Keybindings

| Key | Action |
|-----|--------|
| F5 | Start/Stop recording |
| F10 | End meeting & generate summary |
| F3 | Toggle response panel |
| F2 | Options menu |
| Ctrl+P | Command palette (themes, commands) |
| Escape | Close response panel |
| Q | Quit (when not typing) |

### Command Palette (Ctrl+P)

Press `Ctrl+P` to open the command palette. From here you can:

- **Change themes** — Type "theme" to see all available themes (nord, gruvbox, dracula, monokai, tokyo-night, etc.)
- **Run commands** — Toggle recording, end meeting, open options, and more

### Workflow

1. **Start recording** (F5) — audio capture begins
2. **Watch live transcript** — fast pass appears in cyan, refined in green with ✓
3. **Ask questions** — type in the Ask input, press Enter for LLM response
4. **End meeting** (F10) — generates summary and exports to Markdown
5. **Review** — file opens automatically in your default Markdown viewer

### Options Menu (F2)

Press F2 (when not recording) to open the options menu:

- **Dark mode** — Toggle between dark and light themes
- **Audio Device** — select which loopback device to capture from
- **Whisper Fast Model** — model for quick transcription (tiny, base, small, medium, large)
- **Whisper Slow Model** — model for refined transcription
- **LLM Model** — select from available Ollama models

Settings are applied immediately on save. Whisper models are reloaded automatically.

### Output

Meeting notes are saved to `~/Documents/Squelch/` with filenames like:
```
2025-12-22_1430_meeting.md
```

The Markdown file includes:
- Meeting duration and word count
- AI-generated summary with key themes
- Action items (if any identified)
- Full transcript in a collapsible section

### Legacy CLI

For testing without the TUI:

```bash
python -m squelch --cli
```

## Configuration

Settings can be changed via the Options menu (F2) or by editing `squelch/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `audio.device_name` | None (default device) | Audio loopback device |
| `audio.fast_chunk_duration` | 6.0s | Fast pass chunk size |
| `audio.slow_chunk_duration` | 60.0s | Slow pass chunk size |
| `whisper.fast_model` | "base" | Whisper model for fast pass |
| `whisper.slow_model` | "small" | Whisper model for slow pass |
| `llm.model` | None (auto-detect) | Ollama model for Q&A and summaries |
| `llm.context_segments` | 20 | How many segments to include in Q&A context |
| `output.output_dir` | ~/Documents/Squelch | Where to save meeting notes |

## How It Works

### Dual-Pass Transcription

Squelch uses two parallel transcription workers with different models:

1. **Fast pass** (6-second chunks, `base` model): Low latency, displayed immediately in cyan
2. **Slow pass** (60-second chunks, `small` model): Higher accuracy, replaces fast pass segments, displayed in green with ✓

This gives you quick feedback while maintaining transcript quality.

### Audio Capture

Squelch captures system audio via loopback — it records whatever is playing through your speakers/headphones. This works with any application (Teams, Zoom, YouTube, etc.) without needing virtual audio cables.

- **Windows**: WASAPI loopback via PyAudioWPatch
- **Linux**: PipeWire loopback via sounddevice

### LLM Integration

Squelch uses Ollama for local LLM inference:
- **Auto-detection**: Automatically finds and uses available Ollama models
- **Live Q&A**: Ask questions about the transcript mid-meeting
- **Summary generation**: Automatic key themes and action item extraction
- **Privacy**: All processing happens locally on your machine

## Project Structure

```
squelch/
├── __init__.py
├── __main__.py           # Entry point (TUI or --cli)
├── cli.py                # Legacy test CLI
├── config.py             # Configuration
├── engine/
│   ├── audio/
│   │   ├── base.py       # Abstract audio capture interface
│   │   ├── windows.py    # WASAPI loopback (Windows)
│   │   └── linux.py      # PipeWire loopback (Linux)
│   ├── types.py          # Shared enums (ChunkType, TranscriptQuality)
│   ├── transcriber.py    # faster-whisper worker processes
│   ├── session.py        # Session state management
│   ├── llm.py            # LLM processor for Q&A
│   └── summarizer.py     # Meeting summary generation
├── export/
│   └── markdown.py       # Markdown file generation
└── tui/
    ├── app.py            # Textual terminal UI
    └── options.py        # Options modal screen
```

## Platform Support

| Platform | Status | Audio Backend |
|----------|--------|---------------|
| Windows | ✅ Supported | WASAPI loopback |
| Linux | ✅ Supported | PipeWire |
| macOS | ❌ Not implemented | — |

## Dependencies

| Library | Purpose |
|---------|---------|
| [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) | WASAPI loopback audio capture (Windows) |
| [sounddevice](https://python-sounddevice.readthedocs.io/) | Audio capture (Linux) |
| [faster-whisper](https://github.com/guillaumekln/faster-whisper) | Speech-to-text transcription |
| [Textual](https://textual.textualize.io/) | Terminal UI framework |
| [httpx](https://www.python-httpx.org/) | Async HTTP client for Ollama API |
| [NumPy](https://numpy.org/) | Audio buffer manipulation |

## Development Roadmap

- [x] **Phase 1**: Audio capture & transcription engine
- [x] **Phase 2**: Textual TUI with live transcript display
- [x] **Phase 3**: LLM integration (live Q&A via Ollama)
- [x] **Phase 4**: Summary generation & Markdown export
- [x] **Phase 5**: Options menu, dual Whisper models, theming, Linux support

### Future Ideas

- [ ] macOS audio capture (CoreAudio)
- [ ] Save raw audio as WAV (opt-in)
