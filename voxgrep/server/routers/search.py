"""
Search and Analysis Routes
"""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..dependencies import get_session, get_vector_store, features, logger
from ..models import SearchResult, Video
from ...core import engine as search_engine
from ...utils.config import MEDIA_EXTENSIONS, DEFAULT_SEARCH_TYPE

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
