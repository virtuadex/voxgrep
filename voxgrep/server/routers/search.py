"""
Search, Indexing, and Analysis Routes
"""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select

from ..dependencies import get_session, get_vector_store, features, logger
from ..models import SearchResult, Video, Speaker, VectorStats
from ...core import engine as search_engine
from ...utils.config import MEDIA_EXTENSIONS, DEFAULT_SEARCH_TYPE
from ..db import engine, Session as DbSession

router = APIRouter(tags=["search"])

@router.get("/search", response_model=List[SearchResult])
def search(
    query: str, 
    type: str = DEFAULT_SEARCH_TYPE, 
    threshold: float = 0.45,
    video_ids: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Searches across all videos in the library.
    """
    # Parse video_ids if provided
    target_video_ids = None
    if video_ids:
        try:
            target_video_ids = [int(vid.strip()) for vid in video_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid video_ids format")
    
    # Get files to search
    if target_video_ids:
        videos = session.exec(
            select(Video).where(Video.id.in_(target_video_ids))
        ).all()
    else:
        videos = session.exec(select(Video)).all()
    
    files = [v.path for v in videos]
    
    if not files:
        return []

    try:
        # Use vector store for semantic search
        if type == "semantic" and features.enable_semantic_search:
            vector_store = get_vector_store()
            results = vector_store.search(
                query, session, threshold=threshold, video_ids=target_video_ids
            )
            return [SearchResult(**r) for r in results]
        
        # Use standard search engine
        segments = search_engine.search(files, query, type, threshold=threshold)
        results = []
        for s in segments:
            results.append(SearchResult(
                file=s["file"],
                start=s["start"],
                end=s["end"],
                content=s["content"],
                score=s.get("score")
            ))
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ngrams")
def get_ngrams(path: str, n: int = 1):
    """Returns n-grams for indexed videos in the given path."""
    files_to_search = []
    
    abs_path = os.path.abspath(path)
    if os.path.isdir(abs_path):
        for root, _, files in os.walk(abs_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in MEDIA_EXTENSIONS:
                    full_path = os.path.join(root, file)
                    if search_engine.find_transcript(full_path):
                        files_to_search.append(full_path)
    else:
        if search_engine.find_transcript(abs_path):
            files_to_search = [abs_path]
            
    if not files_to_search:
        return []

    try:
        from collections import Counter
        grams = search_engine.get_ngrams(files_to_search, n)
        most_common = Counter(grams).most_common(100)
        
        results = []
        for ngram, count in most_common:
            results.append({"ngram": " ".join(ngram), "count": count})
            
        return results
    except Exception as e:
        logger.error(f"N-gram extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Indexing routes
index_router = APIRouter(prefix="/index", tags=["indexing"])

@index_router.post("/{video_id}")
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
    import time
    video.indexed_at = time.time()
    session.add(video)
    session.commit()
    
    return {"status": "indexed", "video_id": video_id, "segments": count}


@index_router.post("/all") # Note: original was /index/all, this mounts to /index/all if included with /index prefix
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
                        import time
                        video.indexed_at = time.time()
                        bg_session.add(video)
                        indexed += 1
                except Exception as e:
                    logger.error(f"Failed to index video {video.id}: {e}")
            
            bg_session.commit()
            logger.info(f"Indexed {indexed} videos")
    
    background_tasks.add_task(run_indexing)
    return {"status": "started", "total_videos": len(videos)}


@index_router.get("/stats", response_model=VectorStats)
def get_index_stats(session: Session = Depends(get_session)):
    """Get statistics about the vector index."""
    vector_store = get_vector_store()
    stats = vector_store.get_stats(session)
    return VectorStats(**stats)


# Diarization/Speakers routes
speaker_router = APIRouter(tags=["speakers"])

@speaker_router.post("/diarize/{video_id}")
def diarize_video(
    video_id: int,
    num_speakers: Optional[int] = None,
    force: bool = False,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_session)
):
    """Run speaker diarization on a video."""
    if not features.enable_speaker_diarization:
        raise HTTPException(status_code=400, detail="Speaker diarization is disabled")
    
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    def run_diarization():
        try:
            from ..diarization import diarize_cached
            
            segments = diarize_cached(video.path, num_speakers=num_speakers, force=force)
            
            # Update database
            with DbSession(engine) as bg_session:
                vid = bg_session.get(Video, video_id)
                vid.has_diarization = True
                bg_session.add(vid)
                
                # Store speakers
                speaker_map = {}
                for seg in segments:
                    if seg.speaker_id not in speaker_map:
                        speaker_map[seg.speaker_id] = {
                            "duration": 0,
                            "count": 0
                        }
                    speaker_map[seg.speaker_id]["duration"] += seg.end - seg.start
                    speaker_map[seg.speaker_id]["count"] += 1
                
                for speaker_id, stats in speaker_map.items():
                    speaker = Speaker(
                        video_id=video_id,
                        speaker_label=speaker_id,
                        total_duration=stats["duration"],
                        segment_count=stats["count"]
                    )
                    bg_session.add(speaker)
                
                bg_session.commit()
            
            logger.info(f"Diarization completed for video {video_id}")
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
    
    background_tasks.add_task(run_diarization)
    return {"status": "started", "video_id": video_id}


@speaker_router.get("/speakers/{video_id}", response_model=List[Speaker])
def get_video_speakers(video_id: int, session: Session = Depends(get_session)):
    """Get speakers detected in a video."""
    speakers = session.exec(
        select(Speaker).where(Speaker.video_id == video_id)
    ).all()
    return speakers
