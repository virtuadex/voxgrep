"""
Audio processing utilities for VoxGrep.
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_audio(
    input_file: str,
    output_file: Optional[str] = None,
    target_level: float = -16.0,
    cleanup: bool = True
) -> str:
    """
    Normalize audio levels using ffmpeg loudnorm filter.
    
    This applies EBU R128 loudness normalization which:
    - Evens out volume across the entire audio
    - Makes quiet speech more audible
    - Prevents loud sections from clipping
    - Improves Whisper transcription accuracy
    
    Args:
        input_file: Path to input video/audio file
        output_file: Optional path for output. If None, creates temp file.
        target_level: Target loudness in LUFS (default: -16.0, broadcast standard)
        cleanup: Whether to clean up temp files on error
        
    Returns:
        Path to normalized audio file
        
    Raises:
        RuntimeError: If ffmpeg is not available or normalization fails
    """
    # Check if ffmpeg is available
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(
            "ffmpeg is required for audio normalization but was not found. "
            "Please install ffmpeg and ensure it's in your PATH."
        )
    
    # Create output path if not provided
    if output_file is None:
        temp_dir = tempfile.gettempdir()
        base_name = Path(input_file).stem
        output_file = os.path.join(temp_dir, f"{base_name}_normalized.wav")
    
    logger.info(f"Normalizing audio: {input_file} -> {output_file}")
    logger.info(f"Target loudness: {target_level} LUFS")
    
    try:
        # Two-pass normalization for better results
        # Pass 1: Measure loudness
        cmd_measure = [
            "ffmpeg",
            "-i", input_file,
            "-af", f"loudnorm=I={target_level}:TP=-1.5:LRA=11:print_format=json",
            "-f", "null",
            "-"
        ]
        
        logger.debug(f"Measuring audio levels: {' '.join(cmd_measure)}")
        result = subprocess.run(
            cmd_measure,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Pass 2: Apply normalization and extract audio
        cmd_normalize = [
            "ffmpeg",
            "-i", input_file,
            "-af", f"loudnorm=I={target_level}:TP=-1.5:LRA=11",
            "-ar", "16000",  # Whisper's native sample rate
            "-ac", "1",       # Mono (Whisper doesn't need stereo)
            "-c:a", "pcm_s16le",  # Uncompressed for quality
            "-y",  # Overwrite output
            output_file
        ]
        
        logger.debug(f"Applying normalization: {' '.join(cmd_normalize)}")
        subprocess.run(
            cmd_normalize,
            capture_output=True,
            check=True
        )
        
        # Verify output exists
        if not os.path.exists(output_file):
            raise RuntimeError(f"Normalization completed but output file not found: {output_file}")
        
        file_size = os.path.getsize(output_file)
        logger.info(f"Audio normalized successfully. Output size: {file_size / 1024 / 1024:.2f} MB")
        
        return output_file
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Audio normalization failed: {e.stderr if e.stderr else str(e)}"
        logger.error(error_msg)
        
        # Clean up partial output
        if cleanup and output_file and os.path.exists(output_file):
            try:
                os.remove(output_file)
            except OSError:
                pass
        
        raise RuntimeError(error_msg) from e


def get_normalized_cache_path(video_file: str) -> str:
    """
    Get the cache path for normalized audio file.
    
    Args:
        video_file: Path to original video file
        
    Returns:
        Path where normalized audio should be cached
    """
    video_path = Path(video_file)
    cache_dir = video_path.parent / ".voxgrep_cache"
    cache_dir.mkdir(exist_ok=True)
    
    return str(cache_dir / f"{video_path.stem}_normalized.wav")


def should_normalize_audio(video_file: str, force: bool = False) -> bool:
    """
    Check if audio normalization is needed or cached.
    
    Args:
        video_file: Path to video file
        force: Force normalization even if cache exists
        
    Returns:
        True if normalization should be performed
    """
    if force:
        return True
    
    cache_path = get_normalized_cache_path(video_file)
    
    # If cache doesn't exist, we need to normalize
    if not os.path.exists(cache_path):
        return True
    
    # If cache is older than source, re-normalize
    if os.path.getmtime(cache_path) < os.path.getmtime(video_file):
        logger.info("Cached normalized audio is outdated, will re-normalize")
        return True
    
    logger.info(f"Using cached normalized audio: {cache_path}")
    return False
