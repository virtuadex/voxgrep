"""
VoxGrep Database Models

SQLModel definitions for the VoxGrep library database.
"""

from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum


# ============================================================================
# Enums
# ============================================================================
class ExportStatus(str, Enum):
    """Status of an export job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TransitionType(str, Enum):
    """Types of video transitions for Phase 3."""
    CUT = "cut"  # Hard cut (default)
    CROSSFADE = "crossfade"
    FADE_TO_BLACK = "fade_to_black"
    DISSOLVE = "dissolve"


# ============================================================================
# Video Library Models
# ============================================================================
class VideoBase(SQLModel):
    """Base model for video metadata."""
    path: str = Field(index=True, unique=True)
    filename: str
    size_bytes: int
    duration: float = 0.0
    created_at: float
    has_transcript: bool = False
    transcript_path: str | None = None
    # Phase 2: Speaker diarization
    has_diarization: bool = False
    diarization_path: str | None = None
    # Phase 2: Indexing status
    is_indexed: bool = False
    indexed_at: float | None = None


class Video(VideoBase, table=True):
    """Video entity stored in the database."""
    id: int | None = Field(default=None, primary_key=True)
    
    # Relationships
    embeddings: list["Embedding"] = Relationship(back_populates="video")
    speakers: list["Speaker"] = Relationship(back_populates="video")


# ============================================================================
# Vector Search Models (Phase 2)
# ============================================================================
class Embedding(SQLModel, table=True):
    """
    Stores embeddings for transcript segments.
    Used for semantic search across the library.
    """
    id: int | None = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="video.id", index=True)
    segment_index: int  # Index in the transcript
    segment_start: float
    segment_end: float
    segment_content: str
    embedding_blob: bytes  # Serialized numpy array
    embedding_dim: int
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    
    # Relationship back to video
    video: Video | None = Relationship(back_populates="embeddings")


# ============================================================================
# Speaker Diarization Models (Phase 2)
# ============================================================================
class Speaker(SQLModel, table=True):
    """
    Represents a unique speaker detected in a video.
    """
    id: int | None = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="video.id", index=True)
    speaker_label: str  # e.g., "SPEAKER_00", "SPEAKER_01"
    display_name: str | None = None  # User-assigned name
    total_duration: float = 0.0  # Total speaking time in seconds
    segment_count: int = 0  # Number of segments
    
    # Relationship back to video
    video: Video | None = Relationship(back_populates="speakers")


class SpeakerSegment(SQLModel, table=True):
    """Individual time segment for a speaker."""
    id: int | None = Field(default=None, primary_key=True)
    speaker_id: int = Field(foreign_key="speaker.id", index=True)
    start: float
    end: float
    confidence: float = 1.0


# ============================================================================
# Export & Composition Models (Phase 3)
# ============================================================================
class ExportJob(SQLModel, table=True):
    """
    Tracks export jobs for supercut generation.
    """
    id: int | None = Field(default=None, primary_key=True)
    output_path: str
    status: ExportStatus = ExportStatus.PENDING
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    started_at: float | None = None
    completed_at: float | None = None
    error_message: str | None = None
    total_clips: int = 0
    processed_clips: int = 0
    
    # Composition settings
    transition_type: TransitionType = TransitionType.CUT
    transition_duration: float = 0.5  # seconds
    burn_subtitles: bool = False
    subtitle_style: str | None = None  # JSON string of subtitle styling


class Composition(SQLModel, table=True):
    """
    A saved composition (supercut project) that can be re-exported.
    """
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    
    # Settings
    transition_type: TransitionType = TransitionType.CUT
    transition_duration: float = 0.5
    burn_subtitles: bool = False


class CompositionClip(SQLModel, table=True):
    """
    Individual clip in a composition.
    """
    id: int | None = Field(default=None, primary_key=True)
    composition_id: int = Field(foreign_key="composition.id", index=True)
    video_id: int | None = Field(foreign_key="video.id")
    
    # Clip timing
    source_path: str
    start: float
    end: float
    order_index: int  # Position in the composition
    
    # Content
    content: str | None = None  # Transcript text
    
    # Per-clip settings (override composition defaults)
    transition_type: TransitionType | None = None
    transition_duration: float | None = None


# ============================================================================
# API Response Models (non-table)
# ============================================================================
class SearchResult(SQLModel):
    """Search result returned by the API."""
    file: str
    start: float
    end: float
    content: str
    score: float | None = None
    speaker: str | None = None  # Phase 2: Speaker label
    video_id: int | None = None


class VectorStats(SQLModel):
    """Statistics about the vector index."""
    total_embeddings: int
    indexed_videos: int
    embedding_dim: int
    model_name: str | None


class ExportProgress(SQLModel):
    """Progress update for an export job."""
    job_id: int
    status: ExportStatus
    progress: float  # 0.0 to 1.0
    processed_clips: int
    total_clips: int
    error_message: str | None = None


class TranscriptionModel(SQLModel):
    """Available transcription model info."""
    name: str
    backend: str  # "faster-whisper", "mlx", "openai"
    description: str | None = None
    is_available: bool
    requires_gpu: bool = False
