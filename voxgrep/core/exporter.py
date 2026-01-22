import os
import time
import gc
import platform
import subprocess
from typing import List, Optional, Callable, Dict, Any
from tqdm import tqdm
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips, TextClip, CompositeVideoClip

from ..formats import fcpxml
from ..utils.config import BATCH_SIZE
from ..utils.helpers import setup_logger, get_media_type
from ..utils.exceptions import ExportError, InvalidOutputFormatError, ExportFailedError

logger = setup_logger(__name__)


def get_encoding_params() -> Dict[str, Any]:
    """
    Detect available hardware encoders and return appropriate ffmpeg parameters.
    
    Returns:
        Dictionary of parameters to pass to write_videofile
    """
    params = {
        "codec": "libx264",
        "audio_codec": "aac",
        "bitrate": "8000k",
        "audio_bitrate": "192k",
        "preset": "medium",
        "threads": 4
    }
    
    try:
        # Check ffmpeg encoders
        result = subprocess.run(
            ["ffmpeg", "-encoders"], 
            capture_output=True, 
            text=True
        )
        output = result.stdout
        
        # macOS: VideoToolbox
        if platform.system() == "Darwin" and "h264_videotoolbox" in output:
            logger.info("Enabling hardware acceleration: h264_videotoolbox")
            params["codec"] = "h264_videotoolbox"
            # VideoToolbox doesn't use x264 presets, so we remove it to be safe
            if "preset" in params:
                del params["preset"]
            # Typically faster if we let the hardware handle bitrate allocation, 
            # but we keep bitrate for quality control.
            return params

        # Windows/Linux: NVIDIA NVENC
        if "h264_nvenc" in output:
            logger.info("Enabling hardware acceleration: h264_nvenc")
            params["codec"] = "h264_nvenc"
            params["preset"] = "p4" # Medium preset for NVENC
            return params
            
        # Intel QuickSync (optional fallback)
        if "h264_qsv" in output:
             logger.info("Enabling hardware acceleration: h264_qsv")
             params["codec"] = "h264_qsv"
             if "preset" in params:
                 del params["preset"]
             return params

    except Exception as e:
        logger.warning(f"Failed to detect hardware encoders: {e}. Falling back to libx264.")
        
    return params


def get_input_type(composition: List[dict]) -> str:
    """Determine if the composition is primarily audio or video."""
    filenames = set([c["file"] for c in composition])
    types = [get_media_type(f) for f in filenames]

    if "video" in types:
        return "video"
    if "audio" in types:
        return "audio"
    return "unknown"


def plan_output_strategy(composition: List[dict], outputfile: str) -> str:
    """
    Determine the export strategy based on input types and output format.
    
    Returns:
        'video', 'audio', or raises an error if incompatible.
    """
    input_type = get_input_type(composition)
    output_ext = os.path.splitext(outputfile)[1].lower()
    
    video_exts = ['.mp4', '.mkv', '.mov', '.avi', '.webm']
    audio_exts = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']

    if input_type == "audio" and output_ext in video_exts and outputfile != "supercut.mp4":
        raise InvalidOutputFormatError(
            "VoxGrep cannot convert audio input to video output. "
            "Please use an audio output format like .mp3 or .wav."
        )

    if input_type == "video" and output_ext not in audio_exts:
        return "video"
    
    if input_type == "audio" or output_ext in audio_exts:
        return "audio"
        
    return "video" # Default


def cleanup_log_files(outputfile: str):
    """Search for and remove temp log files found in the output directory."""
    d = os.path.dirname(os.path.abspath(outputfile))
    if os.path.exists(d):
        logfiles = [f for f in os.listdir(d) if f.endswith("ogg.log")]
        for f in logfiles:
            try:
                os.remove(os.path.join(d, f))
            except OSError:
                pass


