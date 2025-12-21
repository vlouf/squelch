# Squelch

Meeting transcription tool with live transcription and AI-powered summaries.

## Features (Planned)

- 🎤 Live audio capture from any application via WASAPI loopback
- 📝 Real-time transcription using faster-whisper
- 🤖 AI-powered Q&A during meetings
- 📋 Automatic summary generation with action items
- 💻 Terminal-based UI using Textual

## Installation

<!-- ### Prerequisites -->

<!-- 1. **VB-Cable** (recommended): Install [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) to route specific application audio to Squelch. -->

<!-- 2. **CUDA** (optional): For GPU-accelerated transcription, install CUDA toolkit and cuDNN. -->

### Install Squelch

```bash
# Clone the repository
git clone https://github.com/vlouf/squelch.git
cd squelch

# Create a virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev,tui,llm]"
```

## Usage

### Phase 1: Basic Transcription

```bash
# Run the test CLI
python -m squelch

# Or use the entry point
squelch
```

This will:
1. List available loopback audio devices
2. Start capturing from the default output device
3. Transcribe audio in 30-second chunks
4. Print transcript to the terminal

Press `Ctrl+C` to stop.

### Configuration

Edit `squelch/config.py` to change:
- Audio device and sample rate
- Whisper model size (tiny/base/small/medium/large)
- Chunk duration for transcription

## Project Structure

```
squelch/
├── __init__.py
├── __main__.py           # Entry point
├── config.py             # Configuration
├── cli.py                # Phase 1 test CLI
└── engine/
    ├── __init__.py
    ├── audio_capture.py  # PyAudioWPatch WASAPI capture
    ├── transcriber.py    # faster-whisper worker process
    └── session.py        # Session state management
```

## Development Phases

- [x] Phase 1: Audio capture & transcription
- [ ] Phase 2: Textual TUI
- [ ] Phase 3: LLM integration (live Q&A)
- [ ] Phase 4: Summary & Markdown export
- [ ] Phase 5: Polish & UX

## License

MIT