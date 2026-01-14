import re
import argparse
import os

# Set environment variables to store heavy models on D: drive
# This must be done before importing libraries that might use these variables
os.environ["WHISPER_CACHE_DIR"] = "D:/models/whisper"
os.environ["HF_HOME"] = "D:/models/huggingface"
os.environ["TORCH_HOME"] = "D:/models/torch"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
import subprocess
import sys
import logging
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# Initialize logger

# Initialize logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

from videogrep import transcribe

def run_whisper(video_path, model="large-v3", language=None, prompt=None, device="cpu", compute_type="int8"):
    """
    Runs faster-whisper (via videogrep.transcribe) on the video file to generate a JSON transcript.
    """
    logger.info(f"[+] Transcribing '{video_path}' using faster-whisper (model: {model}) on {device}...")
    
    if language:
        logger.info(f"[+] Language specified: {language}")
    else:
        logger.info("[+] Language not specified. Whisper will auto-detect.")

    try:
        # The transcribe module handles saving the JSON file
        transcribe.transcribe(
            videofile=video_path,
            model_name=model,
            method="whisper", # This maps to faster-whisper inside transcribe.py
            prompt=prompt,
            language=language,
            device=device,
            compute_type=compute_type
        )
        logger.info("[+] Transcription complete.")
    except Exception as e:
        logger.error(f"[-] Error running Whisper: {e}")
        sys.exit(1)

from videogrep import videogrep as run_videogrep_lib

def run_videogrep(video_path, query, search_type="sentence", output_file="supercut.mp4", padding=0.0, preview=False):
    """
    Runs videogrep using the generated SRT file.
    """
    logger.info(f"[+] Running videogrep for query: '{query}'...")
    
    try:
        run_videogrep_lib(
            files=video_path,
            query=query,
            search_type=search_type,
            output=output_file,
            padding=padding,
            preview=preview
        )
        if not preview:
            logger.info(f"[+] Supercut created: {output_file}")
        
    except Exception as e:
        logger.error(f"[-] Error running videogrep: {e}")

def download_video(url, output_dir="."):
    """
    Downloads video from a URL using yt-dlp.
    """
    logger.info(f"[+] Downloading video from {url}...")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'noplaylist': True,
        'restrictfilenames': True,  # Ensure filenames are ASCII-only
        'writesubtitles': False,    # Don't download manual subtitles by default to avoid rate limits
        'writeautomaticsub': False, # Don't download auto-generated subtitles by default
        'merge_output_format': 'mp4', # Ensure final container is mp4
        'ignoreerrors': True,       # Continue on download errors (like missing subtitles)
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                logger.error("[-] Failed to extract video info or download video.")
                sys.exit(1)
            filename = ydl.prepare_filename(info)
            # yt-dlp might have changed the extension during merge
            if not os.path.exists(filename):
                base_path = os.path.splitext(filename)[0]
                if os.path.exists(base_path + ".mp4"):
                    filename = base_path + ".mp4"
                else:
                    logger.error(f"[-] Downloaded file not found: {filename}")
                    sys.exit(1)
            
            logger.info(f"[+] Download complete: {filename}")
            return filename
    except Exception as e:
        logger.error(f"[-] Error downloading video: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Auto-transcribe with Whisper and run Videogrep.")
    parser.add_argument("video", help="Path to the video file.")
    parser.add_argument("query", help="Search query (regex supported).")
    parser.add_argument("--model", default="large-v3", help="Whisper model size (medium, large, large-v3). Default: large-v3.")
    parser.add_argument("--language", help="Language code (e.g., pt, en). If omitted, Whisper auto-detects.")
    parser.add_argument("--prompt", help="Initial prompt to guide Whisper (useful for transcribing fillers like 'hmmm').")
    parser.add_argument("--search-type", default="sentence", choices=["sentence", "fragment"], help="Videogrep search type. Default: sentence.")
    parser.add_argument("--padding", type=float, default=0.0, help="Padding in seconds to add to the start/end of each clip. Default: 0.0.")
    parser.add_argument("--device", default="cpu", help="Device to use for transcription (cpu, cuda). Default: cpu.")
    parser.add_argument("--compute-type", default="int8", help="Compute type for transcription (int8, float16, int8_float16). Default: int8.")
    parser.add_argument("--preview", action="store_true", help="Preview the cut in mpv instead of rendering a file.")
    parser.add_argument("--output", help="Output filename. If not provided, defaults to virtuacuts_[video_name].mp4")
    parser.add_argument("--force-transcribe", action="store_true", help="Force re-transcription even if SRT exists.")

    args = parser.parse_args()
    
    video_path = args.video
    
    # Check if input is a URL
    if re.match(r'^https?://', video_path):
        if yt_dlp is None:
            logger.error("[-] yt-dlp is not installed. Cannot download video from URL.")
            sys.exit(1)
        video_path = download_video(video_path)
    elif not os.path.exists(video_path):
        logger.error(f"[-] Video file not found: {video_path}")
        sys.exit(1)

    # Determine default output filename based on video name
    if not args.output:
        base_video_name = os.path.basename(video_path)
        video_name_no_ext = os.path.splitext(base_video_name)[0]
        output_file = f"virtuacuts_{video_name_no_ext}.mp4"
    else:
        output_file = args.output

    # Check for existing Transcript (JSON preferred for fragments)
    base_name = os.path.splitext(video_path)[0]
    json_path = base_name + ".json"
    
    if os.path.exists(json_path) and not args.force_transcribe:
        logger.info(f"[+] Found existing transcript file: {json_path}")
        logger.info("[+] Skipping transcription (use --force-transcribe to override).")
    else:
        # If the user is looking for thinking expressions, let's provide a default prompt 
        # unless they provided one.
        prompt = args.prompt
        if not prompt and ("h+m+" in args.query.lower() or "u+m+" in args.query.lower()):
            prompt = "Umm, hmmm, let me see... ah, yes."
            
        run_whisper(video_path, args.model, args.language, prompt, device=args.device, compute_type=args.compute_type)
        
    # Run videogrep
    run_videogrep(video_path, args.query, args.search_type, output_file, args.padding, args.preview)

if __name__ == "__main__":
    main()
