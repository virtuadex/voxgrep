"""
VoxGrep Subtitle Rendering Module (Phase 3)

Provides subtitle burning (hardcoding) capabilities for supercuts.
Supports multiple styling options and positioning.
"""
import os
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from ..utils import setup_logger

logger = setup_logger(__name__)

# Try to import moviepy
try:
    from moviepy import (
        TextClip, CompositeVideoClip, VideoFileClip, 
        concatenate_videoclips
    )
    MOVIEPY_AVAILABLE = True
except ImportError:
    try:
        from moviepy.editor import (
            TextClip, CompositeVideoClip, VideoFileClip, 
            concatenate_videoclips
        )
        MOVIEPY_AVAILABLE = True
    except ImportError:
        MOVIEPY_AVAILABLE = False


@dataclass
class SubtitleStyle:
    """Styling options for burned-in subtitles."""
    font: str = "Arial"
    fontsize: int = 36
    color: str = "white"
    stroke_color: str = "black"
    stroke_width: float = 2.0
    bg_color: Optional[str] = None  # e.g., "rgba(0,0,0,0.5)"
    position: str = "bottom"  # "bottom", "top", "center"
    margin_bottom: int = 50
    margin_top: int = 50
    max_width_ratio: float = 0.9  # Max width as ratio of video width
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SubtitleStyle":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def preset_netflix(cls) -> "SubtitleStyle":
        """Netflix-style subtitles."""
        return cls(
            font="Helvetica-Bold",
            fontsize=42,
            color="white",
            stroke_color="black",
            stroke_width=2.5,
            position="bottom",
            margin_bottom=60
        )
    
    @classmethod
    def preset_youtube(cls) -> "SubtitleStyle":
        """YouTube-style subtitles with background."""
        return cls(
            font="Arial",
            fontsize=32,
            color="white",
            stroke_color=None,
            stroke_width=0,
            bg_color="rgba(0,0,0,0.75)",
            position="bottom",
            margin_bottom=40
        )
    
    @classmethod
    def preset_minimal(cls) -> "SubtitleStyle":
        """Minimal, clean subtitle style."""
        return cls(
            font="Helvetica",
            fontsize=28,
            color="white",
            stroke_color="black",
            stroke_width=1.0,
            position="bottom",
            margin_bottom=30
        )
    
    @classmethod
    def preset_bold(cls) -> "SubtitleStyle":
        """Bold, high-impact subtitles."""
        return cls(
            font="Impact",
            fontsize=48,
            color="yellow",
            stroke_color="black",
            stroke_width=3.0,
            position="center"
        )


def create_text_clip(
    text: str,
    duration: float,
    video_size: tuple,
    style: SubtitleStyle
):
    """
    Create a styled text clip for subtitle overlay.
    """
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("MoviePy is required for subtitle rendering")
    
    video_width, video_height = video_size
    max_width = int(video_width * style.max_width_ratio)
    
    # Create text clip with styling
    # Note: text param name varies by moviepy version, explicit kwargs safer for v2
    txt_clip = TextClip(
        text=text,
        font=style.font,
        font_size=style.fontsize,
        color=style.color,
        stroke_color=style.stroke_color if style.stroke_width > 0 else None,
        stroke_width=style.stroke_width if style.stroke_width > 0 else None,
        method="caption",  # Enables word wrapping
        size=(max_width, None),  # Constrain width, auto height
        horizontal_align="center"
    )
    
    # Set duration
    if hasattr(txt_clip, "with_duration"):
        txt_clip = txt_clip.with_duration(duration)
    else:
        txt_clip = txt_clip.set_duration(duration)
    
    # Calculate position
    if style.position == "bottom":
        position = ("center", video_height - style.margin_bottom - txt_clip.h)
    elif style.position == "top":
        position = ("center", style.margin_top)
    else:  # center
        position = ("center", "center")
    
    if hasattr(txt_clip, "with_position"):
        txt_clip = txt_clip.with_position(position)
    else:
        txt_clip = txt_clip.set_position(position)
    
    return txt_clip


