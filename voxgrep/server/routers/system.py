"""
System, Health, and Configuration Routes
"""
import sys
import os
import subprocess
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from sqlmodel import Session

from ..dependencies import get_session, get_model_manager, config, features, logger
from ..models import Video
from ..multi_model import TranscriptionBackend

router = APIRouter(tags=["system"])

@router.get("/health")
def health_check():
    """Health check endpoint."""
    from ..vector_store import TRANSFORMERS_AVAILABLE
    return {
        "status": "ok",
        "version": "0.3.0",
        "features": {
            "semantic_search": features.enable_semantic_search and TRANSFORMERS_AVAILABLE,
            "mlx_transcription": features.enable_mlx_transcription,
            "speaker_diarization": features.enable_speaker_diarization
        }
    }

@router.post("/open_folder")
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

@router.get("/models")
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

@router.post("/transcribe/{video_id}")
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
            from ..db import engine
            from sqlmodel import Session as DbSession
            
            with DbSession(engine) as bg_session:
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
