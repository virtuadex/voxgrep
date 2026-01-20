"""
VoxGrep Transitions Module (Phase 3)

Provides dynamic video transitions including crossfades, dissolves,
and audio smoothing for professional supercut output.
"""
import os
from typing import List, Optional, Tuple, Union
from enum import Enum

from ..utils import setup_logger
from ..config import BATCH_SIZE

logger = setup_logger(__name__)

# MoviePy v2 compatibility imports
try:
    from moviepy import (
        VideoFileClip, AudioFileClip, CompositeVideoClip, 
        CompositeAudioClip, concatenate_videoclips, 
        concatenate_audioclips, vfx, afx
    )
    
    # Compatibility wrappers for v2
    def fadein(clip, duration):
        return clip.with_effects([vfx.FadeIn(duration)])
        
    def fadeout(clip, duration):
        return clip.with_effects([vfx.FadeOut(duration)])
        
    def audio_fadein(audio, duration):
        return audio.with_effects([afx.AudioFadeIn(duration)])
        
    def audio_fadeout(audio, duration):
        return audio.with_effects([afx.AudioFadeOut(duration)])

    MOVIEPY_AVAILABLE = True
except ImportError:
    # Try v1 fallback (unlikely given environment, but good practice)
    try:
        from moviepy.editor import (
            VideoFileClip, AudioFileClip, CompositeVideoClip, 
            CompositeAudioClip, concatenate_videoclips, 
            concatenate_audioclips, vfx, afx
        )
        from moviepy.video.fx.fadein import fadein
        from moviepy.video.fx.fadeout import fadeout
        from moviepy.audio.fx.audio_fadein import audio_fadein
        from moviepy.audio.fx.audio_fadeout import audio_fadeout
        MOVIEPY_AVAILABLE = True
    except ImportError:
        MOVIEPY_AVAILABLE = False


class TransitionType(str, Enum):
    """Types of video transitions."""
    CUT = "cut"
    CROSSFADE = "crossfade"
    FADE_TO_BLACK = "fade_to_black"
    DISSOLVE = "dissolve"


def apply_audio_smoothing(
    clip,
    fade_duration: float = 0.1
):
    """
    Apply audio fade-in and fade-out to smooth audio transitions.
    """
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("MoviePy is required for transitions")
    
    if clip.audio is None:
        return clip
    
    # Apply audio fades
    # In v2, we operate on clip.audio directly, but set_audio is replaced by with_audio
    smoothed_audio = clip.audio
    if clip.duration > fade_duration * 2:
        try:
            smoothed_audio = audio_fadein(smoothed_audio, fade_duration)
            smoothed_audio = audio_fadeout(smoothed_audio, fade_duration)
        except Exception:
            # Fallback if audio wrappers fail (e.g. API diff)
            pass
            
    # Try with_audio (v2) else set_audio (v1)
    if hasattr(clip, "with_audio"):
        return clip.with_audio(smoothed_audio)
    return clip.set_audio(smoothed_audio)


def create_crossfade_transition(
    clip1,
    clip2,
    duration: float = 0.5
):
    """
    Create a crossfade transition between two clips.
    """
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("MoviePy is required for transitions")
    
    # Ensure clips are long enough for the transition
    if clip1.duration <= duration or clip2.duration <= duration:
        logger.warning("Clips too short for crossfade, reducing duration")
        duration = min(clip1.duration, clip2.duration) / 2
    
    # Apply fadeout to first clip's end
    clip1_faded = fadeout(clip1, duration)
    if clip1_faded.audio:
        clip1_faded_audio = audio_fadeout(clip1_faded.audio, duration)
        if hasattr(clip1_faded, "with_audio"):
            clip1_faded = clip1_faded.with_audio(clip1_faded_audio)
        else:
            clip1_faded = clip1_faded.set_audio(clip1_faded_audio)
    
    # Apply fadein to second clip's start
    clip2_faded = fadein(clip2, duration)
    if clip2_faded.audio:
        clip2_faded_audio = audio_fadein(clip2_faded.audio, duration)
        if hasattr(clip2_faded, "with_audio"):
            clip2_faded = clip2_faded.with_audio(clip2_faded_audio)
        else:
            clip2_faded = clip2_faded.set_audio(clip2_faded_audio)
    
    return clip1_faded, clip2_faded


