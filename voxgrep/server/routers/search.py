"""
Search and Analysis Routes
"""
import os
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..dependencies import get_session, get_vector_store, features, logger
from ..models import SearchResult, Video
from ...core import engine as search_engine
from ...utils.config import MEDIA_EXTENSIONS, DEFAULT_SEARCH_TYPE

router = APIRouter(tags=["search"])

@router.get("/search", response_model=list[SearchResult])
def search(
    query: str, 
    type: str = DEFAULT_SEARCH_TYPE, 
    threshold: float = 0.45,
    exact_match: bool = False,
    video_ids: str | None = None,
    session: Session = Depends(get_session)
):
    """
    Searches across all videos in the library.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
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

    if not files:
        return []

    try:
        results = []
        
        # 1. Semantic Search (Vector Store)
        if type == "semantic" and features.enable_semantic_search:
            vector_store = get_vector_store()
            start_time = os.times()
            semantic_results = vector_store.search(
                query, session, threshold=threshold, video_ids=target_video_ids
            )
            return [SearchResult(**r) for r in semantic_results]
        
        # 2. Optimized Database Search (for Sentence Search)
        # Only works if search type is sentence
        db_video_ids = set()
        if type == "sentence":
            # Find which videos are indexed (have embeddings)
            # If target_video_ids is set, filter by that
            stmt = select(Embedding).where(Embedding.segment_content.contains(query))
            if target_video_ids:
                stmt = stmt.where(Embedding.video_id.in_(target_video_ids))
            
            # Execute DB search
            db_segments = session.exec(stmt).all()
            
            for seg in db_segments:
                if seg.video:
                    results.append(SearchResult(
                        file=seg.video.path,
                        start=seg.segment_start,
                        end=seg.segment_end,
                        content=seg.segment_content,
                        video_id=seg.video_id
                    ))
                    db_video_ids.add(seg.video_id)
            
            # If we found matches in DB, we only need to search files that were NOT in our "indexed" set
            # But wait: "indexed" means "has embeddings". A video might be indexed but contain no matches.
            # So we need to know which videos ARE indexed, regardless of matches.
            pass

        # 3. File-System Search (Fallback & Unindexed)
        # Determine which files need to be searched on disk
        # We search on disk if:
        #  a) Search type is NOT sentence (e.g. fragment, mash)
        #  b) Video is NOT indexed in DB (no embeddings)
        
        # Get list of indexed video IDs
        indexed_query = select(Video.id).where(Video.is_indexed == True)
        if target_video_ids:
            indexed_query = indexed_query.where(Video.id.in_(target_video_ids))
        indexed_ids = set(session.exec(indexed_query).all())
        
        # Filter files: keep only those NOT in indexed_ids (unless type != sentence)
        files_to_scan = []
        for v in videos:
            # If we already searched via DB (type=sentence AND is_indexed), skip disk scan
            if type == "sentence" and v.is_indexed:
                continue
            files_to_scan.append(v.path)

        if files_to_scan:
            logger.info(f"Scanning {len(files_to_scan)} files from disk (fallback/unindexed)...")
            disk_segments = search_engine.search(files_to_scan, query, type, threshold=threshold, exact_match=exact_match)
            for s in disk_segments:
                results.append(SearchResult(
                    file=s["file"],
                    start=s["start"],
                    end=s["end"],
                    content=s["content"],
                    score=s.get("score")
                ))
        
        # Deduplicate results if necessary (though our sets shouldn't overlap)
        return sorted(results, key=lambda x: x.start)

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
