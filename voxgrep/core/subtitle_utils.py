"""
VoxGrep Subtitle Utilities

Provides shared functionality for subtitle burn-in during video export.
"""
from typing import Any

from ..utils.helpers import setup_logger

logger = setup_logger(__name__)


def create_subtitle_clip(
    text: str,
    clip_duration: float,
    clip_width: int,
    font_size: int = 40,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    position_y: float = 0.85,
) -> Any | None:
    """
    Create a TextClip for subtitle burn-in.

    Args:
        text: The subtitle text to display.
        clip_duration: Duration of the clip in seconds.
        clip_width: Width of the video clip for text sizing.
        font_size: Font size for the subtitle text.
        color: Text color.
        stroke_color: Outline/stroke color for readability.
        stroke_width: Width of the text stroke.
        position_y: Vertical position as fraction (0=top, 1=bottom).

    Returns:
        A CompositeVideoClip-compatible TextClip positioned at the bottom,
        or None if creation fails.
    """
    try:
        from moviepy import TextClip

        txt_clip = TextClip(
            text=text,
            font_size=font_size,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method="caption",
            size=(int(clip_width * 0.9), None),  # 90% width
        ).with_duration(clip_duration).with_position(("center", position_y), relative=True)

        return txt_clip

    except Exception as e:
        logger.warning(f"Failed to create subtitle clip: {e}")
        return None


def apply_subtitle_to_clip(
    video_clip: Any,
    text: str,
    font_size: int = 40,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    position_y: float = 0.85,
) -> Any:
    """
    Apply a subtitle overlay to a video clip.

    Args:
        video_clip: The video clip to add subtitle to.
        text: The subtitle text.
        font_size: Font size for the subtitle text.
        color: Text color.
        stroke_color: Outline/stroke color.
        stroke_width: Width of the text stroke.
        position_y: Vertical position as fraction.

    Returns:
        CompositeVideoClip with subtitle overlay, or original clip if subtitle fails.
    """
    txt_clip = create_subtitle_clip(
        text=text,
        clip_duration=video_clip.duration,
        clip_width=video_clip.w,
        font_size=font_size,
        color=color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        position_y=position_y,
    )

    if txt_clip is None:
        return video_clip

    try:
        from moviepy import CompositeVideoClip

        return CompositeVideoClip([video_clip, txt_clip])
    except Exception as e:
        logger.warning(f"Failed to composite subtitle: {e}")
        return video_clip
