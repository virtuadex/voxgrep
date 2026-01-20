"""
VoxGrep CLI - Command Line Interface

This is the main entry point for the VoxGrep command-line tool.
It provides both interactive and argument-based modes for video search.
"""

import sys
import argparse
import logging

from rich_argparse import RichHelpFormatter
from rich.logging import RichHandler

from .ui import console, print_banner
from .interactive import interactive_mode
from .commands import execute_args
from .. import __version__
from ..utils.config import (
    DEFAULT_WHISPER_MODEL,
    DEFAULT_DEVICE,
    DEFAULT_COMPUTE_TYPE,
    DEFAULT_SEARCH_TYPE
)

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
    parser = argparse.ArgumentParser(
        description='Generate a "supercut" of one or more video files by searching through subtitle tracks.',
        formatter_class=RichHelpFormatter
    )
    
    # Input/Output
    io_group = parser.add_argument_group("Input/Output Options")
    io_group.add_argument(
        "--input", "-i",
        dest="inputfile",
        nargs="*",
        required=False,  # Not required for --doctor or --version
        help="video file or files",
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
        default=DEFAULT_SEARCH_TYPE,
        choices=["sentence", "fragment", "mash", "semantic"],
        help=f"Type of search. Default: {DEFAULT_SEARCH_TYPE}",
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

    # Transcription
    trans_group = parser.add_argument_group("Transcription Options")
    trans_group.add_argument(
        "--transcribe", "-tr",
        dest="transcribe",
        action="store_true",
        help="Transcribe the video using Whisper",
    )
    trans_group.add_argument(
        "--model", "-mo",
        dest="model",
        default=DEFAULT_WHISPER_MODEL,
        help=f"Whisper model name. Default: {DEFAULT_WHISPER_MODEL}",
    )
    trans_group.add_argument(
        "--device", "-dev",
        dest="device",
        default=DEFAULT_DEVICE,
        help=f"Device to use for transcription (cpu, cuda, mlx). Default: {DEFAULT_DEVICE}",
    )
    trans_group.add_argument(
        "--compute-type", "-ct",
        dest="compute_type",
        default=DEFAULT_COMPUTE_TYPE,
        help=f"Compute type for transcription. Default: {DEFAULT_COMPUTE_TYPE}",
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
    
    # Validate that --input is provided for non-diagnostic operations
    if not args.inputfile:
        parser.error("the following arguments are required: --input/-i")
    
    # Execute the command
    success = execute_args(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
