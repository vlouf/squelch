# Squelch

Meeting transcription tool with live transcription and AI-powered summaries.

## Features

- 🎤 **Live audio capture** from system audio (Windows WASAPI, Linux PipeWire)
- 📝 **Real-time transcription** using faster-whisper
- 🔄 **Dual-pass transcription** — fast model for low latency, better model for accuracy
- 🤖 **AI-powered Q&A** during meetings (local via Ollama, or cloud via OpenAI/Claude/Gemini)
- 📋 **Automatic summary generation** with key themes and action items
- 📄 **Markdown export** with collapsible full transcript
- ⚙️ **Options menu** — change settings without editing config files
- 🎨 **Theming** — multiple built-in themes via command palette
- 💾 **Persistent config** — settings saved automatically
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

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| Windows | ✅ Supported | WASAPI loopback |
| Linux | ✅ Supported | Requires PipeWire |
| macOS | ❌ Not yet | Contributions welcome! |

## Installation

### Prerequisites

**Python 3.11+** is required.

**Windows** — No additional setup needed.

**Linux** — Install PipeWire:
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

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux
venv\Scripts\activate     # Windows

# Install
pip install -e .

# Optional: install cloud LLM support
pip install -e ".[cloud]"
```

### LLM Setup (Optional)

For AI-powered Q&A and summaries, you need an LLM provider:

**Option A: Ollama (Local, Free)**
```bash
# Install from https://ollama.ai, then:
ollama pull llama3.1:8b
ollama serve
```

**Option B: Cloud Providers**

Install cloud support and set your API key:
```bash
pip install -e ".[cloud]"

# Then set ONE of these:
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GEMINI_API_KEY=...
```

## Usage

### Launch

```bash
squelch
```

### Keybindings

| Key | Action |
|-----|--------|
| **F5** | Start/Stop recording |
| **F10** | End meeting & generate summary |
| **F3** | Toggle response panel |
| **F2** | Options menu |
| **F1** | Help |
| **Ctrl+P** | Command palette |
| **Q** | Quit |

### Workflow

1. **F5** — Start recording (captures system audio)
2. Watch the live transcript appear
3. Type questions in the input box for AI responses
4. **F10** — End meeting, generate summary, export to Markdown
5. Review the exported file (opens automatically)

### Options (F2)

Configure without editing files:

- **Theme** — Dark/light mode
- **Audio device** — Select loopback source
- **Whisper models** — Choose speed vs accuracy tradeoff
- **Language** — Set transcription language
- **LLM provider** — Ollama (local) or Cloud
- **Output directory** — Where to save meeting notes

Settings persist between sessions.

### Command Palette (Ctrl+P)

Quick access to themes and commands. Type to search:
- `theme` — Browse all themes (nord, gruvbox, dracula, etc.)
- `toggle` — Recording, response panel, dark mode
- `options` — Open settings

### Output

Meeting notes are saved as Markdown:
```
~/Documents/Squelch/2025-12-22_1430_meeting.md
```

Each file includes:
- Duration and word count
- AI-generated summary
- Key themes and action items
- Full transcript (collapsible)

## Configuration

Settings are stored in:
- **Windows**: `%APPDATA%\Squelch\config.toml`
- **Linux**: `~/.config/squelch/config.toml`

You can edit this file directly or use the Options menu (F2).

## GPU Acceleration (Optional)

For faster transcription, install CUDA:

1. Install [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
2. Install [cuDNN](https://developer.nvidia.com/cudnn)
3. Squelch will automatically use GPU when available

## Troubleshooting

**No audio being captured?**
- Check Options (F2) → Audio Device
- Make sure audio is playing through the selected device

**Ollama not detected?**
- Run `ollama serve` in a terminal
- Check that a model is pulled: `ollama list`

**Transcription is slow?**
- Use smaller Whisper models in Options
- Enable GPU acceleration (see above)

**Cloud LLM not working?**
- Verify API key is set: `echo $OPENAI_API_KEY`
- Check the model name is correct

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## Acknowledgments

Built with [faster-whisper](https://github.com/guillaumekln/faster-whisper), [Textual](https://textual.textualize.io/), and [Ollama](https://ollama.ai).