def create_fade_to_black_transition(
    clip1,
    clip2,
    duration: float = 0.5
):
    """
    Create a fade-to-black transition between two clips.
    """
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("MoviePy is required for transitions")
    
    # Fade out first clip to black
    clip1_faded = fadeout(clip1, duration)
    if clip1_faded.audio:
        clip1_faded_audio = audio_fadeout(clip1_faded.audio, duration)
        if hasattr(clip1_faded, "with_audio"):
            clip1_faded = clip1_faded.with_audio(clip1_faded_audio)
        else:
            clip1_faded = clip1_faded.set_audio(clip1_faded_audio)
    
    # Fade in second clip from black
    clip2_faded = fadein(clip2, duration)
    if clip2_faded.audio:
        clip2_faded_audio = audio_fadein(clip2_faded.audio, duration)
        if hasattr(clip2_faded, "with_audio"):
            clip2_faded = clip2_faded.with_audio(clip2_faded_audio)
        else:
            clip2_faded = clip2_faded.set_audio(clip2_faded_audio)
    
    return clip1_faded, clip2_faded


def concatenate_with_transitions(
    segments: List[dict],
    output_path: str,
    transition_type: TransitionType = TransitionType.CUT,
    transition_duration: float = 0.5,
    audio_smoothing: bool = True
) -> str:
    """
    Concatenate video segments with transitions.
    """
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("MoviePy is required for transitions")
    
    if not segments:
        raise ValueError("No segments provided")
    
    logger.info(f"Creating supercut with {len(segments)} clips and {transition_type.value} transitions")
    
    clips = []
    
    for seg in segments:
        try:
            # Handle subclip/subclipped compatibility
            clip_source = VideoFileClip(seg["file"])
            start, end = seg["start"], seg["end"]
            
            if hasattr(clip_source, "subclipped"):
                clip = clip_source.subclipped(start, end)
            else:
                clip = clip_source.subclip(start, end)
            
            # Apply audio smoothing if requested
            if audio_smoothing and clip.audio:
                clip = apply_audio_smoothing(clip, fade_duration=0.05)
            
            clips.append(clip)
        except Exception as e:
            logger.error(f"Error loading clip from {seg['file']}: {e}")
            continue
    
    if not clips:
        raise RuntimeError("No valid clips loaded")
    
    # Apply transitions
    if transition_type == TransitionType.CUT:
        # Simple concatenation
        final = concatenate_videoclips(clips, method="compose")
    
    elif transition_type in [TransitionType.CROSSFADE, TransitionType.DISSOLVE]:
        # Crossfade between all clips
        processed_clips = []
        
        for i, clip in enumerate(clips):
            if i == 0:
                # First clip: only fade out at end
                if len(clips) > 1:
                    clip = fadeout(clip, transition_duration)
                    if clip.audio:
                         if hasattr(clip, "with_audio"):
                            clip = clip.with_audio(audio_fadeout(clip.audio, transition_duration))
                         else:
                            clip = clip.set_audio(audio_fadeout(clip.audio, transition_duration))
                processed_clips.append(clip)
            elif i == len(clips) - 1:
                # Last clip: only fade in at start
                clip = fadein(clip, transition_duration)
                if clip.audio:
                    if hasattr(clip, "with_audio"):
                         clip = clip.with_audio(audio_fadein(clip.audio, transition_duration))
                    else:
                         clip = clip.set_audio(audio_fadein(clip.audio, transition_duration))
                
                # Offset to overlap with previous clip
                prev_end = processed_clips[-1].end
                if hasattr(clip, "with_start"):
                    clip = clip.with_start(prev_end - transition_duration)
                else:
                    clip = clip.set_start(prev_end - transition_duration)
                    
                processed_clips.append(clip)
            else:
                # Middle clips: fade in and out
                clip = fadein(clip, transition_duration)
                clip = fadeout(clip, transition_duration)
                if clip.audio:
                    # audio fadein THEN fadeout
                    faded_audio = audio_fadein(clip.audio, transition_duration)
                    faded_audio = audio_fadeout(faded_audio, transition_duration)
                    if hasattr(clip, "with_audio"):
                        clip = clip.with_audio(faded_audio)
                    else:
                        clip = clip.set_audio(faded_audio)
                        
                # Offset to overlap with previous clip
                prev_end = processed_clips[-1].end
                if hasattr(clip, "with_start"):
                    clip = clip.with_start(prev_end - transition_duration)
                else:
                    clip = clip.set_start(prev_end - transition_duration)
                    
                processed_clips.append(clip)
        
        # Use CompositeVideoClip to layer the overlapping clips
        final = CompositeVideoClip(processed_clips)
    
    elif transition_type == TransitionType.FADE_TO_BLACK:
        # Add black frames between clips
        processed_clips = []
        
        for i, clip in enumerate(clips):
            # Fade out
            clip = fadeout(clip, transition_duration)
            if clip.audio:
                if hasattr(clip, "with_audio"):
                     clip = clip.with_audio(audio_fadeout(clip.audio, transition_duration))
                else:
                     clip = clip.set_audio(audio_fadeout(clip.audio, transition_duration))
            
            # Fade in (except first clip)
            if i > 0:
                clip = fadein(clip, transition_duration)
                if clip.audio:
                    if hasattr(clip, "with_audio"):
                        clip = clip.with_audio(audio_fadein(clip.audio, transition_duration))
                    else:
                        clip = clip.set_audio(audio_fadein(clip.audio, transition_duration))
            
            processed_clips.append(clip)
        
        final = concatenate_videoclips(processed_clips, method="compose")
    
    else:
        # Default to simple cut
        final = concatenate_videoclips(clips, method="compose")
    
    # Write output
    logger.info(f"Writing output to {output_path}")
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=f"{output_path}.temp.m4a",
        remove_temp=True,
        logger=None  # Suppress moviepy's progress bar
    )
    
    # Cleanup
    final.close()
    for clip in clips:
        clip.close()
    
    logger.info(f"Supercut saved: {output_path}")
    return output_path


