"""
VoxGrep Utility Functions

Common utility functions used across the application.
"""
import os
import logging
from pathlib import Path
from typing import Optional, List, Union
from .config import SUBTITLE_EXTENSIONS, MEDIA_EXTENSIONS, VIDEO_EXTENSIONS, AUDIO_EXTENSIONS
from .exceptions import InvalidFileFormatError


logger = logging.getLogger(__name__)


# ============================================================================
# File Type Detection
# ============================================================================
def get_file_extension(filename: str) -> str:
    """Get the lowercase file extension without the dot."""
    return Path(filename).suffix.lower()


def is_video_file(filename: str) -> bool:
    """Check if a file is a video file based on extension."""
    return get_file_extension(filename) in VIDEO_EXTENSIONS


def is_audio_file(filename: str) -> bool:
    """Check if a file is an audio file based on extension."""
    return get_file_extension(filename) in AUDIO_EXTENSIONS


def is_media_file(filename: str) -> bool:
    """Check if a file is a media file (video or audio)."""
    return get_file_extension(filename) in MEDIA_EXTENSIONS


def is_subtitle_file(filename: str) -> bool:
    """Check if a file is a subtitle/transcript file."""
    return get_file_extension(filename) in SUBTITLE_EXTENSIONS


def get_media_type(filename: str) -> str:
    """
    Get the media type for a file.
    
    Returns:
        'video', 'audio', or 'unknown'
    """
    ext = get_file_extension(filename)
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    elif ext in AUDIO_EXTENSIONS:
        return 'audio'
    return 'unknown'


# ============================================================================
# Path Utilities
# ============================================================================
def ensure_absolute_path(path: Union[str, Path]) -> Path:
    """Ensure a path is absolute."""
    p = Path(path)
    return p.resolve() if not p.is_absolute() else p


def ensure_directory_exists(path: Union[str, Path]) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_base_filename(filepath: Union[str, Path]) -> str:
    """Get the filename without extension."""
    return Path(filepath).stem


def get_output_directory(output_path: Union[str, Path]) -> Path:
    """Get the directory for an output file, creating it if necessary."""
    output_dir = Path(output_path).parent
    if output_dir != Path('.'):
        ensure_directory_exists(output_dir)
    return output_dir


# ============================================================================
# File Validation
# ============================================================================
def validate_file_exists(filepath: Union[str, Path]) -> Path:
    """
    Validate that a file exists.
    
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    from .exceptions import FileNotFoundError as VoxGrepFileNotFoundError
    
    p = Path(filepath)
    if not p.exists():
        raise VoxGrepFileNotFoundError(f"File not found: {filepath}")
    if not p.is_file():
        raise VoxGrepFileNotFoundError(f"Path is not a file: {filepath}")
    return p


def validate_media_file(filepath: Union[str, Path]) -> Path:
    """
    Validate that a file exists and is a supported media file.
    
    Raises:
        FileNotFoundError: If the file doesn't exist
        InvalidFileFormatError: If the file format is not supported
    """
    p = validate_file_exists(filepath)
    if not is_media_file(str(p)):
        raise InvalidFileFormatError(
            f"Unsupported media format: {p.suffix}. "
            f"Supported formats: {', '.join(MEDIA_EXTENSIONS)}"
        )
    return p


# ============================================================================
# List Utilities
# ============================================================================
def ensure_list(value: Union[str, List[str]]) -> List[str]:
    """Ensure a value is a list."""
    if isinstance(value, str):
        return [value]
    return value


def flatten_list(nested_list: List[List]) -> List:
    """Flatten a nested list."""
    return [item for sublist in nested_list for item in sublist]


# ============================================================================
# String Utilities
# ============================================================================
def format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def format_file_size(bytes: int) -> str:
    """Format bytes as human-readable file size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"


# ============================================================================
# Logging Utilities
# ============================================================================
def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Setup a logger with consistent formatting.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    from .config import LOG_FORMAT, LOG_DATE_FORMAT
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Only add handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(handler)
    
    return logger
