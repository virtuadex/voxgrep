"""
VoxGrep CLI - Command Line Interface

This is the main entry point for the VoxGrep command-line tool.
It provides both interactive and argument-based modes for video search.
"""

import sys
import argparse
import logging

try:
    from rich_argparse import RichHelpFormatter
    HelpFormatter = RichHelpFormatter
except ImportError:
    import argparse
    HelpFormatter = argparse.HelpFormatter
from rich.logging import RichHandler

from .ui import console, print_banner
from .interactive import interactive_mode
from .commands import execute_args
from ..modules.youtube import download_video
from .. import __version__
from ..utils.config import (
    DEFAULT_WHISPER_MODEL,
    DEFAULT_DEVICE,
    DEFAULT_COMPUTE_TYPE,
    DEFAULT_SEARCH_TYPE
)
from ..utils.prefs import load_prefs

# Configure logger with Rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
)
logger = logging.getLogger("voxgrep.cli")


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    prefs = load_prefs()
    
    parser = argparse.ArgumentParser(
        description='Generate a "supercut" of one or more video files by searching through subtitle tracks.',
        formatter_class=HelpFormatter
    )
    
    # Input/Output
    io_group = parser.add_argument_group("Input/Output Options")
    io_group.add_argument(
        "--input", "-i",
        dest="inputfile",
        nargs="*",
        required=False,  # Not required for --doctor or --version
        help="video file or files, or YouTube URLs",
    )
    io_group.add_argument(
        "--output", "-o",
        dest="outputfile",
        default="supercut.mp4",
        help="name of output file",
    )
    io_group.add_argument(
        "--export-clips", "-ec",
        dest="export_clips",
        action="store_true",
        help="Export individual clips instead of concatenating",
    )
    io_group.add_argument(
        "--export-vtt", "-ev",
        dest="write_vtt",
        action="store_true",
        help="Write a WebVTT file next to the output",
    )

    # Search
    search_group = parser.add_argument_group("Search Options")
    search_group.add_argument(
        "--search", "-s",
        dest="search",
        action="append",
        help="Search term (use multiple times for multiple queries)",
    )
    search_group.add_argument(
        "--search-type", "-st",
        dest="searchtype",
        default=prefs.get("search_type", DEFAULT_SEARCH_TYPE),
        choices=["sentence", "fragment", "mash", "semantic"],
        help=f"Type of search. Default: {prefs.get('search_type', DEFAULT_SEARCH_TYPE)}",
    )
    search_group.add_argument(
        "--max-clips", "-m",
        dest="maxclips",
        type=int,
        default=0,
        help="Maximum number of clips to use",
    )
    search_group.add_argument(
        "--randomize", "-r",
        action="store_true",
        help="Randomize the clip order",
    )
    search_group.add_argument(
        "--word-regexp", "-w",
        dest="exact_match",
        action="store_true",
        help="Match only whole words (regex strict matching)",
    )

    # Audio/Video processing
    proc_group = parser.add_argument_group("Processing Options")
    proc_group.add_argument(
        "--padding", "-p",
        dest="padding",
        type=float,
        help="Padding in seconds at start and end of each clip",
    )
    proc_group.add_argument(
        "--resyncsubs", "-rs",
        dest="sync",
        default=0,
        type=float,
        help="Subtitle re-sync delay +/- in seconds",
    )
    proc_group.add_argument(
        "--burn-in-subtitles", "-bs",
        dest="burn_in_subtitles",
        action="store_true",
        help="Burn subtitles into the exported video",
    )

    # Transcription
    trans_group = parser.add_argument_group("Transcription Options")
    trans_group.add_argument(
        "--transcribe", "-tr",
        dest="transcribe",
        action="store_true",
        help="Transcribe the video using Whisper",
    )
    trans_group.add_argument(
        "--translate",
        dest="translate",
        action="store_true",
        help="Translate the subtitles to English (Whisper only)",
    )
    trans_group.add_argument(
        "--stream",
        dest="stream",
        action="store_true",
        help="Process a live stream or URL in real-time (background processing)",
    )
    trans_group.add_argument(
        "--model", "-mo",
        dest="model",
        default=prefs.get("whisper_model", DEFAULT_WHISPER_MODEL),
        help=f"Whisper model name. Default: {prefs.get('whisper_model', DEFAULT_WHISPER_MODEL)}",
    )
    trans_group.add_argument(
        "--device", "-dev",
        dest="device",
        default=prefs.get("device", DEFAULT_DEVICE),
        help=f"Device to use for transcription (cpu, cuda, mlx). Default: {prefs.get('device', DEFAULT_DEVICE)}",
    )
    trans_group.add_argument(
        "--compute-type", "-ct",
        dest="compute_type",
        default=prefs.get("compute_type", DEFAULT_COMPUTE_TYPE),
        help=f"Compute type for transcription. Default: {prefs.get('compute_type', DEFAULT_COMPUTE_TYPE)}",
    )
    trans_group.add_argument(
        "--language", "-l",
        dest="language",
        help="Language of the video (Whisper only)",
    )
    trans_group.add_argument(
        "--initial-prompt", "-ip",
        dest="prompt",
        help="Initial prompt to guide transcription (Whisper only)",
    )
    trans_group.add_argument(
        "--sphinx-transcribe", "-str",
        dest="sphinxtranscribe",
        action="store_true",
        help="Transcribe using pocketsphinx (must be installed)",
    )
    trans_group.add_argument(
        "--beam-size",
        dest="beam_size",
        type=int,
        default=prefs.get("beam_size", 5),
        help=f"Beam size for transcription decoding (default: {prefs.get('beam_size', 5)})",
    )
    trans_group.add_argument(
        "--best-of",
        dest="best_of",
        type=int,
        default=prefs.get("best_of", 5),
        help=f"Number of candidates when sampling (default: {prefs.get('best_of', 5)})",
    )
    trans_group.add_argument(
        "--no-vad",
        dest="vad_filter",
        action="store_false",
        default=True,
        help="Disable Voice Activity Detection (VAD) filter",
    )
    trans_group.add_argument(
        "--normalize-audio",
        dest="normalize_audio",
        action="store_true",
        help="Normalize audio levels before transcription",
    )

    # Advanced
    adv_group = parser.add_argument_group("Advanced Options")
    adv_group.add_argument(
        "--ngrams", "-n",
        dest="ngrams",
        type=int,
        default=0,
        help="Return n-grams for the input videos",
    )
    adv_group.add_argument(
        "--preview", "-pr",
        action="store_true",
        help="Preview results in mpv (must be installed)",
    )
    adv_group.add_argument(
        "--demo", "-d",
        action="store_true",
        help="Show results without creating a supercut",
    )
    adv_group.add_argument(
        "--doctor",
        action="store_true",
        help="Run environment diagnostics to check installation health",
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"VoxGrep {__version__}",
    )

    return parser


