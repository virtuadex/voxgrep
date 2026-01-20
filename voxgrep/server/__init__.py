"""
VoxGrep Server Package

FastAPI service for the VoxGrep desktop application.
"""
from .app import app
from .db import engine, create_db_and_tables, get_session
from .models import (
    Video, SearchResult, Embedding, Speaker, SpeakerSegment,
    ExportJob, Composition, CompositionClip, VectorStats,
    ExportProgress, TransitionType, ExportStatus
)
from .vector_store import get_vector_store, VectorStore, EmbeddingModel
from .multi_model import get_model_manager, ModelManager, TranscriptionBackend
from .transitions import (
    concatenate_with_transitions, 
    concatenate_with_transitions_batched,
    TransitionType as TransType
)
from .subtitles import (
    SubtitleStyle, 
    burn_subtitles_on_segments,
    PRESET_STYLES
)

__all__ = [
    # Core
    "app",
    "engine",
    "create_db_and_tables",
    "get_session",
    # Models
    "Video",
    "SearchResult",
    "Embedding",
    "Speaker",
    "SpeakerSegment",
    "ExportJob",
    "Composition",
    "CompositionClip",
    "VectorStats",
    "ExportProgress",
    "TransitionType",
    "ExportStatus",
    # Vector Store
    "get_vector_store",
    "VectorStore",
    "EmbeddingModel",
    # Multi-Model
    "get_model_manager",
    "ModelManager",
    "TranscriptionBackend",
    # Transitions
    "concatenate_with_transitions",
    "concatenate_with_transitions_batched",
    "TransType",
    # Subtitles
    "SubtitleStyle",
    "burn_subtitles_on_segments",
    "PRESET_STYLES",
]