def concatenate_with_transitions_batched(
    segments: List[dict],
    output_path: str,
    transition_type: TransitionType = TransitionType.CUT,
    transition_duration: float = 0.5,
    batch_size: int = BATCH_SIZE
) -> str:
    """
    Process large supercuts in batches to manage memory.
    """
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("MoviePy is required for transitions")
    
    if len(segments) <= batch_size:
        return concatenate_with_transitions(
            segments, output_path, transition_type, transition_duration
        )
    
    import tempfile
    import shutil
    
    logger.info(f"Processing {len(segments)} clips in batches of {batch_size}")
    
    # Create temp directory for intermediate files
    temp_dir = tempfile.mkdtemp(prefix="voxgrep_batch_")
    batch_outputs = []
    
    try:
        # Process in batches
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            batch_output = os.path.join(temp_dir, f"batch_{i:04d}.mp4")
            
            logger.info(f"Processing batch {i // batch_size + 1}")
            concatenate_with_transitions(
                batch, batch_output, transition_type, transition_duration
            )
            batch_outputs.append({"file": batch_output, "start": 0, "end": None})
        
        # Concatenate batch outputs
        logger.info("Combining batch outputs...")
        final_clips = []
        for batch_file in batch_outputs:
            clip = VideoFileClip(batch_file["file"])
            final_clips.append(clip)
        
        final = concatenate_videoclips(final_clips, method="compose")
        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            logger=None
        )
        
        # Cleanup
        final.close()
        for clip in final_clips:
            clip.close()
        
    finally:
        # Remove temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    logger.info(f"Batched supercut saved: {output_path}")
    return output_path
