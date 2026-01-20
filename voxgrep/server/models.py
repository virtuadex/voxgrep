"""
VoxGrep Database Models

SQLModel definitions for the VoxGrep library database.
"""
from typing import Optional, List
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
    transcript_path: Optional[str] = None
    # Phase 2: Speaker diarization
    has_diarization: bool = False
    diarization_path: Optional[str] = None
    # Phase 2: Indexing status
    is_indexed: bool = False
    indexed_at: Optional[float] = None


class Video(VideoBase, table=True):
    """Video entity stored in the database."""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    embeddings: List["Embedding"] = Relationship(back_populates="video")
    speakers: List["Speaker"] = Relationship(back_populates="video")


# ============================================================================
# Vector Search Models (Phase 2)
# ============================================================================
class Embedding(SQLModel, table=True):
    """
    Stores embeddings for transcript segments.
    Used for semantic search across the library.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="video.id", index=True)
    segment_index: int  # Index in the transcript
    segment_start: float
    segment_end: float
    segment_content: str
    embedding_blob: bytes  # Serialized numpy array
    embedding_dim: int
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    
    # Relationship back to video
    video: Optional[Video] = Relationship(back_populates="embeddings")


# ============================================================================
# Speaker Diarization Models (Phase 2)
# ============================================================================
class Speaker(SQLModel, table=True):
    """
    Represents a unique speaker detected in a video.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="video.id", index=True)
    speaker_label: str  # e.g., "SPEAKER_00", "SPEAKER_01"
    display_name: Optional[str] = None  # User-assigned name
    total_duration: float = 0.0  # Total speaking time in seconds
    segment_count: int = 0  # Number of segments
    
    # Relationship back to video
    video: Optional[Video] = Relationship(back_populates="speakers")


class SpeakerSegment(SQLModel, table=True):
    """Individual time segment for a speaker."""
    id: Optional[int] = Field(default=None, primary_key=True)
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
    id: Optional[int] = Field(default=None, primary_key=True)
    output_path: str
    status: ExportStatus = ExportStatus.PENDING
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    total_clips: int = 0
    processed_clips: int = 0
    
    # Composition settings
    transition_type: TransitionType = TransitionType.CUT
    transition_duration: float = 0.5  # seconds
    burn_subtitles: bool = False
    subtitle_style: Optional[str] = None  # JSON string of subtitle styling


class Composition(SQLModel, table=True):
    """
    A saved composition (supercut project) that can be re-exported.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
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
    id: Optional[int] = Field(default=None, primary_key=True)
    composition_id: int = Field(foreign_key="composition.id", index=True)
    video_id: Optional[int] = Field(foreign_key="video.id")
    
    # Clip timing
    source_path: str
    start: float
    end: float
    order_index: int  # Position in the composition
    
    # Content
    content: Optional[str] = None  # Transcript text
    
    # Per-clip settings (override composition defaults)
    transition_type: Optional[TransitionType] = None
    transition_duration: Optional[float] = None


# ============================================================================
# API Response Models (non-table)
# ============================================================================
class SearchResult(SQLModel):
    """Search result returned by the API."""
    file: str
    start: float
    end: float
    content: str
    score: Optional[float] = None
    speaker: Optional[str] = None  # Phase 2: Speaker label
    video_id: Optional[int] = None


class VectorStats(SQLModel):
    """Statistics about the vector index."""
    total_embeddings: int
    indexed_videos: int
    embedding_dim: int
    model_name: Optional[str]


class ExportProgress(SQLModel):
    """Progress update for an export job."""
    job_id: int
    status: ExportStatus
    progress: float  # 0.0 to 1.0
    processed_clips: int
    total_clips: int
    error_message: Optional[str] = None


class TranscriptionModel(SQLModel):
    """Available transcription model info."""
    name: str
    backend: str  # "faster-whisper", "mlx", "openai"
    description: Optional[str] = None
    is_available: bool
    requires_gpu: bool = False
