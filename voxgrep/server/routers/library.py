"""
Library Management Routes
"""
import os
import subprocess
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from ..dependencies import get_session, get_model_manager, get_vector_store, config, features, logger
from ..models import Video
from ...core import engine as search_engine
from ...utils.config import MEDIA_EXTENSIONS
from ...utils.helpers import ensure_directory_exists, validate_media_file
from ..db import engine, Session as DbSession
from ..multi_model import TranscriptionBackend

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


# Note: /download and /add-local were top level in app.py but logically belong to library management. 
# We'll put them here but alias them if we want to keep API compatibility, or just move them.
# The original app.py had them as /download and /add-local. 
# We can mount this router with a prefix, but these endpoints didn't have /library prefix.
# We'll define them here without the prefix using include_in_schema logic in app.py or just define them separately.
# For now, I'll put them in this file but attach them to a separate router or same router with different path.
# To keep simple, I'll make a separate router for 'ingest' operations or just put them here and we'll handle routing in app.py

@router.post("/download", include_in_schema=False) 
# Wait, if I put it in this router, it will be /library/download. That changes the API.
# Let's create a separate router object for these top-level endpoints in this file.

ingest_router = APIRouter(tags=["ingest"])

@ingest_router.post("/download")
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
            filepath = result.stdout.strip().split('\\n')[-1]
            
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
            with DbSession(engine) as session:
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


@ingest_router.post("/add-local")
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
            with DbSession(engine) as session:
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

# Add media serving here as well as it takes an ID
@router.get("/media/{video_id}") # This becomes /library/media/{video_id} which is fine but original was /media/{video_id}
def serve_media(video_id: int, session: Session = Depends(get_session)):
    """Serve a video file for playback."""
    # ... logic ...
    pass

# Actually, to avoid breaking frontend, I should probably keep /media top level.
# I'll add it to ingest_router or creating a separate one.
media_router = APIRouter(tags=["media"])

@media_router.get("/media/{video_id}")
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
