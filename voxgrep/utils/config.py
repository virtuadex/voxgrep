"""
VoxGrep Configuration Module

Centralizes all configuration constants and settings for the application.
"""
import os
from pathlib import Path
from pathlib import Path
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
MASH_PADDING = 0.05  # Micro-padding in seconds for word-level cuts (50ms)


# ============================================================================
# Transcription Defaults
# ============================================================================
DEFAULT_WHISPER_MODEL = "large-v3"
DEFAULT_MLX_MODEL = "mlx-community/whisper-large-v3-mlx"

# MLX model name mappings (short name -> HuggingFace repo)
MLX_MODEL_MAPPING = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large": "mlx-community/whisper-large-v3-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "large-v2": "mlx-community/whisper-large-v2-mlx",
    "distil-large-v3": "mlx-community/distil-whisper-large-v3",
}

def get_best_device() -> str:
    """Detect the best available device for transcription."""
    import platform
    try:
        # Check for Apple Silicon (MLX)
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            try:
                import mlx_whisper
                return "mlx"
            except ImportError:
                pass
        
        # Check for CUDA
        import torch
        if torch.cuda.is_available():
            return "cuda"
            
        # Check for MPS (Metal Performance Shaders) - though faster-whisper support varies
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            # faster-whisper doesn't support mps directly usually, but we check anyway
            # Keeping it safe: default to cpu if not MLX or CUDA for now
            pass
            
    except ImportError:
        pass
        
    return "cpu"

DEFAULT_DEVICE = get_best_device()
DEFAULT_COMPUTE_TYPE = "float16" if DEFAULT_DEVICE == "mlx" else "int8"


# ============================================================================
# Search Defaults
# ============================================================================
DEFAULT_SEARCH_TYPE = "sentence"
DEFAULT_SEMANTIC_THRESHOLD = 0.45
DEFAULT_SEMANTIC_MODEL = "all-MiniLM-L6-v2"

DEFAULT_IGNORED_WORDS = [
    "a", "o", "as", "os", "e", "é", "de", "do", "da", "dos", "das", 
    "em", "no", "na", "nos", "nas", "que", "para", "por", "com", 
    "um", "uma", "uns", "umas", "não", "se"
]


# ============================================================================
# Download Configuration
# ============================================================================
@dataclass
class DownloadConfig:
    """Configuration for yt-dlp downloads (YouTube, X/Twitter, etc.)."""
    # Cookie options for authenticated downloads (X/Twitter, age-restricted content)
    # Set to browser name to auto-extract: 'chrome', 'firefox', 'safari', 'edge', 'brave', 'opera', 'chromium'
    cookies_from_browser: str | None = "brave"
    # Or specify a Netscape-format cookies.txt file path
    cookies_file: str | None = None


# ============================================================================
# Server Configuration
# ============================================================================
@dataclass
class ServerConfig:
    """Configuration for the FastAPI server."""
    host: str = "127.0.0.1"
    port: int = 8000
    db_name: str = "voxgrep_library.db"
    downloads_dir: Path = field(default_factory=lambda: get_data_dir() / "downloads")
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    log_level: str = "INFO"
    download: DownloadConfig = field(default_factory=DownloadConfig)


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
