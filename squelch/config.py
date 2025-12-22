"""
Squelch configuration with TOML persistence.
"""

from dataclasses import dataclass, field
from pathlib import Path
import sys
import tomllib


# Platform-specific config directory
def get_config_dir() -> Path:
    """Get platform-appropriate config directory."""
    if sys.platform == "win32":
        # Windows: %APPDATA%/Squelch
        base = Path.home() / "AppData" / "Roaming"
    else:
        # Linux/macOS: ~/.config/squelch
        base = Path.home() / ".config"

    config_dir = base / "squelch"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get path to config file."""
    return get_config_dir() / "config.toml"


@dataclass
class AudioConfig:
    """Audio capture settings."""
    sample_rate: int = 16000  # Whisper expects 16kHz
    channels: int = 1         # Mono is fine for speech
    device_name: str | None = None  # None = use default

    # Dual-pass chunking
    fast_chunk_duration: float = 6.0   # Seconds per fast chunk
    slow_chunk_duration: float = 60.0  # Seconds per slow chunk


@dataclass
class WhisperConfig:
    """Whisper transcription settings."""
    fast_model: str = "base"    # Fast pass model
    slow_model: str = "small"   # Slow pass model

    device: str = "auto"        # auto, cpu, cuda
    compute_type: str = "auto"  # auto, int8, float16, float32
    language: str | None = "en" # None = auto-detect


@dataclass
class OutputConfig:
    """Output settings."""
    output_dir: Path = field(default_factory=lambda: Path.home() / "Documents" / "Squelch")


@dataclass
class LLMConfig:
    """LLM configuration."""
    endpoint: str = "http://localhost:11434/v1/chat/completions"
    model: str | None = None  # None = auto-detect
    max_tokens: int = 500
    temperature: float = 0.7
    context_segments: int = 20


@dataclass
class AppConfig:
    """Application UI settings."""
    theme: str = "textual-dark"


@dataclass
class Config:
    """Main configuration container."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    app: AppConfig = field(default_factory=AppConfig)

    def save(self) -> None:
        """Save configuration to TOML file."""
        config_path = get_config_path()

        # Build TOML content
        lines = ["# Squelch configuration", ""]

        # Audio section
        lines.append("[audio]")
        if self.audio.device_name:
            lines.append(f'device_name = "{self.audio.device_name}"')
        lines.append(f"fast_chunk_duration = {self.audio.fast_chunk_duration}")
        lines.append(f"slow_chunk_duration = {self.audio.slow_chunk_duration}")
        lines.append("")

        # Whisper section
        lines.append("[whisper]")
        lines.append(f'fast_model = "{self.whisper.fast_model}"')
        lines.append(f'slow_model = "{self.whisper.slow_model}"')
        if self.whisper.language:
            lines.append(f'language = "{self.whisper.language}"')
        else:
            lines.append('language = "auto"')
        lines.append(f'device = "{self.whisper.device}"')
        lines.append(f'compute_type = "{self.whisper.compute_type}"')
        lines.append("")

        # LLM section
        lines.append("[llm]")
        if self.llm.model:
            lines.append(f'model = "{self.llm.model}"')
        lines.append(f"context_segments = {self.llm.context_segments}")
        lines.append("")

        # Output section - use forward slashes for cross-platform compatibility
        lines.append("[output]")
        output_path = str(self.output.output_dir).replace("\\", "/")
        lines.append(f'output_dir = "{output_path}"')
        lines.append("")

        # App section
        lines.append("[app]")
        lines.append(f'theme = "{self.app.theme}"')
        lines.append("")

        config_path.write_text("\n".join(lines))

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from TOML file, or return defaults."""
        config_path = get_config_path()
        config = cls()

        if not config_path.exists():
            return config

        try:
            text = config_path.read_text()
            data = tomllib.loads(text)

            # Audio
            if "audio" in data:
                audio = data["audio"]
                if "device_name" in audio:
                    config.audio.device_name = audio["device_name"]
                if "fast_chunk_duration" in audio:
                    config.audio.fast_chunk_duration = float(audio["fast_chunk_duration"])
                if "slow_chunk_duration" in audio:
                    config.audio.slow_chunk_duration = float(audio["slow_chunk_duration"])

            # Whisper
            if "whisper" in data:
                whisper = data["whisper"]
                if "fast_model" in whisper:
                    config.whisper.fast_model = whisper["fast_model"]
                if "slow_model" in whisper:
                    config.whisper.slow_model = whisper["slow_model"]
                if "language" in whisper:
                    lang = whisper["language"]
                    config.whisper.language = None if lang == "auto" else lang
                if "device" in whisper:
                    config.whisper.device = whisper["device"]
                if "compute_type" in whisper:
                    config.whisper.compute_type = whisper["compute_type"]

            # LLM
            if "llm" in data:
                llm = data["llm"]
                if "model" in llm:
                    config.llm.model = llm["model"]
                if "context_segments" in llm:
                    config.llm.context_segments = int(llm["context_segments"])

            # Output
            if "output" in data:
                output = data["output"]
                if "output_dir" in output:
                    config.output.output_dir = Path(output["output_dir"])

            # App
            if "app" in data:
                app = data["app"]
                if "theme" in app:
                    config.app.theme = app["theme"]

        except Exception as e:
            # If config is corrupted, use defaults
            import sys
            print(f"Warning: Failed to load config: {e}", file=sys.stderr)

        return config


# Load config on import
config = Config.load()