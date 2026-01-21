__version__ = "3.0.0"

# Core modules (formats)
from . import formats as formats_module
# Expose individual format modules for backward compatibility if needed, 
# or prefer just importing 'formats' package
from .formats import vtt, srt, sphinx, fcpxml
# Utils package is available as .utils
from . import utils

# Transcription module
from .core import transcriber as transcribe

# Main voxgrep function
from .core.logic import (
    voxgrep,
    remove_overlaps,
    pad_and_sync,
)

# Search engine
from .core.engine import (
    search,
    find_transcript,
    parse_transcript,
    get_ngrams,
    SUB_EXTS,  # Legacy compatibility
)

# Exporter
from .core.exporter import (
    create_supercut,
    create_supercut_in_batches,
    export_individual_clips,
    export_m3u,
    export_mpv_edl,
    export_xml,
    cleanup_log_files,
)
# Note: BATCH_SIZE is better imported from utils.config directly if needed
from .utils.config import BATCH_SIZE

# Expose commonly used items from utils package
from .utils.config import (
    SUBTITLE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    MEDIA_EXTENSIONS,
)

from .utils.exceptions import (
    VoxGrepError,
    TranscriptNotFoundError,
    SearchError,
    NoResultsFoundError,
)

from .utils.helpers import (
    is_video_file,
    is_audio_file,
    is_media_file,
    validate_media_file,
    get_media_type,
)
