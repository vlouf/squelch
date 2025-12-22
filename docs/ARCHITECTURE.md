# Squelch Architecture

Technical documentation for developers and contributors.

## Overview

Squelch is a meeting transcription tool built with:
- **faster-whisper** for speech-to-text
- **Textual** for the terminal UI
- **Ollama/LiteLLM** for LLM features

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        TUI (Textual)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Transcript  │  │  Event Log  │  │   Response Panel    │  │
│  │    View     │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         Engine                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │    Audio     │  │  Transcriber │  │       LLM        │   │
│  │   Capture    │  │   Workers    │  │    Processor     │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│         │                  │                   │            │
│         ▼                  ▼                   ▼            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Session    │  │   Whisper    │  │  Ollama/LiteLLM  │   │
│  │    State     │  │   Models     │  │      APIs        │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### Audio Capture (`engine/audio/`)

Platform-specific loopback audio capture.

**Interface (`base.py`):**
```python
class AudioCaptureBase(ABC):
    @abstractmethod
    def start(self, callback: Callable[[np.ndarray], None]) -> None: ...
    
    @abstractmethod
    def stop(self) -> None: ...
    
    @staticmethod
    @abstractmethod
    def list_devices() -> list[dict]: ...
```

**Windows (`windows.py`):**
- Uses PyAudioWPatch for WASAPI loopback
- Captures audio from any output device
- Resamples to 16kHz mono for Whisper

**Linux (`linux.py`):**
- Uses sounddevice with PipeWire
- Creates a virtual monitor source
- Same 16kHz mono output

**Factory pattern:**
```python
# engine/audio/__init__.py
if sys.platform == "win32":
    from .windows import WindowsAudioCapture as AudioCapture
else:
    from .linux import LinuxAudioCapture as AudioCapture
```

### Transcription (`engine/transcriber.py`)

Dual-pass transcription using faster-whisper in separate processes.

**Why separate processes?**
- Whisper models can't be pickled for threading
- Process isolation prevents GIL contention
- Each worker loads its own model

**Architecture:**
```
Main Process                    Worker Processes
┌────────────┐                 ┌─────────────────┐
│            │  audio chunks   │  Fast Worker    │
│   TUI      │ ──────────────► │  (base model)   │
│            │                 │  6s chunks      │
│            │ ◄────────────── │                 │
│            │   transcripts   └─────────────────┘
│            │                 
│            │  audio chunks   ┌─────────────────┐
│            │ ──────────────► │  Slow Worker    │
│            │                 │  (small model)  │
│            │ ◄────────────── │  60s chunks     │
│            │   transcripts   └─────────────────┘
└────────────┘
```

**Chunk types (`types.py`):**
```python
class ChunkType(Enum):
    FAST = "fast"  # 6-second chunks
    SLOW = "slow"  # 60-second chunks

class TranscriptQuality(Enum):
    FAST = "fast"      # Quick but less accurate
    REFINED = "refined" # Slower but more accurate
```

**Worker communication:**
- `multiprocessing.Queue` for audio input
- `multiprocessing.Queue` for transcript output
- Poison pill pattern for shutdown

### Session State (`engine/session.py`)

Manages recording state and transcript segments.

```python
@dataclass
class TranscriptSegment:
    start_time: float
    end_time: float
    text: str
    quality: TranscriptQuality
    chunk_type: ChunkType

class Session:
    def start_recording(self) -> None
    def stop_recording(self) -> None
    def add_segment(self, segment: TranscriptSegment) -> None
    def get_transcript_text(self) -> str
    def get_recent_context(self, n: int) -> str
```

**Segment replacement logic:**

When a slow (refined) segment arrives, it replaces overlapping fast segments:
```python
def add_segment(self, segment: TranscriptSegment):
    if segment.quality == TranscriptQuality.REFINED:
        # Remove fast segments that overlap with this refined segment
        self._segments = [
            s for s in self._segments
            if not (s.quality == TranscriptQuality.FAST and 
                   self._overlaps(s, segment))
        ]
    self._segments.append(segment)
```

### LLM Integration (`engine/llm*.py`)

Factory pattern for multiple LLM providers.

**Factory (`llm.py`):**
```python
def create_llm_processor() -> OllamaProcessor | LiteLLMProcessor:
    if config.llm.provider == "ollama":
        return OllamaProcessor()
    else:
        return LiteLLMProcessor(model=config.llm.model)
```

