# Squelch

Meeting transcription tool with live transcription and AI-powered summaries.

## Features

- 🎤 **Live audio capture** from any Windows application via WASAPI loopback
- 📝 **Real-time transcription** using faster-whisper
- 🔄 **Dual-pass transcription** — fast pass for low latency, slow pass for accuracy
- 🤖 **AI-powered Q&A** during meetings via Ollama
- 📋 **Automatic summary generation** with key themes and action items
- 📄 **Markdown export** with collapsible full transcript
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
│ f5 Start/Stop  f10 End & Generate  f3 Response  q Quit│
└───────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

1. **Python 3.11+**

2. **Ollama** (for LLM features): Install from [ollama.ai](https://ollama.ai), then pull a model:
   ```powershell
   ollama pull llama3.1:8b
   ollama serve
   ```

3. **CUDA** (optional): For GPU-accelerated transcription, install CUDA toolkit and cuDNN.

### Install Squelch

```powershell
# Clone the repository
git clone https://github.com/vlouf/squelch.git
cd squelch

# Create a virtual environment
python -m venv venv
venv\Scripts\activate

# Install in development mode
pip install -e ".[dev,llm]"
```

## Usage

### Launch the TUI

```powershell
python -m squelch
```

### Keybindings

| Key | Action |
|-----|--------|
| F5 | Start/Stop recording |
| F10 | End meeting & generate summary |
| F3 | Toggle response panel |
| F2 | Options (coming soon) |
| Escape | Close response panel |
| Q | Quit (when not typing) |

### Workflow

1. **Start recording** (F5) — audio capture begins
2. **Watch live transcript** — fast pass appears in cyan, refined in green with ✓
3. **Ask questions** — type in the Ask input, press Enter for LLM response
4. **End meeting** (F10) — generates summary and exports to Markdown
5. **Review** — file opens automatically in your default Markdown viewer

### Output

Meeting notes are saved to `~/Documents/Squelch/` with filenames like:
```
2025-12-21_2118_meeting.md
```

The Markdown file includes:
- Meeting duration and word count
- AI-generated summary with key themes
- Action items (if any identified)
- Full transcript in a collapsible section

### Legacy CLI

For testing without the TUI:

```powershell
python -m squelch --cli
```

## Configuration

Edit `squelch/config.py` to change:

| Setting | Default | Description |
|---------|---------|-------------|
| `audio.fast_chunk_duration` | 6.0s | Fast pass chunk size |
| `audio.slow_chunk_duration` | 60.0s | Slow pass chunk size |
| `whisper.model_size` | "base" | Whisper model (tiny/base/small/medium/large) |
| `llm.model` | "llama3.1:8b" | Ollama model for Q&A and summaries |
| `llm.context_segments` | 20 | How many segments to include in Q&A context |
| `output.output_dir` | ~/Documents/Squelch | Where to save meeting notes |

## How It Works

### Dual-Pass Transcription

Squelch uses two parallel transcription passes:

1. **Fast pass** (6-second chunks): Low latency, displayed immediately in cyan
2. **Slow pass** (60-second chunks): Higher accuracy, replaces fast pass segments, displayed in green with ✓

This gives you quick feedback while maintaining transcript quality.

### Audio Capture

Squelch captures audio via WASAPI loopback — it records whatever is playing through your speakers/headphones. This works with any application (Teams, Zoom, YouTube, etc.) without needing virtual audio cables.

### LLM Integration

Squelch uses Ollama for local LLM inference:
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
│   ├── types.py          # Shared enums (ChunkType, TranscriptQuality)
│   ├── audio_capture.py  # WASAPI loopback capture with dual buffers
│   ├── transcriber.py    # faster-whisper worker process
│   ├── session.py        # Session state management
│   ├── llm.py            # LLM processor for Q&A
│   └── summarizer.py     # Meeting summary generation
├── export/
│   └── markdown.py       # Markdown file generation
└── tui/
    └── app.py            # Textual terminal UI
```

## Dependencies

| Library | Purpose |
|---------|---------|
| [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) | WASAPI loopback audio capture |
| [faster-whisper](https://github.com/guillaumekln/faster-whisper) | Speech-to-text transcription |
| [Textual](https://textual.textualize.io/) | Terminal UI framework |
| [httpx](https://www.python-httpx.org/) | Async HTTP client for Ollama API |
| [NumPy](https://numpy.org/) | Audio buffer manipulation |

## Development Roadmap

- [x] **Phase 1**: Audio capture & transcription engine
- [x] **Phase 2**: Textual TUI with live transcript display
- [x] **Phase 3**: LLM integration (live Q&A via Ollama)
- [x] **Phase 4**: Summary generation & Markdown export
- [ ] **Phase 5**: Polish (options menu, audio recording, theming)

## License

MIT