def create_supercut(composition: List[dict], outputfile: str, progress_callback: Optional[Callable[[float], None]] = None, burn_in_subtitles: bool = False):
    """
    Creates a supercut from a composition of clips.
    """
    if not composition:
        return

    strategy = plan_output_strategy(composition, outputfile)
    all_filenames = set([c["file"] for c in composition])
    
    try:
        if strategy == "video":
            logger.info("[+] Creating video clips.")
            videofileclips = {f: VideoFileClip(f) for f in all_filenames}
            try:
                cut_clips = []
                iterable = composition if progress_callback else tqdm(composition, desc="Creating video clips", unit="clip")
                for i, c in enumerate(iterable):
                    clip_source = videofileclips[c["file"]]
                    start = max(0, c["start"])
                    end = min(clip_source.duration, c["end"])
                    
                    clip = clip_source.subclipped(start, end)
                    
                    if burn_in_subtitles:
                        # Create TextClip for subtitles
                        # Basic styling: white text with black stroke at the bottom
                        try:
                            txt_clip = TextClip(
                                text=c["content"],
                                font_size=40,
                                color='white',
                                stroke_color='black',
                                stroke_width=2,
                                method='caption',
                                size=(int(clip.w * 0.9), None) # 90% width
                            ).with_duration(clip.duration).with_position(('center', 0.85), relative=True) # Bottom 15%
                            
                            clip = CompositeVideoClip([clip, txt_clip])
                        except Exception as e:
                            logger.warning(f"Failed to create subtitle for clip {i}: {e}. Skipping subtitle.")

                    cut_clips.append(clip)
                    if progress_callback:
                        progress_callback((i + 1) / len(composition) * 0.05)

                logger.info("[+] Concatenating video clips.")
                final_clip = concatenate_videoclips(cut_clips, method="compose")

                logger.info("[+] Writing video output.")
                
                
                # Get hardware capabilities
                encoding_params = get_encoding_params()
                
                # For progress tracking: MoviePy's proglog integration is unreliable
                # Instead, we'll use a simple approach: suppress verbose output and update after completion
                
                write_kwargs = {
                    "temp_audiofile": f"{outputfile}_temp-audio{time.time()}.m4a",
                    "remove_temp": True,
                    "logger": 'bar',
                    **encoding_params
                }
                
                final_clip.write_videofile(outputfile, **write_kwargs)
                
                # Update progress to completion after write finishes
                if progress_callback:
                    progress_callback(1.0)
                
                final_clip.close()
                for clip in cut_clips:
                    clip.close()
            finally:
                for f in videofileclips:
                    videofileclips[f].close()

        else: # Audio strategy
            logger.info("[+] Creating audio clips.")
            audiofileclips = {f: AudioFileClip(f) for f in all_filenames}
            try:
                cut_clips = []
                iterable = composition if progress_callback else tqdm(composition, desc="Creating audio clips", unit="clip")
                for i, c in enumerate(iterable):
                    clip_source = audiofileclips[c["file"]]
                    start = max(0, c["start"])
                    end = min(clip_source.duration, c["end"])
                    
                    cut_clips.append(clip_source.subclipped(start, end))
                    if progress_callback:
                        progress_callback((i + 1) / len(composition) * 0.05)

                logger.info("[+] Concatenating audio clips.")
                final_clip = concatenate_audioclips(cut_clips)

                if outputfile.endswith(".mp4"):
                    outputfile = outputfile.replace(".mp4", ".mp3")
                    logger.info(f"[!] Changing output extension to .mp3: {outputfile}")

                logger.info(f"[+] Writing audio output: {outputfile}")
                
                final_clip.write_audiofile(outputfile, logger='bar')
                
                # Update progress to completion after write finishes
                if progress_callback:
                    progress_callback(1.0)
                
                final_clip.close()
                for clip in cut_clips:
                    clip.close()
            finally:
                for f in audiofileclips:
                    audiofileclips[f].close()

        if progress_callback:
            progress_callback(1.0)
            
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise ExportFailedError(f"Failed to create supercut: {e}") from e


