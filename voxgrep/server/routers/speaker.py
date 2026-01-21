"""
Speaker Diarization Routes
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select, Session as DbSession

from ..dependencies import get_session, features, logger
from ..models import Video, Speaker
from ..db import engine

router = APIRouter(tags=["speakers"])

@router.post("/diarize/{video_id}")
def diarize_video(
    video_id: int,
    num_speakers: int | None = None,
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


@router.get("/speakers/{video_id}", response_model=list[Speaker])
def get_video_speakers(video_id: int, session: Session = Depends(get_session)):
    """Get speakers detected in a video."""
    speakers = session.exec(
        select(Speaker).where(Speaker.video_id == video_id)
    ).all()
    return speakers
