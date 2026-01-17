import sys
import json
import os
import argparse
from pathlib import Path

# Add the project root to sys.path so we can import videogrep
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import videogrep
from videogrep.modules import youtube
from videogrep import transcribe
# from videogrep import search as search_module # This caused the conflict

def emit(event, data):
    print(json.dumps({"event": event, "data": data}), flush=True)

def cmd_download(url, output_dir, device="cpu"):
    os.makedirs(output_dir, exist_ok=True)
    
    emit("status", "Downloading video...")
    try:
        # download_video signature: (url, output_template, format_code)
        # We need to construct the template to include the directory
        template = os.path.join(output_dir, "%(title)s.%(ext)s")
        video_path = youtube.download_video(url, output_template=template)
        emit("downloaded", {"path": video_path})
        
        emit("status", f"Transcribing on {device}...")
        transcribe.transcribe(
            videofile=video_path,
            model_name="large-v3",
            method="whisper",
            device=device, 
            compute_type="int8"
        )
        emit("transcribed", {"path": video_path})
        emit("complete", {"path": video_path})
        
    except Exception as e:
        emit("error", str(e))

def cmd_search(query, search_path, search_type="sentence"):
    try:
        segments = videogrep.search(search_path, query, search_type)
        # Format segments for JSON
        results = []
        for s in segments:
            results.append({
                "file": s["file"],
                "start": s["start"],
                "end": s["end"],
                "content": s["content"]
            })
        emit("search_results", results)
    except Exception as e:
        emit("error", str(e))

def cmd_list_library(library_path):
    # List video files that have corresponding transcripts
    library = []
    if not os.path.exists(library_path):
        emit("library", [])
        return
        
    for f in os.listdir(library_path):
        if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.mp3')):
            video_path = os.path.join(library_path, f)
            if videogrep.find_transcript(video_path):
                stats = os.stat(video_path)
                library.append({
                    "path": video_path,
                    "name": f,
                    "size": f"{stats.st_size / (1024*1024):.1f}MB",
                    "date": os.path.getmtime(video_path)
                })
    emit("library", library)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    down_parser = subparsers.add_parser("download")
    down_parser.add_argument("url")
    down_parser.add_argument("--output", default="downloads")
    down_parser.add_argument("--device", default="cpu")
    
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--path", default="downloads")
    search_parser.add_argument("--type", default="sentence")
    
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--path", default="downloads")
    
    args = parser.parse_args()
    
    if args.command == "download":
        cmd_download(args.url, args.output, args.device)
    elif args.command == "search":
        cmd_search(args.query, args.path, args.type)
    elif args.command == "list":
        cmd_list_library(args.path)
    else:
        parser.print_help()
