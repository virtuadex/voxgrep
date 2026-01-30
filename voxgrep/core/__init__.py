"""
Core Logic Package
"""
from .logic import voxgrep, remove_overlaps, pad_and_sync
from .engine import search, find_transcript, parse_transcript, get_ngrams, SemanticModel
from .transcriber import transcribe, transcribe_whisper, transcribe_mlx
from .exporter import create_supercut
from .types import (
    SearchType,
    OutputMode,
    DeviceType,
    ExportStrategy,
    TranscriptionBackend,
    VoxGrepResult,
    TranscriptionResult,
    Segment,
)

__all__ = [
    # Core functions
    "voxgrep", "remove_overlaps", "pad_and_sync",
    "search", "find_transcript", "parse_transcript", "get_ngrams", "SemanticModel",
    "transcribe", "transcribe_whisper", "transcribe_mlx",
    "create_supercut",
    # Types
    "SearchType",
    "OutputMode",
    "DeviceType",
    "ExportStrategy",
    "TranscriptionBackend",
    "VoxGrepResult",
    "TranscriptionResult",
    "Segment",
]
