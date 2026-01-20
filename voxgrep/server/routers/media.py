"""
Media Serving Routes
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session

from ..dependencies import get_session
from ..models import Video

router = APIRouter(tags=["media"])

@router.get("/media/{video_id}")
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