**Ollama Processor (`llm_ollama.py`):**
- Uses Ollama's OpenAI-compatible API
- Auto-detects available models
- Local inference, no API key needed

**LiteLLM Processor (`llm_litellm.py`):**
- Wraps LiteLLM library
- Supports 100+ providers with unified interface
- API keys via environment variables

**Common interface:**
```python
class LLMProcessorProtocol:
    async def check_availability(self) -> bool
    async def ask(self, question: str, transcript: str) -> str
    def set_model(self, model: str) -> None
    @property
    def is_available(self) -> bool
    @property
    def model(self) -> str | None
```

### Configuration (`config.py`)

TOML-based configuration with hot-reload support.

**Structure:**
```python
@dataclass
class Config:
    audio: AudioConfig
    whisper: WhisperConfig
    output: OutputConfig
    llm: LLMConfig
    app: AppConfig
    
    def save(self) -> None  # Write to TOML
    
    @classmethod
    def load(cls) -> Config  # Read from TOML
```

**File locations:**
- Windows: `%APPDATA%\Squelch\config.toml`
- Linux: `~/.config/squelch/config.toml`

**Example TOML:**
```toml
[audio]
fast_chunk_duration = 6.0
slow_chunk_duration = 60.0

[whisper]
fast_model = "base"
slow_model = "small"
language = "en"

[llm]
provider = "ollama"
model = "llama3.1:8b"

[app]
theme = "textual-dark"
```

### TUI (`tui/`)

Textual-based terminal interface.

**Main App (`app.py`):**
- Manages UI layout and state
- Polls transcriber queues
- Handles keybindings and commands

**Key widgets:**
- `TranscriptView` — RichLog with segment coloring
- `EventLog` — Timestamped event display
- `ResponsePanel` — Collapsible LLM response area

**Modals:**
- `OptionsScreen` — Settings editor
- `AboutScreen` — Help and keybindings

**Command Palette:**
- Built-in Textual feature
- Custom commands via `SquelchCommands` provider
- Access to all themes

### Export (`export/markdown.py`)

Generates meeting summary documents.

**Output structure:**
```markdown
# Meeting Notes — Dec 22, 2025

**Duration**: 45 minutes | **Words**: 3,247

## Summary
[AI-generated overview]

## Key Themes
### Theme 1
- Point one
- Point two

## Action Items
- [ ] Task one
- [ ] Task two

<details>
<summary>Full Transcript (click to expand)</summary>

[00:00] First segment...
[00:06] ✓ Refined segment...

</details>
```

## Data Flow

### Recording Flow

```
1. User presses F5 (start recording)
2. Session.start_recording() called
3. AudioCapture.start() begins streaming
4. Audio callback receives chunks
5. Chunks routed to transcriber queues:
   - Every 6s → Fast queue
   - Every 60s → Slow queue
6. Workers process and return segments
7. TUI polls and displays results
8. User presses F5 (stop) or F10 (end)
```

### Q&A Flow

```
1. User types question, presses Enter
2. App gets recent transcript context
3. LLM processor called with question + context
4. Response displayed in ResponsePanel
5. History stored for export
```

### Summary Generation Flow

```
1. User presses F10 (end meeting)
2. Recording stops
3. Wait for pending slow transcriptions
4. Full transcript assembled
5. Summarizer.generate() called
6. MarkdownExporter creates file
7. File opened in default viewer
```

## Performance Considerations

### Memory

- Whisper models loaded per-worker (75MB - 3GB each)
- Audio buffer: ~1MB rolling window
- Transcript segments: minimal (text only)

### CPU/GPU

- Whisper inference is the bottleneck
- GPU (CUDA) provides 10-50x speedup
- Two workers = 2x model memory but parallel processing

### Latency

- Fast pass: ~1-2s after 6s chunk completes
- Slow pass: ~5-10s after 60s chunk completes
- LLM response: depends on model/provider

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=squelch

# Run specific test
pytest tests/test_session.py -v
```

## Future Architecture Considerations

**macOS Support:**
- Need CoreAudio implementation
- Similar pattern to Windows/Linux

**Streaming LLM:**
- Currently waits for full response
- Could stream tokens for better UX

**Multi-speaker:**
- Would require diarization model
- Significant complexity increase