def burn_subtitles_on_clip(
    video_clip,
    subtitles: List[dict],
    style: Optional[SubtitleStyle] = None,
    offset: float = 0
):
    """
    Burn subtitles onto a video clip.
    """
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("MoviePy is required for subtitle rendering")
    
    if style is None:
        style = SubtitleStyle()
    
    video_size = video_clip.size
    text_clips = [video_clip]
    
    for sub in subtitles:
        start = sub.get("start", 0) - offset
        end = sub.get("end", 0) - offset
        content = sub.get("content", "")
        
        # Skip if outside clip bounds
        if end <= 0 or start >= video_clip.duration:
            continue
        
        # Clamp to clip bounds
        start = max(0, start)
        end = min(video_clip.duration, end)
        duration = end - start
        
        if duration <= 0 or not content.strip():
            continue
        
        # Create and position text clip
        txt_clip = create_text_clip(content, duration, video_size, style)
        
        if hasattr(txt_clip, "with_start"):
            txt_clip = txt_clip.with_start(start)
        else:
            txt_clip = txt_clip.set_start(start)
            
        text_clips.append(txt_clip)
    
    # Composite all clips
    return CompositeVideoClip(text_clips)


def burn_subtitles_on_segments(
    segments: List[dict],
    output_path: str,
    style: Optional[SubtitleStyle] = None,
    include_transitions: bool = False
) -> str:
    """
    Create a supercut with burned-in subtitles.
    """
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("MoviePy is required for subtitle rendering")
    
    if style is None:
        style = SubtitleStyle()
    
    logger.info(f"Creating supercut with burned subtitles for {len(segments)} clips")
    
    processed_clips = []
    
    for seg in segments:
        try:
            # Load video segment
            # Handle v1 vs v2 subclip
            source_clip = VideoFileClip(seg["file"])
            start, end = seg["start"], seg["end"]
            
            if hasattr(source_clip, "subclipped"):
                clip = source_clip.subclipped(start, end)
            else:
                clip = source_clip.subclip(start, end)
            
            # Create subtitle for this segment
            # Subtitle timing is relative to the segment start (0)
            subtitle = [{
                "start": 0,
                "end": clip.duration,
                "content": seg.get("content", "")
            }]
            
            # Burn subtitle
            clip_with_subs = burn_subtitles_on_clip(clip, subtitle, style)
            processed_clips.append(clip_with_subs)
            
        except Exception as e:
            logger.error(f"Error processing clip from {seg['file']}: {e}")
            continue
    
    if not processed_clips:
        raise RuntimeError("No valid clips processed")
    
    # Concatenate
    final = concatenate_videoclips(processed_clips, method="compose")
    
    # Write output
    logger.info(f"Writing output with burned subtitles to {output_path}")
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        logger=None
    )
    
    # Cleanup
    final.close()
    for clip in processed_clips:
        clip.close()
    
    logger.info(f"Supercut with subtitles saved: {output_path}")
    return output_path


def get_available_fonts() -> List[str]:
    """
    Get list of available fonts on the system.
    """
    # Common cross-platform fonts
    common_fonts = [
        "Arial",
        "Helvetica",
        "Helvetica-Bold",
        "Times-Roman",
        "Courier",
        "Impact",
        "Georgia",
        "Verdana",
        "Comic-Sans-MS",
        "Trebuchet-MS"
    ]
    
    # Try to detect system fonts
    try:
        import subprocess
        if os.name == "posix":
            result = subprocess.run(
                ["fc-list", ":", "family"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                fonts = set()
                for line in result.stdout.strip().split("\n"):
                    for font in line.split(","):
                        fonts.add(font.strip())
                return sorted(fonts)
    except Exception:
        pass
    
    return common_fonts


# Preset styles available for the API
PRESET_STYLES = {
    "default": SubtitleStyle(),
    "netflix": SubtitleStyle.preset_netflix(),
    "youtube": SubtitleStyle.preset_youtube(),
    "minimal": SubtitleStyle.preset_minimal(),
    "bold": SubtitleStyle.preset_bold()
}
