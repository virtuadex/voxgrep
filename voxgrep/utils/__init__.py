"""
Utilities package for VoxGrep.

This package contains helper functions, configuration, preferences, and exceptions.
"""

# Import from helpers (formerly utils.py)
from .helpers import (
    setup_logger,
    ensure_list,
    ensure_directory_exists,
    is_video_file,
    is_audio_file,
    is_media_file,
    validate_media_file,
    get_media_type,
)

# Import from config
from .config import (
    SUBTITLE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    MEDIA_EXTENSIONS,
    DEFAULT_PADDING,
    BATCH_SIZE,
    DEFAULT_SEARCH_TYPE,
    ServerConfig,
    FeatureFlags,
)

# Import from exceptions
from .exceptions import (
    VoxGrepError,
    TranscriptNotFoundError,
    SearchError,
    NoResultsFoundError,
    ExportError,
    TranscriptionError,
    DiarizationError,
)

# Import from prefs
from .prefs import (
    get_pref,
    set_pref,
)

__all__ = [
    # Helpers
    "setup_logger",
    "ensure_list",
    "ensure_directory_exists",
    "is_video_file",
    "is_audio_file",
    "is_media_file",
    "validate_media_file",
    "get_media_type",
    # Config
    "SUBTITLE_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "MEDIA_EXTENSIONS",
    "DEFAULT_PADDING",
    "BATCH_SIZE",
    "DEFAULT_SEARCH_TYPE",
    "ServerConfig",
    "FeatureFlags",
    # Exceptions
    "VoxGrepError",
    "TranscriptNotFoundError",
    "SearchError",
    "NoResultsFoundError",
    "ExportError",
    "TranscriptionError",
    "DiarizationError",
    # Prefs
    "get_pref",
    "set_pref",
]
