"""
Export Routes
"""
from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks

from ..dependencies import logger
from ..models import SearchResult
from ..transitions import concatenate_with_transitions, TransitionType as TransType
from ..subtitles import SubtitleStyle, burn_subtitles_on_segments, PRESET_STYLES

router = APIRouter(tags=["export"])

@router.post("/export")
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
                from ...core.exporter import create_supercut
                create_supercut(composition, output)
            
            logger.info(f"Export completed: {output}")
        except Exception as e:
            logger.error(f"Background export failed: {e}")

    background_tasks.add_task(run_export)
    return {"status": "started", "path": output}


@router.get("/subtitle-presets")
def get_subtitle_presets():
    """Get available subtitle style presets."""
    return {
        name: style.to_dict() 
        for name, style in PRESET_STYLES.items()
    }
