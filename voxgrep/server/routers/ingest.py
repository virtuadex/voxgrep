"""
Ingest Routes (Download and Local Add)
"""
import os
import subprocess
import json
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlmodel import select, Session as DbSession

from ..dependencies import get_model_manager, get_vector_store, config, features, logger
from ..models import Video
from ..db import engine
from ..multi_model import TranscriptionBackend
from ...utils.config import MEDIA_EXTENSIONS
from ...utils.helpers import ensure_directory_exists
from .library import _scan_path

router = APIRouter(tags=["ingest"])

@router.post("/download")
def download_video(
    url: str, 
    output_dir: Optional[str] = None, 
    device: str = "auto",
    background_tasks: BackgroundTasks = None
):
    """Downloads a video from a URL using yt-dlp and transcribes it."""
    # Ensure background_tasks is not None to avoid AttributeError if not provided (though FastAPI usually injects it)
    if background_tasks is None:
        # This shouldn't happen with FastAPI injection but good for safety/testing
        raise HTTPException(status_code=500, detail="BackgroundTasks dependency missing")

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


@router.post("/add-local")
def add_local_file(
    filepath: str,
    device: str = "auto",
    background_tasks: BackgroundTasks = None
):
    """Adds a local video file to the library and transcribes it."""
    if background_tasks is None:
        raise HTTPException(status_code=500, detail="BackgroundTasks dependency missing")

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
                        with open(transcript_path, "r", encoding="utf-8") as f:
                            segments = json.load(f)
                        vector_store = get_vector_store()
                        vector_store.index_video(video.id, segments, session)
                    elif video and needs_transcription:
                        # Use the fresh transcription
                        # Note: trans_result is local to the if block above. 
                        # I must ensure it's available here or re-read it.
                        # Wait, if needs_transcription is True, trans_result is defined.
                        # Python scoping allows it.
                        vector_store = get_vector_store()
                        vector_store.index_video(video.id, trans_result.segments, session)
                
            logger.info(f"Successfully processed local file: {abs_filepath}")
        except Exception as e:
            logger.error(f"Local file processing failed: {e}")
    
    background_tasks.add_task(run_transcribe_and_index)
    return {"status": "started", "filepath": abs_filepath}
