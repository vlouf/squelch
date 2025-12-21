# Squelch

Meeting transcription tool with live transcription and AI-powered summaries.

## Features

- 🎤 **Live audio capture** from any Windows application via WASAPI loopback
- 📝 **Real-time transcription** using faster-whisper
- 🔄 **Dual-pass transcription** — fast pass for low latency, slow pass for accuracy
- 🤖 **AI-powered Q&A** during meetings (Phase 3 - in progress)
- 📋 **Automatic summary generation** with action items (Phase 4 - planned)
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
├─────────────────────────────────────────┴─────────────┤
│ 💬 Ask about the transcript...                        │
├───────────────────────────────────────────────────────┤
│ f5 Start/Stop  f10 End & Generate  f2 Options  q Quit │
└───────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

1. **Python 3.11+**

2. **Ollama** (for LLM features): Install from [ollama.ai](https://ollama.ai), then pull a model:
   ```powershell
   ollama pull llama3.1:8b
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
| F2 | Options (coming soon) |
| Q | Quit |

### Legacy CLI

For testing without the TUI:

```powershell
python -m squelch --cli
```

## Configuration

Edit `squelch/config.py` to change:

- **Audio settings**: sample rate, device name
- **Chunk durations**: `fast_chunk_duration` (default 6s), `slow_chunk_duration` (default 60s)
- **Whisper model**: tiny / base / small / medium / large-v2 / large-v3

## How It Works

### Dual-Pass Transcription

Squelch uses two parallel transcription passes:

1. **Fast pass** (6-second chunks): Low latency, displayed immediately in cyan
2. **Slow pass** (60-second chunks): Higher accuracy, replaces fast pass segments, displayed in green with ✓

This gives you quick feedback while maintaining transcript quality.

### Audio Capture

Squelch captures audio via WASAPI loopback — it records whatever is playing through your speakers/headphones. This works with any application (Teams, Zoom, YouTube, etc.) without needing virtual audio cables.

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
│   └── session.py        # Session state management
└── tui/
    └── app.py            # Textual terminal UI
```

## Dependencies

| Library | Purpose |
|---------|---------|
| [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) | WASAPI loopback audio capture |
| [faster-whisper](https://github.com/guillaumekln/faster-whisper) | Speech-to-text transcription |
| [Textual](https://textual.textualize.io/) | Terminal UI framework |
| [NumPy](https://numpy.org/) | Audio buffer manipulation |

## Development Roadmap

- [x] **Phase 1**: Audio capture & transcription engine
- [x] **Phase 2**: Textual TUI with live transcript display
- [ ] **Phase 3**: LLM integration (live Q&A via Ollama)
- [ ] **Phase 4**: Summary generation & Markdown export
- [ ] **Phase 5**: Polish (options menu, audio recording, theming)

## License

MIT