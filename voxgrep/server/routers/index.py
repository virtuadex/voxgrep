"""
Indexing Routes
"""
import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select, Session as DbSession

from ..dependencies import get_session, get_vector_store, features, logger
from ..models import Video, VectorStats
from ...core import engine as search_engine
from ..db import engine

router = APIRouter(prefix="/index", tags=["indexing"])

@router.post("/{video_id}")
def index_video(
    video_id: int, 
    force: bool = False,
    session: Session = Depends(get_session)
):
    """Index a video for semantic search."""
    if not features.enable_semantic_search:
        raise HTTPException(status_code=400, detail="Semantic search is disabled")
    
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.has_transcript:
        raise HTTPException(status_code=400, detail="Video has no transcript")
    
    # Load transcript
    transcript = search_engine.parse_transcript(video.path)
    if not transcript:
        raise HTTPException(status_code=400, detail="Could not parse transcript")
    
    # Index
    vector_store = get_vector_store()
    count = vector_store.index_video(video_id, transcript, session, force=force)
    
    # Update video record
    video.is_indexed = True
    video.indexed_at = time.time()
    session.add(video)
    session.commit()
    
    return {"status": "indexed", "video_id": video_id, "segments": count}


@router.post("/all")
def index_all_videos(
    force: bool = False,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_session)
):
    """Index all videos in the library for semantic search."""
    if not features.enable_semantic_search:
        raise HTTPException(status_code=400, detail="Semantic search is disabled")
    
    videos = session.exec(select(Video).where(Video.has_transcript == True)).all()
    
    def run_indexing():
        with DbSession(engine) as bg_session:
            vector_store = get_vector_store()
            indexed = 0
            for video in videos:
                try:
                    if not force and video.is_indexed:
                        continue
                    
                    transcript = search_engine.parse_transcript(video.path)
                    if transcript:
                        vector_store.index_video(video.id, transcript, bg_session, force=force)
                        video.is_indexed = True
                        video.indexed_at = time.time()
                        bg_session.add(video)
                        indexed += 1
                except Exception as e:
                    logger.error(f"Failed to index video {video.id}: {e}")
            
            bg_session.commit()
            logger.info(f"Indexed {indexed} videos")
    
    background_tasks.add_task(run_indexing)
    return {"status": "started", "total_videos": len(videos)}


@router.get("/stats", response_model=VectorStats)
def get_index_stats(session: Session = Depends(get_session)):
    """Get statistics about the vector index."""
    vector_store = get_vector_store()
    stats = vector_store.get_stats(session)
    return VectorStats(**stats)
