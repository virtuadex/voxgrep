import argparse
import logging
import os
from collections import Counter
from argparse import Namespace
import sys
import glob

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich import box

from ..formats import sphinx
from ..core import logic as voxgrep
from .. import __version__
from ..core.engine import get_ngrams, find_transcript
from ..utils.config import (
    DEFAULT_WHISPER_MODEL,
    DEFAULT_DEVICE,
    DEFAULT_COMPUTE_TYPE,
    DEFAULT_SEARCH_TYPE
)
from ..utils.helpers import setup_logger

# Initialize Rich Console
console = Console()

# Configure logger with Rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
)
logger = logging.getLogger("voxgrep.cli")


def print_banner():
    """Display the VoxGrep banner."""
    title = Text("VoxGrep", style="bold magenta")
    subtitle = Text(f"v{__version__} - Semantic Video Search", style="italic white")
    
    panel = Panel(
        Text.assemble(title, "\n", subtitle),
        box=box.ROUNDED,
        border_style="cyan",
        expand=False,
        padding=(1, 2)
    )
    console.print(panel)
    console.print()


def interactive_mode():
    """
    Run an interactive wizard to gather arguments.
    """
    import questionary
    from ..utils.config import MEDIA_EXTENSIONS
    from ..utils.prefs import load_prefs, save_prefs

    console.print("[bold yellow]Interactive Mode[/bold yellow]")
    console.print("Let's configure your task.\n")

    prefs = load_prefs()
    
    # 1. Input Files (Done once or until explicit change)
    available_files = []
    for f in os.listdir("."):
        if os.path.isfile(f) and any(f.lower().endswith(ext) for ext in MEDIA_EXTENSIONS):
            available_files.append(f)
    
    available_files.sort()
    
    input_files = []
    if available_files:
        select_choices = []
        if len(available_files) > 1:
            select_choices.append(questionary.Choice("--- ALL FILES ---", value="__all__"))
            select_choices.append(questionary.Choice("--- CHOOSE MULTIPLE... ---", value="__multiple__"))
        
        for f in available_files:
            select_choices.append(f)

        selection = questionary.select(
            "Select input file(s):",
            choices=select_choices,
            style=questionary.Style([('highlighted', 'fg:black bg:cyan bold')])
        ).ask()

        if selection is None:
            return

        if selection == "__all__":
            input_files = available_files
        elif selection == "__multiple__":
            input_files = questionary.checkbox(
                "Select multiple files (Space to toggle, Enter to confirm):",
                choices=available_files
            ).ask()
            if not input_files:
                return
        else:
            input_files = [selection]
    else:
        manual_path = questionary.text("Enter video file paths (comma separated, supports globs):").ask()
        if not manual_path:
            return
            
        for path in manual_path.split(','):
            path = path.strip()
            expanded = glob.glob(path)
            if expanded:
                input_files.extend(expanded)
            else:
                input_files.append(path)

    if not input_files:
        return

    console.print(f"[green]Selected {len(input_files)} files.[/green]\n")

    # MAIN LOOP
    while True:
        args = Namespace()
        args.inputfile = input_files
        
        # Defaults for each run
        args.outputfile = "supercut.mp4"
        args.export_clips = False
        args.write_vtt = False
        args.search = None
        args.searchtype = prefs.get("search_type", DEFAULT_SEARCH_TYPE)
        args.maxclips = 0
        args.randomize = False
        args.exact_match = False
        args.padding = None
        args.sync = 0
        args.transcribe = False
        args.model = prefs.get("whisper_model", DEFAULT_WHISPER_MODEL)
        args.device = prefs.get("device", DEFAULT_DEVICE)
        args.compute_type = DEFAULT_COMPUTE_TYPE
        args.language = None
        args.prompt = None
        args.sphinxtranscribe = False
        args.ngrams = 0
        args.preview = prefs.get("preview", False)
        args.demo = prefs.get("demo", False)

        # 2. Main Task
        task = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("Search", value="search"),
                questionary.Choice("Transcription Only", value="transcribe"),
                questionary.Choice("Calculate N-grams", value="ngrams"),
                questionary.Separator(),
                questionary.Choice("Change Files", value="change_files"),
                questionary.Choice("Exit", value="exit")
            ],
            default="search"
        ).ask()

        if task is None or task == "exit":
            break
            
        if task == "change_files":
            # Recurse or just re-run selection? 
            # Easiest is to just call interactive_mode again and return.
            return interactive_mode()

        if task == "ngrams":
            args.ngrams = int(questionary.text("Enter N for N-grams", default="1").ask())
        
        # 3. Transcription Check
        missing_transcripts = []
        for f in args.inputfile:
            if not find_transcript(f):
                missing_transcripts.append(f)
                
        should_transcribe = False
        
        if task == "transcribe":
            should_transcribe = True
        else:
            if missing_transcripts:
                console.print(f"[yellow]Note: {len(missing_transcripts)} file(s) are missing transcripts.[/yellow]")
                should_transcribe = questionary.confirm(
                    "Transcribe missing files before processing?", 
                    default=True
                ).ask()
            else:
                # Only ask if they want to RE-transcribe if they specifically didn't choose 'transcribe' task
                # but if they chose search/ngrams, usually they don't want to re-transcribe.
                # Let's keep it optional but hidden under a prompt.
                pass

        if should_transcribe:
            args.transcribe = True
            args.device = questionary.select(
                "Transcription Device", 
                choices=["cpu", "cuda", "mlx"], 
                default=args.device
            ).ask()
            
            args.model = questionary.select(
                "Whisper Model", 
                choices=["tiny", "base", "small", "medium", "large-v3", "distil-large-v3"], 
                default=args.model
            ).ask()
        
        if task == "ngrams" and not args.transcribe and missing_transcripts:
             console.print("[bold red]Error: Cannot calculate n-grams without transcripts.[/bold red]")
             continue # Go back to task selection

        if task == "search":
            # 4. Search Configuration
            search_input = questionary.text("Enter search terms (comma separated):").ask()
            if not search_input:
                continue
            args.search = [s.strip() for s in search_input.split(',') if s.strip()]
            
            args.searchtype = questionary.select(
                "Search Type",
                choices=["sentence", "fragment", "mash", "semantic"],
                default=args.searchtype
            ).ask()

            # 5. Output Configuration
            args.demo = questionary.confirm(
                "Run in Demo mode? (Show results only, no file generation)", 
                default=args.demo
            ).ask()
            
            if not args.demo:
                if questionary.confirm("Preview in MPV before rendering?", default=args.preview).ask():
                    args.preview = True
                else:
                    args.preview = False
                    # Generate smart default from search term
                    default_out = "supercut"
                    if args.search:
                        # Sanitize first search term for filename
                        # Replace spaces with underscores, remove unsafe chars
                        safe_term = "".join([c if c.isalnum() or c in (' ', '-', '_') else '' for c in args.search[0]]).strip().replace(' ', '_')
                        if safe_term:
                            default_out = safe_term

                    out_name = questionary.text(f"Output Filename (default: {default_out})", default="").ask()
                    if not out_name:
                        out_name = default_out
                    if not out_name.lower().endswith(".mp4"):
                        out_name += ".mp4"
                    args.outputfile = out_name
        
        # Save prefs (capturing device/model/search preferences)
        save_prefs({
            "device": args.device,
            "whisper_model": args.model,
            "search_type": args.searchtype,
            "preview": args.preview,
            "demo": args.demo
        })

        # EXECUTE
        execute_args(args)
        console.print("\n[dim]--- Task Complete ---[/dim]\n")



