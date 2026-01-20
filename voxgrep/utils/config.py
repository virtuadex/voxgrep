"""
VoxGrep Configuration Module

Centralizes all configuration constants and settings for the application.
"""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


# ============================================================================
# File Extensions
# ============================================================================
SUBTITLE_EXTENSIONS = [".json", ".vtt", ".srt", ".transcript"]
VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"]
AUDIO_EXTENSIONS = [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"]
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS + AUDIO_EXTENSIONS


# ============================================================================
# Processing Constants
# ============================================================================
BATCH_SIZE = 20  # Number of clips to process in a batch for large supercuts
MAX_CHARS = 36  # Maximum characters for display/formatting
DEFAULT_PADDING = 0.3  # Default padding in seconds for fragment/mash searches


# ============================================================================
# Transcription Defaults
# ============================================================================
DEFAULT_WHISPER_MODEL = "large-v3"
DEFAULT_MLX_MODEL = "mlx-community/whisper-large-v3-mlx"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"


# ============================================================================
# Search Defaults
# ============================================================================
DEFAULT_SEARCH_TYPE = "sentence"
DEFAULT_SEMANTIC_THRESHOLD = 0.45
DEFAULT_SEMANTIC_MODEL = "all-MiniLM-L6-v2"


# ============================================================================
# Server Configuration
# ============================================================================
@dataclass
class ServerConfig:
    """Configuration for the FastAPI server."""
    host: str = "127.0.0.1"
    port: int = 8000
    db_name: str = "voxgrep_library.db"
    downloads_dir: str = "downloads"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    log_level: str = "INFO"


# ============================================================================
# Paths
# ============================================================================
def get_data_dir() -> Path:
    """Get the data directory for VoxGrep (for database, cache, etc.)."""
    if os.getenv("VOXGREP_DATA_DIR"):
        return Path(os.getenv("VOXGREP_DATA_DIR"))
    
    # Use XDG_DATA_HOME on Linux/Mac, LOCALAPPDATA on Windows
    if os.name == "posix":
        base = os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    else:
        base = os.getenv("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
    
    data_dir = Path(base) / "voxgrep"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_cache_dir() -> Path:
    """Get the cache directory for VoxGrep (for embeddings, models, etc.)."""
    if os.getenv("VOXGREP_CACHE_DIR"):
        return Path(os.getenv("VOXGREP_CACHE_DIR"))
    
    # Use XDG_CACHE_HOME on Linux/Mac, TEMP on Windows
    if os.name == "posix":
        base = os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    else:
        base = os.getenv("TEMP", os.path.expanduser("~/AppData/Local/Temp"))
    
    cache_dir = Path(base) / "voxgrep"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


# ============================================================================
# Logging Configuration
# ============================================================================
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================================
# Feature Flags
# ============================================================================
@dataclass
class FeatureFlags:
    """Feature flags for experimental or optional features."""
    enable_semantic_search: bool = True
    enable_mlx_transcription: bool = True
    enable_gpu_acceleration: bool = True
    enable_speaker_diarization: bool = False  # Future feature
    enable_auto_indexing: bool = True
