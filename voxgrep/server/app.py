"""
VoxGrep FastAPI Service

Main API server for the VoxGrep desktop application.
Provides endpoints for library management, search, transcription, and export.

Phase 1: Core API (library, search, download, export)
Phase 2: Semantic search, vector indexing, speaker diarization
Phase 3: Transitions, subtitle burning, multi-model support
"""
import os
import sys
import subprocess
import logging
import threading
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from .db import engine, create_db_and_tables, get_session
from .models import (
    Video, SearchResult, Embedding, Speaker, ExportJob, 
    Composition, CompositionClip, VectorStats, ExportProgress,
    TransitionType, ExportStatus
)
from .vector_store import get_vector_store, EmbeddingModel, TRANSFORMERS_AVAILABLE
from .multi_model import get_model_manager, TranscriptionBackend
from .transitions import concatenate_with_transitions, TransitionType as TransType
from .subtitles import SubtitleStyle, burn_subtitles_on_segments, PRESET_STYLES
from .. import voxgrep, transcribe, search_engine
from ..config import ServerConfig, MEDIA_EXTENSIONS, DEFAULT_SEARCH_TYPE, FeatureFlags
from ..utils import setup_logger, ensure_directory_exists, validate_media_file

# Use ServerConfig defaults
config = ServerConfig()
features = FeatureFlags()

# Setup logger
logger = setup_logger("voxgrep.server", level=config.log_level)

app = FastAPI(
    title="VoxGrep Service",
    version="0.3.0",
    description="VoxGrep API - Search through video dialog and create supercuts"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Startup & Lifecycle
# ============================================================================
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # Auto-scan downloads folder on startup
    with Session(engine) as session:
        _scan_path(config.downloads_dir, session)
    
    # Pre-warm the semantic model in a background thread
    if features.enable_semantic_search:
        def pre_load_model():
            try:
                logger.info("Pre-loading semantic model...")
                EmbeddingModel.get_instance()
                logger.info("Semantic model loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to pre-load semantic model: {e}")
        
        threading.Thread(target=pre_load_model, daemon=True).start()
            
    logger.info(f"VoxGrep Server v0.3.0 started. Database initialized.")


# ============================================================================
# Helper Functions
# ============================================================================
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


# ============================================================================
# Phase 1: Core API Endpoints
# ============================================================================
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.3.0",
        "features": {
            "semantic_search": features.enable_semantic_search and TRANSFORMERS_AVAILABLE,
            "mlx_transcription": features.enable_mlx_transcription,
            "speaker_diarization": features.enable_speaker_diarization
        }
    }


@app.get("/library", response_model=List[Video])
def get_library(session: Session = Depends(get_session)):
    """Returns a list of all videos in the library."""
    videos = session.exec(select(Video)).all()
    return videos


@app.get("/library/{video_id}", response_model=Video)
def get_video(video_id: int, session: Session = Depends(get_session)):
    """Get a specific video by ID."""
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@app.post("/library/scan")
def scan_library(path: Optional[str] = None, session: Session = Depends(get_session)):
    """Scans a directory and adds new videos to the library."""
    target_path = path or config.downloads_dir
    added = _scan_path(target_path, session)
    return {"added": added, "path": target_path}


@app.delete("/library/{video_id}")
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


