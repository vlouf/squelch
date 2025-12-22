# Contributing to Squelch

Thanks for your interest in contributing! This document covers development setup and guidelines.

## Development Setup

### Prerequisites

- Python 3.11+
- Git
- (Optional) CUDA for GPU acceleration

### Clone and Install

```bash
git clone https://github.com/vlouf/squelch.git
cd squelch

python -m venv venv
source venv/bin/activate  # Linux
venv\Scripts\activate     # Windows

# Install with dev dependencies
pip install -e ".[dev,cloud]"
```

### Running

```bash
# TUI (main interface)
squelch

# Or via module
python -m squelch

# Legacy CLI (for testing)
squelch --cli
```

### Code Quality

```bash
# Lint with ruff
ruff check squelch/

# Format
ruff format squelch/

# Run tests
pytest
```

## Project Structure

```
squelch/
├── __init__.py
├── __main__.py           # Entry point
├── cli.py                # Legacy test CLI
├── config.py             # Configuration with TOML persistence
├── engine/
│   ├── audio/
│   │   ├── base.py       # Abstract audio interface
│   │   ├── windows.py    # WASAPI loopback
│   │   └── linux.py      # PipeWire loopback
│   ├── types.py          # Shared enums
│   ├── transcriber.py    # Whisper worker processes
│   ├── session.py        # Session state
│   ├── llm.py            # LLM factory
│   ├── llm_ollama.py     # Ollama processor
│   ├── llm_litellm.py    # Cloud LLM processor
│   └── summarizer.py     # Summary generation
├── export/
│   └── markdown.py       # Markdown export
└── tui/
    ├── app.py            # Main Textual app
    ├── options.py        # Options modal
    ├── about.py          # About/Help modal
    └── themes.py         # Custom themes
```

## Architecture Overview

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed technical documentation.

### Key Concepts

**Dual-Pass Transcription**

Two parallel Whisper workers process audio:
1. **Fast pass** (6s chunks, `base` model) — Low latency display
2. **Slow pass** (60s chunks, `small` model) — Higher accuracy, replaces fast segments

**Audio Capture**

Platform-specific loopback capture:
- Windows: WASAPI via PyAudioWPatch
- Linux: PipeWire via sounddevice

**LLM Integration**

Factory pattern for LLM providers:
- `OllamaProcessor` — Local inference via Ollama API
- `LiteLLMProcessor` — Cloud providers (OpenAI, Anthropic, Google, etc.)

**Configuration**

TOML-based config with platform-appropriate paths:
- Windows: `%APPDATA%\Squelch\config.toml`
- Linux: `~/.config/squelch/config.toml`

## How to Contribute

### Reporting Issues

- Check existing issues first
- Include Python version, OS, and steps to reproduce
- Attach relevant logs if possible

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run linting: `ruff check squelch/`
5. Test your changes
6. Commit with clear messages
7. Push and open a PR

### Code Style

- Follow existing patterns in the codebase
- Use type hints
- Keep functions focused and documented
- Prefer composition over inheritance

### Areas for Contribution

**Good first issues:**
- Documentation improvements
- Bug fixes
- Test coverage

**Larger contributions:**
- macOS audio capture (CoreAudio)
- Additional export formats
- UI improvements

## Questions?

Open an issue or discussion on GitHub.