def create_supercut_in_batches(composition: List[dict], outputfile: str, progress_callback: Optional[Callable[[float], None]] = None, burn_in_subtitles: bool = False):
    """
    Creates a supercut in batches to avoid memory issues.
    """
    total_clips = len(composition)
    num_batches = (total_clips + BATCH_SIZE - 1) // BATCH_SIZE
    batch_files = []
    
    strategy = plan_output_strategy(composition, outputfile)
    file_ext = ".mp4" if strategy == "video" else ".mp3"
    
    if strategy == "audio" and outputfile.endswith(".mp4"):
        outputfile = outputfile.replace(".mp4", ".mp3")

    pbar = None
    if not progress_callback:
        pbar = tqdm(total=num_batches, desc="Processing batches", unit="batch")

    try:
        for batch_idx in range(num_batches):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, total_clips)
            
            batch_filename = f"{outputfile}.batch{batch_idx}{file_ext}"
            
            def batch_progress(p):
                if progress_callback:
                    # Scale batch progress to 80% of total
                    overall_p = (batch_idx + p) / num_batches * 0.8
                    progress_callback(overall_p)
            
            try:
                create_supercut(composition[start_idx:end_idx], batch_filename, progress_callback=batch_progress, burn_in_subtitles=burn_in_subtitles)
                batch_files.append(batch_filename)
            except Exception as e:
                logger.error(f"Failed to create batch {batch_idx}: {e}")
                logger.warning(f"Skipping batch {batch_idx}, continuing with remaining batches...")
                # Continue processing remaining batches
                
            gc.collect()
            if pbar:
                pbar.update(1)
            
        if pbar:
            pbar.close()

        if not batch_files:
            raise ExportFailedError("All batches failed to create. Cannot produce output.")
        
        if len(batch_files) < num_batches:
            logger.warning(f"Only {len(batch_files)}/{num_batches} batches succeeded. Output may be incomplete.")

        if progress_callback:
            progress_callback(0.8)

        logger.info("[+] Concatenating all batches.")
        if strategy == "video":
            clips = [VideoFileClip(f) for f in batch_files]
            final = concatenate_videoclips(clips, method="compose")
            
            
            encoding_params = get_encoding_params()
            write_kwargs = {
                "temp_audiofile": f"{outputfile}_final_temp-audio.m4a",
                "remove_temp": True,
                "logger": 'bar',
                **encoding_params
            }
            
            final.write_videofile(outputfile, **write_kwargs)
            
            if progress_callback:
                progress_callback(1.0)
            final.close()
            for c in clips:
                c.close()
        else:
            clips = [AudioFileClip(f) for f in batch_files]
            final = concatenate_audioclips(clips)
            
            final.write_audiofile(outputfile, logger='bar')
            
            if progress_callback:
                progress_callback(1.0)
            final.close()
            for c in clips:
                c.close()

        if progress_callback:
            progress_callback(1.0)

    finally:
        for f in batch_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass
        cleanup_log_files(outputfile)


