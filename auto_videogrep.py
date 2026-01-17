import re
import argparse
import os
import subprocess
import sys
import logging
from pathlib import Path

# Initialize logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

import videogrep
from videogrep.modules import youtube
from videogrep import transcribe


def run_whisper(video_path, model="large-v3", language=None, prompt=None, device="cpu", compute_type="int8"):
    """
    Runs faster-whisper (via videogrep.transcribe) on the video file to generate a JSON transcript.
    """
    logger.info(f"[+] Transcribing '{video_path}' using faster-whisper/mlx (model: {model}) on {device}...")
    
    if language:
        logger.info(f"[+] Language specified: {language}")
    else:
        logger.info("[+] Language not specified. Whisper will auto-detect.")

    try:
        # The transcribe module handles saving the JSON file
        transcribe.transcribe(
            videofile=video_path,
            model_name=model,
            method="whisper",
            prompt=prompt,
            language=language,
            device=device,
            compute_type=compute_type
        )
        logger.info("[+] Transcription complete.")
    except Exception as e:
        logger.error(f"[-] Error running Whisper: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Auto-transcribe with Whisper and run Videogrep.")
    parser.add_argument("video", help="Path to the video file or YouTube URL.")
    parser.add_argument("query", help="Search query (regex supported).")
    parser.add_argument("--model", default="large-v3", help="Whisper model size (medium, large, large-v3). Default: large-v3.")
    parser.add_argument("--language", help="Language code (e.g., pt, en). If omitted, Whisper auto-detects.")
    parser.add_argument("--prompt", help="Initial prompt to guide Whisper (useful for transcribing fillers like 'hmmm').")
    parser.add_argument("--search-type", default="sentence", choices=["sentence", "fragment"], help="Videogrep search type. Default: sentence.")
    parser.add_argument("--padding", type=float, default=0.0, help="Padding in seconds to add to the start/end of each clip. Default: 0.0.")
    parser.add_argument("--device", default="cpu", help="Device to use for transcription (cpu, cuda, mlx). Default: cpu.")
    parser.add_argument("--compute-type", default="int8", help="Compute type for transcription (int8, float16, int8_float16). Default: int8.")
    parser.add_argument("--preview", action="store_true", help="Preview the cut in mpv instead of rendering a file.")
    parser.add_argument("--output", help="Output filename. If not provided, defaults to supercut_[video_name].mp4")
    parser.add_argument("--force-transcribe", action="store_true", help="Force re-transcription even if transcript exists.")

    args = parser.parse_args()
    
    video_path = args.video
    
    # Check if input is a URL
    if re.match(r'^https?://', video_path):
        logger.info(f"[+] Downloading video from {video_path}...")
        try:
            video_path = youtube.download_video(video_path)
        except Exception as e:
            logger.error(f"[-] Failed to download video: {e}")
            sys.exit(1)
    elif not os.path.exists(video_path):
        logger.error(f"[-] Video file not found: {video_path}")
        sys.exit(1)

    # Determine default output filename based on video name
    if not args.output:
        base_video_name = os.path.basename(video_path)
        video_name_no_ext = os.path.splitext(base_video_name)[0]
        output_file = f"supercut_{video_name_no_ext}.mp4"
    else:
        output_file = args.output

    # Check for existing Transcript
    if not args.force_transcribe and videogrep.find_transcript(video_path):
        logger.info(f"[+] Found existing transcript file for: {video_path}")
        logger.info("[+] Skipping transcription (use --force-transcribe to override).")
    else:
        # Provide a default prompt for specific searches if none provided
        prompt = args.prompt
        if not prompt and ("h+m+" in args.query.lower() or "u+m+" in args.query.lower()):
            prompt = "Umm, hmmm, let me see... ah, yes."
            
        run_whisper(
            video_path, 
            args.model, 
            args.language, 
            prompt, 
            device=args.device, 
            compute_type=args.compute_type
        )
        
    # Run videogrep
    logger.info(f"[+] Running videogrep for query: '{args.query}'...")
    try:
        videogrep.videogrep(
            files=video_path,
            query=args.query,
            search_type=args.search_type,
            output=output_file,
            padding=args.padding,
            preview=args.preview
        )
        if not args.preview:
            logger.info(f"[+] Supercut created: {output_file}")
    except Exception as e:
        logger.error(f"[-] Error running videogrep: {e}")


if __name__ == "__main__":
    main()