def main() -> None:
    """
    Run the command line version of VoxGrep.
    """
    print_banner()

    # If no arguments provided, switch to interactive mode
    if len(sys.argv) == 1:
        interactive_mode()
        return

    # Parse command-line arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle doctor command first (diagnostic mode)
    if hasattr(args, 'doctor') and args.doctor:
        from .doctor import run_doctor
        sys.exit(run_doctor())

    # Handle Stream Mode
    if hasattr(args, 'stream') and args.stream:
        if not args.inputfile:
            parser.error("argument --input/-i is required for streaming")
        
        if len(args.inputfile) > 1:
            console.print("[red]Streaming mode only supports one URL at a time.[/red]")
            sys.exit(1)
            
        url = args.inputfile[0]
        if not (url.lower().startswith("http") or url.lower().startswith("rtmp")):
             console.print("[red]Streaming mode requires a URL input (http/https/rtmp).[/red]")
             sys.exit(1)
            
        try:
            from ..core.stream_handler import StreamHandler
            import time
            
            console.print(f"[bold cyan]Starting background stream processing for:[/bold cyan] {url}")
            console.print(f"[dim]Recording to: {args.outputfile}[/dim]")
            console.print("[dim]Press Ctrl+C to stop...[/dim]\n")
            
            def on_segment(segments):
                for seg in segments:
                    console.print(f"[green][{seg['start']:.1f}s -> {seg['end']:.1f}s][/green] {seg['content']}")
            
            handler = StreamHandler(callback=on_segment)
            handler.start_processing(
                url, 
                args.outputfile,
                device=args.device,
                model=args.model,
                compute_type=args.compute_type
            )
            
            while handler.running:
                time.sleep(0.5)
                
            console.print("\n[bold green]Stream processing complete.[/bold green]")
            sys.exit(0)
            
        except ImportError as ie:
             logger.error(f"Missing dependencies for streaming: {ie}")
             sys.exit(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping stream...[/yellow]")
            if 'handler' in locals():
                handler.stop()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Stream error: {e}")
            sys.exit(1)
    
    # Validate that --input is provided for non-diagnostic operations
    if not args.inputfile:
        parser.error("the following arguments are required: --input/-i")
    
    # Process inputs (handle URLs)
    processed_inputs = []
    for inp in args.inputfile:
        if inp.lower().startswith("http://") or inp.lower().startswith("https://"):
            try:
                console.print(f"[cyan]Found URL in input: {inp}[/cyan]")
                # Use a simple status spinner, yt-dlp is fast enough usually or we can rely on internal logs if things get stuck
                # But to show progress we use a custom hook
                with console.status(f"[bold cyan]Initializing download...[/bold cyan]") as status:
                    def progress_hook(d):
                        if d['status'] == 'downloading':
                            p = d.get('_percent_str', '').strip()
                            eta = d.get('_eta_str', '').strip()
                            status.update(f"[bold cyan]Downloading... {p} (ETA: {eta})[/bold cyan]")
                        elif d['status'] == 'finished':
                            status.update("[bold green]Download complete! Processing...[/bold green]")

                    filename = download_video(inp, progress_hooks=[progress_hook], quiet=True)
                    console.print(f"[green]✓ Downloaded:[/green] {filename}")
                    processed_inputs.append(filename)
            except Exception as e:
                logger.error(f"Download failed: {e}")
                console.print(f"[bold red]✗ Failed to download {inp}[/bold red]")
                sys.exit(1)
        else:
            processed_inputs.append(inp)
            
    args.inputfile = processed_inputs
    
    # Execute the command
    success = execute_args(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