@app.post("/download")
def download_video(
    url: str, 
    output_dir: Optional[str] = None, 
    device: str = "auto",
    background_tasks: BackgroundTasks = None
):
    """Downloads a video from a URL using yt-dlp and transcribes it."""
    target_dir = os.path.abspath(output_dir or config.downloads_dir)
    ensure_directory_exists(target_dir)

    def run_download_and_transcribe():
        try:
            logger.info(f"Downloading video from {url} to {target_dir}")
            
            cmd = [
                "yt-dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
                "--merge-output-format", "mp4",
                "-o", f"{target_dir}/%(title)s.%(ext)s",
                "--print", "after_move:filepath",
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            filepath = result.stdout.strip().split('\n')[-1]
            
            if not os.path.exists(filepath):
                logger.error(f"yt-dlp reported success but file not found at {filepath}")
                return

            logger.info(f"Successfully downloaded: {filepath}")

            # Transcribe using model manager for auto backend selection
            model_mgr = get_model_manager()
            backend = None
            if device == "mlx":
                backend = TranscriptionBackend.MLX_WHISPER
            elif device == "cpu":
                backend = TranscriptionBackend.FASTER_WHISPER
            
            trans_result = model_mgr.transcribe(filepath, backend=backend)
            
            # Save transcript
            import json
            transcript_path = os.path.splitext(filepath)[0] + ".json"
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(trans_result.segments, f)
            
            # Scan to update DB and index
            with Session(engine) as session:
                _scan_path(target_dir, session)
                
                # Auto-index for semantic search
                if features.enable_auto_indexing and features.enable_semantic_search:
                    video = session.exec(
                        select(Video).where(Video.path == filepath)
                    ).first()
                    if video:
                        vector_store = get_vector_store()
                        vector_store.index_video(video.id, trans_result.segments, session)
                
        except Exception as e:
            logger.error(f"Download or transcription failed: {e}")

    background_tasks.add_task(run_download_and_transcribe)
    return {"status": "started", "url": url}


@app.post("/add-local")
def add_local_file(
    filepath: str,
    device: str = "auto",
    background_tasks: BackgroundTasks = None
):
    """Adds a local video file to the library and transcribes it."""
    abs_filepath = os.path.abspath(filepath)
    
    # Validate file exists
    if not os.path.exists(abs_filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Validate it's a media file
    ext = os.path.splitext(abs_filepath)[1].lower()
    if ext not in MEDIA_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Supported: {', '.join(MEDIA_EXTENSIONS)}"
        )
    
    def run_transcribe_and_index():
        try:
            logger.info(f"Processing local file: {abs_filepath}")
            
            # Check if already transcribed
            transcript_path = os.path.splitext(abs_filepath)[0] + ".json"
            needs_transcription = not os.path.exists(transcript_path)
            
            if needs_transcription:
                # Transcribe using model manager
                model_mgr = get_model_manager()
                backend = None
                if device == "mlx":
                    backend = TranscriptionBackend.MLX_WHISPER
                elif device == "cpu":
                    backend = TranscriptionBackend.FASTER_WHISPER
                
                trans_result = model_mgr.transcribe(abs_filepath, backend=backend)
                
                # Save transcript
                import json
                with open(transcript_path, "w", encoding="utf-8") as f:
                    json.dump(trans_result.segments, f)
                
                logger.info(f"Transcription saved: {transcript_path}")
            
            # Add to database
            with Session(engine) as session:
                # Scan the parent directory to add the file
                parent_dir = os.path.dirname(abs_filepath)
                _scan_path(parent_dir, session)
                
                # Auto-index for semantic search
                if features.enable_auto_indexing and features.enable_semantic_search:
                    video = session.exec(
                        select(Video).where(Video.path == abs_filepath)
                    ).first()
                    if video and not needs_transcription:
                        # Load existing transcript for indexing
                        import json
                        with open(transcript_path, "r", encoding="utf-8") as f:
                            segments = json.load(f)
                        vector_store = get_vector_store()
                        vector_store.index_video(video.id, segments, session)
                    elif video and needs_transcription:
                        # Use the fresh transcription
                        vector_store = get_vector_store()
                        vector_store.index_video(video.id, trans_result.segments, session)
                
            logger.info(f"Successfully processed local file: {abs_filepath}")
        except Exception as e:
            logger.error(f"Local file processing failed: {e}")
    
    background_tasks.add_task(run_transcribe_and_index)
    return {"status": "started", "filepath": abs_filepath}


@app.get("/search", response_model=List[SearchResult])
def search(
    query: str, 
    type: str = DEFAULT_SEARCH_TYPE, 
    threshold: float = 0.45,
    video_ids: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Searches across all videos in the library.
    
    Args:
        query: Search query
        type: Search type (sentence, fragment, mash, semantic)
        threshold: Semantic search threshold (0-1)
        video_ids: Comma-separated video IDs to search (optional)
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


@app.post("/export")
def export_supercut(
    matches: List[SearchResult], 
    output: str,
    transition: str = "cut",
    transition_duration: float = 0.5,
    burn_subtitles: bool = False,
    subtitle_preset: str = "default",
    background_tasks: BackgroundTasks = None
):
    """
    Exports a supercut from the given search results.
    
    Args:
        matches: List of SearchResult segments
        output: Output file path
        transition: Transition type (cut, crossfade, fade_to_black)
        transition_duration: Duration of transitions in seconds
        burn_subtitles: Whether to burn subtitles onto the video
        subtitle_preset: Subtitle style preset (default, netflix, youtube, minimal, bold)
    """
    composition = [m.dict() for m in matches]
    
    def run_export():
        try:
            # Determine transition type
            trans_type = TransType.CUT
            if transition == "crossfade":
                trans_type = TransType.CROSSFADE
            elif transition == "fade_to_black":
                trans_type = TransType.FADE_TO_BLACK
            elif transition == "dissolve":
                trans_type = TransType.DISSOLVE
            
            if burn_subtitles:
                style = PRESET_STYLES.get(subtitle_preset, SubtitleStyle())
                burn_subtitles_on_segments(composition, output, style=style)
            elif trans_type != TransType.CUT:
                concatenate_with_transitions(
                    composition, output, 
                    transition_type=trans_type,
                    transition_duration=transition_duration
                )
            else:
                # Use default exporter
                from ..exporter import create_supercut
                create_supercut(composition, output)
            
            logger.info(f"Export completed: {output}")
        except Exception as e:
            logger.error(f"Background export failed: {e}")

    background_tasks.add_task(run_export)
    return {"status": "started", "path": output}


@app.post("/open_folder")
def open_folder(path: str):
    """Opens a file or directory in the system's file manager."""
    try:
        abs_path = os.path.abspath(path)
        if os.path.isfile(abs_path):
            abs_path = os.path.dirname(abs_path)
            
        if sys.platform == "darwin":
            subprocess.run(["open", abs_path])
        elif sys.platform == "win32":
            os.startfile(abs_path)
        else:
            subprocess.run(["xdg-open", abs_path])
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Open folder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ngrams")
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


# ============================================================================
# Phase 2: Semantic Search & Vector Indexing
# ============================================================================
@app.post("/index/{video_id}")
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


@app.post("/index/all")
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
        with Session(engine) as bg_session:
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


@app.get("/index/stats", response_model=VectorStats)
def get_index_stats(session: Session = Depends(get_session)):
    """Get statistics about the vector index."""
    vector_store = get_vector_store()
    stats = vector_store.get_stats(session)
    return VectorStats(**stats)


# ============================================================================
# Phase 2: Speaker Diarization
# ============================================================================
@app.post("/diarize/{video_id}")
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
            from .diarization import diarize_cached, assign_speakers_to_transcript
            
            segments = diarize_cached(video.path, num_speakers=num_speakers, force=force)
            
            # Update database
            with Session(engine) as bg_session:
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


@app.get("/speakers/{video_id}", response_model=List[Speaker])
def get_video_speakers(video_id: int, session: Session = Depends(get_session)):
    """Get speakers detected in a video."""
    speakers = session.exec(
        select(Speaker).where(Speaker.video_id == video_id)
    ).all()
    return speakers


# ============================================================================
# Phase 3: Multi-Model Support
# ============================================================================
@app.get("/models")
def get_available_models():
    """Get list of available transcription models."""
    model_mgr = get_model_manager()
    return {
        "models": [
            {
                "name": m.name,
                "backend": m.backend.value,
                "description": m.description,
                "is_available": m.is_available,
                "requires_gpu": m.requires_gpu,
                "estimated_speed": m.estimated_speed
            }
            for m in model_mgr.get_available_models()
        ],
        "backends": model_mgr.get_available_backends()
    }


@app.post("/transcribe/{video_id}")
def transcribe_video(
    video_id: int,
    model: Optional[str] = None,
    backend: Optional[str] = None,
    language: Optional[str] = None,
    force: bool = False,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_session)
):
    """Transcribe a video using the specified model and backend."""
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.has_transcript and not force:
        return {"status": "already_transcribed", "video_id": video_id}
    
    def run_transcription():
        try:
            model_mgr = get_model_manager()
            
            backend_enum = None
            if backend:
                try:
                    backend_enum = TranscriptionBackend(backend)
                except ValueError:
                    logger.warning(f"Unknown backend: {backend}")
            
            result = model_mgr.transcribe(
                video.path,
                backend=backend_enum,
                model=model,
                language=language
            )
            
            # Save transcript
            import json
            transcript_path = os.path.splitext(video.path)[0] + ".json"
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(result.segments, f)
            
            # Update database
            with Session(engine) as bg_session:
                vid = bg_session.get(Video, video_id)
                vid.has_transcript = True
                vid.transcript_path = transcript_path
                bg_session.add(vid)
                bg_session.commit()
            
            logger.info(f"Transcription completed for video {video_id}")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
    
    background_tasks.add_task(run_transcription)
    return {"status": "started", "video_id": video_id}


# ============================================================================
# Phase 3: Subtitle Styles
# ============================================================================
@app.get("/subtitle-presets")
def get_subtitle_presets():
    """Get available subtitle style presets."""
    return {
        name: style.to_dict() 
        for name, style in PRESET_STYLES.items()
    }


# ============================================================================
# Media Serving
# ============================================================================
@app.get("/media/{video_id}")
def serve_media(video_id: int, session: Session = Depends(get_session)):
    """Serve a video file for playback."""
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not os.path.exists(video.path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    
    return FileResponse(
        video.path,
        media_type="video/mp4",
        filename=video.filename
    )


# ============================================================================
# Entry Point
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