def export_individual_clips(composition: List[dict], outputfile: str, progress_callback: Optional[Callable[[float], None]] = None, burn_in_subtitles: bool = False):
    """Exports each clip in the composition as a separate file."""
    strategy = plan_output_strategy(composition, outputfile)
    all_filenames = set([c["file"] for c in composition])
    basename, ext = os.path.splitext(outputfile)
    
    if strategy == "audio" and ext == ".mp4":
        ext = ".mp3"

    results = {"success": 0, "failed": 0, "errors": []}
    
    try:
        if strategy == "video":
            videofileclips = {f: VideoFileClip(f) for f in all_filenames}
            try:
                iterable = composition if progress_callback else tqdm(composition, desc="Exporting individual clips", unit="clip")
                for i, c in enumerate(iterable):
                    try:
                        clip_source = videofileclips[c["file"]]
                        start = max(0, c["start"])
                        end = min(clip_source.duration, c["end"])
                        
                        clip = clip_source.subclipped(start, end)
                        
                        if burn_in_subtitles:
                            # Create TextClip for subtitles
                            try:
                                txt_clip = TextClip(
                                    text=c["content"],
                                    font_size=40,
                                    color='white',
                                    stroke_color='black',
                                    stroke_width=2,
                                    method='caption',
                                    size=(int(clip.w * 0.9), None)
                                ).with_duration(clip.duration).with_position(('center', 0.85), relative=True)
                                
                                clip = CompositeVideoClip([clip, txt_clip])
                            except Exception as e:
                                logger.warning(f"Failed to create subtitle for clip {i}: {e}")

                        clip_filename = f"{basename}_{str(i).zfill(5)}{ext}"
                        
                        clip_prog_start = i / len(composition)
                        clip_prog_end = (i + 1) / len(composition)
                        
                        
                        encoding_params = get_encoding_params()
                        
                        clip.write_videofile(
                            clip_filename,
                            remove_temp=True,
                            logger='bar',
                            **encoding_params
                        )
                        
                        if progress_callback:
                            progress_callback(clip_prog_end)
                        clip.close()
                        results["success"] += 1
                    except Exception as e:
                        logger.error(f"Failed to export clip {i}: {e}")
                        results["failed"] += 1
                        results["errors"].append(f"Clip {i}: {e}")
            finally:
                for f in videofileclips:
                    videofileclips[f].close()
        else:
            audiofileclips = {f: AudioFileClip(f) for f in all_filenames}
            try:
                iterable = composition if progress_callback else tqdm(composition, desc="Exporting individual clips", unit="clip")
                for i, c in enumerate(iterable):
                    try:
                        clip_source = audiofileclips[c["file"]]
                        start = max(0, c["start"])
                        end = min(clip_source.duration, c["end"])
                        
                        clip = clip_source.subclipped(start, end)
                        clip_filename = f"{basename}_{str(i).zfill(5)}{ext}"
                        clip_prog_start = i / len(composition)
                        clip_prog_end = (i + 1) / len(composition)
                        
                        clip.write_audiofile(clip_filename, logger='bar')
                        
                        if progress_callback:
                            progress_callback(clip_prog_end)
                        clip.close()
                        results["success"] += 1
                    except Exception as e:
                        logger.error(f"Failed to export clip {i}: {e}")
                        results["failed"] += 1
                        results["errors"].append(f"Clip {i}: {e}")
            finally:
                for f in audiofileclips:
                    audiofileclips[f].close()
    except Exception as e:
        logger.error(f"Batch setup failed: {e}")
        raise ExportFailedError(f"Failed to start export: {e}") from e
    
    return results


def export_m3u(composition: List[dict], outputfile: str):
    """Exports a VLC-compatible M3U playlist."""
    lines = ["#EXTM3U"]
    for c in composition:
        lines.append("#EXTINF:")
        lines.append(f"#EXTVLCOPT:start-time={c['start']}")
        lines.append(f"#EXTVLCOPT:stop-time={c['end']}")
        lines.append(c["file"])

    with open(outputfile, "w", encoding="utf-8") as outfile:
        outfile.write("\n".join(lines))


def export_mpv_edl(composition: List[dict], outputfile: str):
    """Exports an mpv-compatible EDL file."""
    lines = ["# mpv EDL v0"]
    for c in composition:
        abs_path = os.path.abspath(c['file'])
        duration = c['end'] - c['start']
        lines.append(f"{abs_path},{c['start']},{duration}")

    with open(outputfile, "w", encoding="utf-8") as outfile:
        outfile.write("\n".join(lines))


def export_xml(composition: List[dict], outputfile: str):
    """Exports a Final Cut Pro XML file."""
    fcpxml.compose(composition, outputfile)
