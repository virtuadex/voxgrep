"""
Command execution logic for VoxGrep CLI.

This module handles the core execution of VoxGrep commands including
transcription, n-gram analysis, and search operations.
"""

import os
from collections import Counter
from argparse import Namespace
from typing import List, Tuple, Optional

from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, 
    TaskProgressColumn, TimeRemainingColumn
)
import logging

from .ui import console, print_ngrams_table, print_success_panel
from ..utils.helpers import setup_logger
from ..formats import sphinx
from ..core import logic as voxgrep
from ..core.engine import get_ngrams
from ..utils.prefs import load_prefs
from ..utils.config import DEFAULT_IGNORED_WORDS

logger = setup_logger(__name__)


def run_transcription_sphinx(input_files: List[str]) -> None:
    """
    Run Sphinx transcription with progress bar.
    
    Args:
        input_files: List of files to transcribe
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Transcribing (Sphinx)...", total=len(input_files))
        for f in input_files:
            try:
                sphinx.transcribe(f)
            except Exception as e:
                console.print(f"[red]✗ Failed to transcribe {os.path.basename(f)}: {e}[/red]")
                logger.error(f"Sphinx transcription failed for {f}: {e}")
            progress.advance(task)


def run_transcription_whisper(
    input_files: List[str], 
    model: str,
    device: str,
    compute_type: str,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    beam_size: int = 5,
    best_of: int = 5,
    vad_filter: bool = True,
    normalize_audio: bool = False,
    translate: bool = False
) -> None:
    """
    Run Whisper transcription with progress bar.
    
    Args:
        input_files: List of files to transcribe
        model: Whisper model name
        device: Device to use (cpu, cuda, mlx)
        compute_type: Compute type for transcription
        language: Optional language code
        prompt: Optional initial prompt
    """
    from ..core import transcriber as transcribe
    import questionary
    
    def ask_about_existing_transcript(existing_meta, current_meta):
        """Ask user whether to reuse existing transcript or regenerate."""
        console.print()
        console.print(f"[yellow]⚠ Found existing transcript created with different settings:[/yellow]")
        
        # Helper to format setting line
        def fmt_diff(key, label, default_val='unknown/default'):
            old = existing_meta.get(key, default_val)
            new = current_meta.get(key)
            if old != new:
                return f"\n  • [dim]{label}:[/dim] {old} → [bold]{new}[/bold]"
            return ""

        msg = ""
        msg += fmt_diff("model", "Model")
        msg += fmt_diff("device", "Device")
        msg += fmt_diff("beam_size", "Beam Size", 5)
        msg += fmt_diff("vad_filter", "VAD Filter", True)
        msg += fmt_diff("has_prompt", "Vocabulary Hint", False)
        msg += fmt_diff("translate", "Translate", False)
        
        console.print(msg)
        console.print()
        
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("Use existing transcript (faster)", value="reuse"),
                questionary.Choice("Regenerate with new settings (recommended for quality)", value="regenerate"),
                questionary.Choice("Cancel", value="cancel")
            ],
            default="regenerate"
        ).ask()
        
        if choice == "cancel":
            console.print("[yellow]Transcription cancelled.[/yellow]")
            raise KeyboardInterrupt()
        
        return choice == "reuse"
    
    if device == "mlx":
        console.print("[dim]Press Ctrl+C to cancel transcription at any time[/dim]\n")
        try:
            with console.status("[bold blue]Starting MLX transcription...[/bold blue]", spinner="dots") as status:
                for i, f in enumerate(input_files):
                    filename = os.path.basename(f)
                    status.update(f"[bold blue]Transcribing {filename} ({i+1}/{len(input_files)}) using MLX...[/bold blue]")
                    try:
                        transcribe.transcribe(
                            f, 
                            model_name=model, 
                            prompt=prompt, 
                            language=language, 
                            device=device, 
                            compute_type=compute_type,
                            on_existing_transcript=ask_about_existing_transcript,
                            beam_size=beam_size,
                            best_of=best_of,
                            vad_filter=vad_filter,
                            normalize_audio=normalize_audio,
                            translate=translate
                        )
                    except Exception as e:
                        console.print(f"\n[red]✗ Failed to transcribe {filename}: {e}[/red]")
                        logger.error(f"MLX transcription failed for {f}: {e}")
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Transcription cancelled by user. Partial results have been saved.[/yellow]")
            return
    else:
        console.print("[dim]Press Ctrl+C to cancel transcription at any time[/dim]\n")
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                for i, f in enumerate(input_files):
                    filename = os.path.basename(f)
                    original_desc = f"[cyan]Transcribing {filename} ({i+1}/{len(input_files)})..."
                    task = progress.add_task(original_desc, total=100)
                    
                    def update_progress(current_sec, total_sec, text: Optional[str] = None):
                        """Callback to update Rich progress bar"""
                        # Special handling for normalization phase
                        if text and "Normalizing audio" in text:
                            progress.update(task, description=f"[yellow]⧖ {text}[/yellow]", completed=0)
                            return
                            
                        percent = (current_sec / total_sec) * 100 if total_sec > 0 else 0
                        
                        # Revert description if we actually have progress
                        if percent > 0:
                             progress.update(task, description=original_desc)
                             
                        progress.update(task, completed=percent)
                        if text and "Normalizing audio" not in text:
                            # Print the text above the progress bar (scrolling ticker)
                            progress.console.print(f"[dim grey50]{text}[/dim grey50]")
                    
                    try:
                        transcribe.transcribe(
                            f, 
                            model_name=model, 
                            prompt=prompt, 
                            language=language, 
                            device=device, 
                            compute_type=compute_type,
                            progress_callback=update_progress,
                            on_existing_transcript=ask_about_existing_transcript,
                            beam_size=beam_size,
                            best_of=best_of,
                            vad_filter=vad_filter,
                            normalize_audio=normalize_audio,
                            translate=translate
                        )
                    except Exception as e:
                        console.print(f"\n[red]✗ Failed to transcribe {filename}: {e}[/red]")
                        
                    progress.update(task, completed=100)
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Transcription cancelled by user. Partial results have been saved.[/yellow]")
            return


def calculate_ngrams(
    input_files: List[str], 
    n: int,
    ignored_words: Optional[List[str]] = None,
    use_filter: bool = True
) -> Tuple[List[Tuple[tuple, int]], bool]:
    """
    Calculate and filter n-grams from input files.
    
    Args:
        input_files: List of files to analyze
        n: N value for n-grams
        ignored_words: Optional list of words to filter out
        use_filter: Whether to apply the filter
        
    Returns:
        Tuple of (most_common_ngrams, was_filtered)
    """
    with console.status(f"[bold green]Calculating {n}-grams...", spinner="dots"):
        # Get ignored words from prefs if not provided
        if ignored_words is None:
            prefs = load_prefs()
            ignored_words = prefs.get("ignored_words", DEFAULT_IGNORED_WORDS)
            use_filter = prefs.get("use_ignored_words", True)
        
        filter_list = ignored_words if use_filter else None
        
        # Pass filter list to core engine
        grams = get_ngrams(input_files, n, ignored_words=filter_list)
        
        most_common = Counter(grams).most_common(100)
        filtered = bool(filter_list)
        
        return most_common, filtered


def run_voxgrep_search(
    files: List[str],
    query: List[str],
    search_type: str,
    output: str,
    maxclips: int = 0,
    padding: Optional[float] = None,
    demo: bool = False,
    random_order: bool = False,
    resync: float = 0,
    export_clips: bool = False,
    write_vtt: bool = False,
    preview: bool = False,
    exact_match: bool = False,
    progress_callback = None,
    burn_in_subtitles: bool = False
) -> bool:
    """
    Execute voxgrep search with optional progress tracking.
    
    Args:
        files: List of input files
        query: Search query terms
        search_type: Type of search (sentence, fragment, mash, semantic)
        output: Output file path
        maxclips: Maximum number of clips (0 for all)
        padding: Padding in seconds
        demo: Demo mode (show results without creating output)
        random_order: Randomize clip order
        resync: Subtitle resync offset
        export_clips: Export individual clips
        write_vtt: Write WebVTT file
        preview: Preview mode (use MPV)
        exact_match: Exact word matching
        progress_callback: Optional progress callback function
        
    Returns:
        True if successful, False otherwise
    """
    if demo or preview:
        # No progress bar for demo/preview
        return voxgrep.voxgrep(
            files=files,
            query=query,
            search_type=search_type,
            output=output,
            maxclips=maxclips,
            padding=padding,
            demo=demo,
            random_order=random_order,
            resync=resync,
            export_clips=export_clips,
            write_vtt=write_vtt,
            preview=preview,
            exact_match=exact_match,
            console=console,
            burn_in_subtitles=burn_in_subtitles
        )
    else:
        # Use progress bar for actual processing
        with Progress(
            SpinnerColumn("bouncingBar", style="magenta"),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=None, style="black on white", complete_style="magenta", finished_style="green"),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True
        ) as progress:
            task_id = progress.add_task("[cyan]Creating Supercut...", total=100)
            
            def update_progress(p: float):
                progress.update(task_id, completed=p * 100)
            
            result = voxgrep.voxgrep(
                files=files,
                query=query,
                search_type=search_type,
                output=output,
                maxclips=maxclips,
                padding=padding,
                demo=demo,
                random_order=random_order,
                resync=resync,
                export_clips=export_clips,
                write_vtt=write_vtt,
                preview=preview,
                exact_match=exact_match,
                console=console,
                progress_callback=progress_callback or update_progress,
                burn_in_subtitles=burn_in_subtitles
            )
            
            if result and isinstance(result, bool):
                # Only show simple success if result is just True (legacy)
                # If it's a dict, the caller handles displaying the stats
                print_success_panel(output)
            
            return result


def execute_args(args: Namespace) -> bool:
    """
    Execute VoxGrep commands based on parsed arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        True if execution was successful
    """
    if args is None:
        return True

    # Handle Sphinx transcription
    if args.sphinxtranscribe:
        run_transcription_sphinx(args.inputfile)
        if not args.search and args.ngrams == 0:
            return True

    # Handle Whisper transcription
    if args.transcribe:
        run_transcription_whisper(
            args.inputfile,
            args.model,
            args.device,
            args.compute_type,
            args.language,
            args.prompt,
            args.beam_size,
            args.best_of,
            args.vad_filter,
            args.normalize_audio,
            translate=getattr(args, 'translate', False)
        )
        if not args.search and args.ngrams == 0:
            return True

    # Handle n-grams mode
    if args.ngrams > 0:
        ignored_words = getattr(args, 'ignored_words', None)
        use_filter = getattr(args, 'use_ignored_words', True)
        
        most_common, filtered = calculate_ngrams(
            args.inputfile, 
            args.ngrams,
            ignored_words,
            use_filter
        )
        
        print_ngrams_table(most_common, filtered, args.ngrams)
        
        # Note: Interactive n-gram selection is handled in interactive.py
        # This function only handles CLI mode n-gram calculation
        return True

    # Validate search
    if not args.search:
        console.print("[bold red]Error:[/bold red] At least one search term is required.")
        return False

    # Execute voxgrep search
    return run_voxgrep_search(
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
        burn_in_subtitles=getattr(args, 'burn_in_subtitles', False)
    )
