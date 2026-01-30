"""
VoxGrep Core Type Definitions

Provides enums, dataclasses, and type interfaces for the core library.
Centralizes type definitions to avoid circular imports between modules.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class SearchType(str, Enum):
    """Available search strategies."""
    SENTENCE = "sentence"
    FRAGMENT = "fragment"
    MASH = "mash"
    SEMANTIC = "semantic"

    @classmethod
    def from_string(cls, value: str) -> "SearchType":
        """Convert string to SearchType with fallback to SENTENCE."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.SENTENCE


class OutputMode(str, Enum):
    """Available output/export modes."""
    SUPERCUT = "supercut"
    INDIVIDUAL_CLIPS = "individual_clips"
    PLAYLIST_M3U = "m3u"
    PLAYLIST_EDL = "edl"
    XML = "xml"


class DeviceType(str, Enum):
    """Available transcription devices/backends."""
    CPU = "cpu"
    CUDA = "cuda"
    MLX = "mlx"
    MPS = "mps"

    @classmethod
    def from_string(cls, value: str) -> "DeviceType":
        """Convert string to DeviceType with fallback to CPU."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.CPU


class TranscriptionBackend(str, Enum):
    """Available transcription backends."""
    FASTER_WHISPER = "faster-whisper"
    MLX_WHISPER = "mlx-whisper"
    OPENAI_API = "openai-api"
    TRANSFORMERS = "transformers"


class ExportStrategy(str, Enum):
    """Export strategy based on input type and output format."""
    VIDEO = "video"
    AUDIO = "audio"


@dataclass
class Segment:
    """A single transcript segment with timing and content."""
    file: str
    start: float
    end: float
    content: str
    words: list[dict] = field(default_factory=list)
    score: Optional[float] = None  # For semantic search results

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = {
            "file": self.file,
            "start": self.start,
            "end": self.end,
            "content": self.content,
        }
        if self.words:
            d["words"] = self.words
        if self.score is not None:
            d["score"] = self.score
        return d


@dataclass
class VoxGrepResult:
    """
    Result from a voxgrep operation.

    Provides structured result data with backward compatibility via to_dict().
    """
    success: bool
    clips_count: int = 0
    supercut_duration: float = 0.0
    original_duration: float = 0.0
    time_saved: float = 0.0
    efficiency_percent: float = 0.0
    search_query: str = ""
    output_file: Optional[str] = None
    mode: str = "export"
    segments: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "success": self.success,
            "clips_count": self.clips_count,
            "supercut_duration": self.supercut_duration,
            "original_duration": self.original_duration,
            "time_saved": self.time_saved,
            "efficiency_percent": self.efficiency_percent,
            "search_query": self.search_query,
            "output_file": self.output_file,
            "mode": self.mode,
        }

    def __bool__(self) -> bool:
        """Allow result to be used in boolean context (True if successful)."""
        return self.success


@dataclass
class TranscriptionResult:
    """Result from transcription."""
    segments: list[dict]
    language: Optional[str] = None
    duration: Optional[float] = None
    backend: Optional[str] = None
