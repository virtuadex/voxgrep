"""
VoxGrep Speaker Diarization Module

Provides speaker identification and diarization for audio/video files.
Uses pyannote.audio for speaker diarization when available.
"""
import os
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from ..config import get_cache_dir
from ..utils import setup_logger

logger = setup_logger(__name__)

# Try to import pyannote
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False


class DiarizationPipeline:
    """Singleton for the speaker diarization pipeline."""
    _instance: Optional[Any] = None
    _auth_token: Optional[str] = None
    
    @classmethod
    def get_instance(cls, auth_token: Optional[str] = None) -> Any:
        """
        Get or create the diarization pipeline instance.
        
        Note: pyannote.audio requires a Hugging Face token with access to
        the pyannote/speaker-diarization model.
        """
        if not PYANNOTE_AVAILABLE:
            raise RuntimeError(
                "pyannote.audio is not installed. Install with: "
                "pip install pyannote.audio"
            )
        
        if cls._instance is None:
            token = auth_token or os.getenv("HF_TOKEN")
            if not token:
                raise RuntimeError(
                    "Hugging Face token required for pyannote.audio. "
                    "Set HF_TOKEN environment variable or pass auth_token."
                )
            
            logger.info("Loading speaker diarization pipeline...")
            cls._instance = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.0",
                use_auth_token=token
            )
            cls._auth_token = token
            logger.info("Diarization pipeline loaded successfully")
        
        return cls._instance
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if diarization is available."""
        return PYANNOTE_AVAILABLE


class SpeakerSegment:
    """Represents a segment of audio attributed to a specific speaker."""
    
    def __init__(
        self,
        speaker_id: str,
        start: float,
        end: float,
        confidence: float = 1.0
    ):
        self.speaker_id = speaker_id
        self.start = start
        self.end = end
        self.confidence = confidence
    
    def to_dict(self) -> dict:
        return {
            "speaker_id": self.speaker_id,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence
        }
    
    def overlaps(self, start: float, end: float) -> bool:
        """Check if this segment overlaps with a time range."""
        return self.start < end and self.end > start
    
    def overlap_duration(self, start: float, end: float) -> float:
        """Calculate overlap duration with a time range."""
        overlap_start = max(self.start, start)
        overlap_end = min(self.end, end)
        return max(0, overlap_end - overlap_start)


def diarize(
    audio_path: str,
    num_speakers: Optional[int] = None,
    min_speakers: int = 1,
    max_speakers: int = 10,
    auth_token: Optional[str] = None
) -> List[SpeakerSegment]:
    """
    Perform speaker diarization on an audio/video file.
    
    Args:
        audio_path: Path to the audio or video file
        num_speakers: Exact number of speakers (if known)
        min_speakers: Minimum expected speakers
        max_speakers: Maximum expected speakers
        auth_token: Hugging Face auth token
        
    Returns:
        List of SpeakerSegment objects
    """
    if not PYANNOTE_AVAILABLE:
        logger.warning("Speaker diarization not available")
        return []
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    pipeline = DiarizationPipeline.get_instance(auth_token)
    
    logger.info(f"Running speaker diarization on {audio_path}")
    
    # Configure pipeline parameters
    params = {}
    if num_speakers:
        params["num_speakers"] = num_speakers
    else:
        params["min_speakers"] = min_speakers
        params["max_speakers"] = max_speakers
    
    # Run diarization
    diarization = pipeline(audio_path, **params)
    
    # Convert to SpeakerSegments
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(SpeakerSegment(
            speaker_id=speaker,
            start=turn.start,
            end=turn.end
        ))
    
    logger.info(f"Found {len(segments)} speaker segments")
    return segments


def assign_speakers_to_transcript(
    transcript: List[dict],
    speaker_segments: List[SpeakerSegment]
) -> List[dict]:
    """
    Assign speaker labels to transcript segments based on diarization.
    
    Args:
        transcript: List of transcript segments with 'start' and 'end' keys
        speaker_segments: List of SpeakerSegment objects from diarization
        
    Returns:
        Transcript with 'speaker' field added to each segment
    """
    result = []
    
    for seg in transcript:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        
        # Find the speaker with most overlap
        best_speaker = None
        best_overlap = 0
        
        for speaker_seg in speaker_segments:
            if speaker_seg.overlaps(seg_start, seg_end):
                overlap = speaker_seg.overlap_duration(seg_start, seg_end)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = speaker_seg.speaker_id
        
        # Create new segment with speaker info
        new_seg = seg.copy()
        new_seg["speaker"] = best_speaker or "UNKNOWN"
        result.append(new_seg)
    
    return result


def get_diarization_cache_path(video_path: str) -> Path:
    """Get the cache path for diarization results."""
    import hashlib
    video_hash = hashlib.md5(video_path.encode()).hexdigest()[:16]
    return get_cache_dir() / "diarization" / f"{video_hash}.json"


def save_diarization(video_path: str, segments: List[SpeakerSegment]) -> None:
    """Save diarization results to cache."""
    import json
    cache_path = get_diarization_cache_path(video_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({
            "video_path": video_path,
            "segments": [s.to_dict() for s in segments]
        }, f)
    
    logger.debug(f"Saved diarization cache: {cache_path}")


def load_diarization(video_path: str) -> Optional[List[SpeakerSegment]]:
    """Load cached diarization results."""
    import json
    cache_path = get_diarization_cache_path(video_path)
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return [
            SpeakerSegment(**seg) for seg in data.get("segments", [])
        ]
    except Exception as e:
        logger.warning(f"Failed to load diarization cache: {e}")
        return None


def diarize_cached(
    audio_path: str,
    num_speakers: Optional[int] = None,
    force: bool = False,
    **kwargs
) -> List[SpeakerSegment]:
    """
    Perform speaker diarization with caching.
    
    Args:
        audio_path: Path to the audio or video file
        num_speakers: Exact number of speakers (if known)
        force: If True, re-run diarization even if cached
        **kwargs: Additional arguments passed to diarize()
        
    Returns:
        List of SpeakerSegment objects
    """
    if not force:
        cached = load_diarization(audio_path)
        if cached is not None:
            logger.info(f"Using cached diarization for {audio_path}")
            return cached
    
    segments = diarize(audio_path, num_speakers=num_speakers, **kwargs)
    save_diarization(audio_path, segments)
    return segments
