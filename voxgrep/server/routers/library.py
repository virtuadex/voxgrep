"""
Library Management Routes
"""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..dependencies import get_session, get_vector_store, config, logger
from ..models import Video
from ...core import engine as search_engine
from ...utils.config import MEDIA_EXTENSIONS
from ..db import engine

router = APIRouter(prefix="/library", tags=["library"])

# Helper function (internal)
def _scan_path(path: str, session: Session) -> int:
    """Scans a path for media files and adds them to the database using absolute paths."""
    abs_target_path = os.path.abspath(path)
    if not os.path.exists(abs_target_path):
        os.makedirs(abs_target_path, exist_ok=True)
        
    count = 0
    for root, _, files in os.walk(abs_target_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in MEDIA_EXTENSIONS:
                full_path = os.path.join(root, file)
                existing = session.exec(select(Video).where(Video.path == full_path)).first()
                if not existing:
                    try:
                        stats = os.stat(full_path)
                        transcript_path = search_engine.find_transcript(full_path)
                        video = Video(
                            path=full_path,
                            filename=file,
                            size_bytes=stats.st_size,
                            created_at=stats.st_mtime,
                            has_transcript=transcript_path is not None,
                            transcript_path=transcript_path
                        )
                        session.add(video)
                        count += 1
                        logger.info(f"Added to library: {file}")
                    except OSError as e:
                        logger.error(f"Error accessing {full_path}: {e}")
                        
    session.commit()
    return count


@router.get("", response_model=List[Video])
def get_library(session: Session = Depends(get_session)):
    """Returns a list of all videos in the library."""
    videos = session.exec(select(Video)).all()
    return videos


@router.get("/{video_id}", response_model=Video)
def get_video(video_id: int, session: Session = Depends(get_session)):
    """Get a specific video by ID."""
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("/scan")
def scan_library(path: Optional[str] = None, session: Session = Depends(get_session)):
    """Scans a directory and adds new videos to the library."""
    target_path = path or config.downloads_dir
    added = _scan_path(target_path, session)
    return {"added": added, "path": target_path}


@router.delete("/{video_id}")
def delete_video(video_id: int, session: Session = Depends(get_session)):
    """Remove a video from the library (does not delete the file)."""
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Remove associated embeddings
    vector_store = get_vector_store()
    vector_store.remove_video(video_id, session)
    
    session.delete(video)
    session.commit()
    return {"status": "deleted", "video_id": video_id}
