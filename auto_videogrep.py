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

def run_whisper(video_path, model="medium", language=None, prompt=None):
    """
    Runs OpenAI Whisper on the video file to generate an SRT file.
    """
    logger.info(f"[+] Transcribing '{video_path}' using Whisper (model: {model})...")
    
    if language:
        logger.info(f"[+] Language specified: {language}")
    else:
        logger.info("[+] Language not specified. Whisper will auto-detect from the first 30s.")

    # Whisper command to output SRT directly to the same directory
    output_dir = os.path.dirname(os.path.abspath(video_path))
    
    cmd = [
        "whisper",
        video_path,
        "--model", model,
        "--output_format", "srt",
        "--output_dir", output_dir,
    ]

    if language:
        cmd.extend(["--language", language])
    
    if prompt:
        cmd.extend(["--initial_prompt", prompt])
        logger.info(f"[+] Using initial prompt: '{prompt}'")

    try:
        subprocess.run(cmd, check=True)
        logger.info("[+] Transcription complete.")
    except subprocess.CalledProcessError as e:
        logger.error(f"[-] Error running Whisper: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("[-] 'whisper' command not found. Please ensure openai-whisper is installed.")
        logger.error("[-] Try running: pip install openai-whisper")
        sys.exit(1)

from videogrep import videogrep as run_videogrep_lib

def run_videogrep(video_path, query, search_type="sentence", output_file="supercut.mp4"):
    """
    Runs videogrep using the generated SRT file.
    """
    logger.info(f"[+] Running videogrep for query: '{query}'...")
    
    try:
        run_videogrep_lib(
            files=video_path,
            query=query,
            search_type=search_type,
            output=output_file
        )
        logger.info(f"[+] Supercut created: {output_file}")
        
    except Exception as e:
        logger.error(f"[-] Error running videogrep: {e}")

def main():
    parser = argparse.ArgumentParser(description="Auto-transcribe with Whisper and run Videogrep.")
    parser.add_argument("video", help="Path to the video file.")
    parser.add_argument("query", help="Search query (regex supported).")
    parser.add_argument("--model", default="medium", help="Whisper model size (tiny, base, small, medium, large). Default: medium.")
    parser.add_argument("--language", help="Language code (e.g., pt, en). If omitted, Whisper auto-detects.")
    parser.add_argument("--prompt", help="Initial prompt to guide Whisper (useful for transcribing fillers like 'hmmm').")
    parser.add_argument("--search-type", default="sentence", choices=["sentence", "fragment"], help="Videogrep search type. Default: sentence.")
    parser.add_argument("--output", help="Output filename. If not provided, defaults to virtuacuts_[video_name].mp4")
    parser.add_argument("--force-transcribe", action="store_true", help="Force re-transcription even if SRT exists.")

    args = parser.parse_args()
    
    video_path = args.video
    if not os.path.exists(video_path):
        logger.error(f"[-] Video file not found: {video_path}")
        sys.exit(1)

    # Determine default output filename based on video name
    if not args.output:
        base_video_name = os.path.basename(video_path)
        video_name_no_ext = os.path.splitext(base_video_name)[0]
        output_file = f"virtuacuts_{video_name_no_ext}.mp4"
    else:
        output_file = args.output

    # Check for existing SRT
    base_name = os.path.splitext(video_path)[0]
    srt_path = base_name + ".srt"
    
    if os.path.exists(srt_path) and not args.force_transcribe:
        logger.info(f"[+] Found existing subtitle file: {srt_path}")
        logger.info("[+] Skipping transcription (use --force-transcribe to override).")
    else:
        # If the user is looking for thinking expressions, let's provide a default prompt 
        # unless they provided one.
        prompt = args.prompt
        if not prompt and ("h+m+" in args.query or "u+m+" in args.query):
            prompt = "Umm, hmmm, let me see... ah, yes."
            
        run_whisper(video_path, args.model, args.language, prompt)
        
    # Run videogrep
    run_videogrep(video_path, args.query, args.search_type, output_file)

if __name__ == "__main__":
    main()