def execute_args(args):
    """
    Execute the logic based on parsed arguments.
    """
    if args is None:
        return True

    # Handle transcription (Moved to top priority)
    if args.sphinxtranscribe:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Transcribing (Sphinx)...", total=len(args.inputfile))
            for f in args.inputfile:
                sphinx.transcribe(f)
                progress.advance(task)
        
        # If the primary task was transcription (no ngrams or search), exit.
        if not args.search and args.ngrams == 0:
            return True

    if args.transcribe:
        from ..core import transcriber as transcribe
        if args.device == "mlx":
             with console.status("[bold blue]Starting MLX transcription...[/bold blue]", spinner="dots") as status:
                for i, f in enumerate(args.inputfile):
                    filename = os.path.basename(f)
                    status.update(f"[bold blue]Transcribing {filename} ({i+1}/{len(args.inputfile)}) using MLX...[/bold blue]")
                    transcribe.transcribe(
                        f, 
                        model_name=args.model, 
                        prompt=args.prompt, 
                        language=args.language, 
                        device=args.device, 
                        compute_type=args.compute_type
                    )
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                for i, f in enumerate(args.inputfile):
                    filename = os.path.basename(f)
                    task = progress.add_task(f"[cyan]Transcribing {filename} ({i+1}/{len(args.inputfile)})...", total=100)
                    
                    def update_progress(current_sec, total_sec):
                        """Callback to update Rich progress bar"""
                        percent = (current_sec / total_sec) * 100 if total_sec > 0 else 0
                        progress.update(task, completed=percent)
                    
                    transcribe.transcribe(
                        f, 
                        model_name=args.model, 
                        prompt=args.prompt, 
                        language=args.language, 
                        device=args.device, 
                        compute_type=args.compute_type,
                        progress_callback=update_progress
                    )
                    progress.update(task, completed=100)
        
        # If the primary task was transcription (no ngrams or search), exit.
        if not args.search and args.ngrams == 0:
            return True

    # Handle n-grams mode
    if args.ngrams > 0:
        with console.status(f"[bold green]Calculating {args.ngrams}-grams...", spinner="dots"):
            grams = get_ngrams(args.inputfile, args.ngrams)
            most_common = Counter(grams).most_common(100)
        
        table = Table(title=f"Top 100 {args.ngrams}-grams", box=box.SIMPLE)
        table.add_column("N-gram", style="cyan", no_wrap=True)
        table.add_column("Count", style="magenta", justify="right")

        for ngram, count in most_common:
            table.add_row(" ".join(ngram), str(count))
        
        console.print(table)
        
        # Interactive n-gram selection
        import questionary
        if questionary.confirm("\n🔍 Search for any of these n-grams?", default=False).ask():
            # Create choices from top 20 n-grams
            ngram_choices = [
                questionary.Choice(f"{' '.join(ngram)} ({count}x)", value=" ".join(ngram))
                for ngram, count in most_common[:20]
            ]
            
            selected_ngrams = questionary.checkbox(
                "Select n-grams to search (Space to toggle, Enter to confirm):",
                choices=ngram_choices
            ).ask()
            
            if selected_ngrams:
                console.print(f"\n[bold green]Searching for {len(selected_ngrams)} selected n-gram(s)...[/bold green]\n")
                
                # Create a new args object for the search
                search_args = Namespace()
                search_args.inputfile = args.inputfile
                search_args.search = selected_ngrams
                search_args.searchtype = "sentence"  # Use sentence search for phrases
                search_args.demo = questionary.confirm("Run in Demo mode?", default=True).ask()
                
                if not search_args.demo:
                    search_args.preview = questionary.confirm("Preview in MPV?", default=True).ask()
                    if not search_args.preview:
                        # Generate smart default from selected n-gram
                        default_ngram_out = "ngram_supercut"
                        if search_args.search:
                            safe_ngram = "".join([c if c.isalnum() or c in (' ', '-', '_') else '' for c in search_args.search[0]]).strip().replace(' ', '_')
                            if safe_ngram:
                                default_ngram_out = safe_ngram

                        out_name = questionary.text(f"Output Filename (default: {default_ngram_out})", default="").ask()
                        if not out_name:
                            out_name = default_ngram_out
                        if not out_name.lower().endswith(".mp4"):
                            out_name += ".mp4"
                        search_args.outputfile = out_name
                    else:
                        search_args.outputfile = "ngram_supercut.mp4"
                else:
                    search_args.preview = False
                    search_args.outputfile = "ngram_supercut.mp4"
                
                search_args.maxclips = 0
                search_args.padding = None
                search_args.randomize = False
                search_args.resync = 0
                search_args.export_clips = False
                search_args.write_vtt = False
                search_args.exact_match = False
                
                # Execute the search
                result = voxgrep.voxgrep(
                    files=search_args.inputfile,
                    query=search_args.search,
                    search_type=search_args.searchtype,
                    output=search_args.outputfile,
                    maxclips=search_args.maxclips,
                    padding=search_args.padding,
                    demo=search_args.demo,
                    random_order=search_args.randomize,
                    resync=search_args.resync,
                    export_clips=search_args.export_clips,
                    write_vtt=search_args.write_vtt,
                    preview=search_args.preview,
                    exact_match=search_args.exact_match,
                    console=console
                )
                
                if result and not search_args.demo and not search_args.preview:
                    panel = Panel(
                        Text.assemble(
                            ("N-gram Supercut Created!\n", "bold green"),
                            (f"Output: {os.path.abspath(search_args.outputfile)}", "white")
                        ),
                        title="Success",
                        border_style="green",
                        box=box.ROUNDED
                    )
                    console.print()
                    console.print(panel)
        
        return True

    # Validate search
    if not args.search:
        console.print("[bold red]Error:[/bold red] At least one search term is required.")
        sys.exit(1)

    # Execute voxgrep
    result = voxgrep.voxgrep(
        files=args.inputfile,
        query=args.search,
        search_type=args.searchtype,
        output=args.outputfile,
        maxclips=args.maxclips,
        padding=args.padding,
        demo=args.demo,
        random_order=args.randomize,
        resync=args.sync,
        export_clips=args.export_clips,
        write_vtt=args.write_vtt,
        preview=args.preview,
        exact_match=args.exact_match,
        console=console # Pass console for rich output
    )

    if result and not args.demo and not args.preview:
        panel = Panel(
            Text.assemble(
                ("Supercut Created Successfully!\n", "bold green"),
                (f"Output saved to: {os.path.abspath(args.outputfile)}", "white")
            ),
            title="Session Summary",
            border_style="green",
            box=box.ROUNDED
        )
        console.print()
        console.print(panel)


def main():
    """
    Run the command line version of VoxGrep
    """
    print_banner()

    if len(sys.argv) == 1:
        # No arguments provided, switch to interactive mode
        interactive_mode()
        return

    parser = argparse.ArgumentParser(
        description='Generate a "supercut" of one or more video files by searching through subtitle tracks.'
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

    args = parser.parse_args()
    
    # Handle doctor command first (diagnostic mode)
    if hasattr(args, 'doctor') and args.doctor:
        from .doctor import run_doctor
        sys.exit(run_doctor())
    
    # Validate that --input is provided for non-diagnostic operations
    if not args.inputfile:
        parser.error("the following arguments are required: --input/-i")
    
    execute_args(args)
