"""
Interactive mode for VoxGrep CLI.

This module provides the main interactive wizard for configuring
and executing VoxGrep tasks through a menu-driven interface.
"""

from argparse import Namespace
from typing import List, Optional

import questionary

from .ui import console, print_session_summary

from .workflows import (
    select_input_files, check_transcripts, configure_transcription,
    settings_menu, post_export_menu, search_settings_menu,
    get_output_filename
)
from .commands import run_voxgrep_search, execute_args
from .ngrams import interactive_ngrams_workflow
from ..utils.config import (
    DEFAULT_WHISPER_MODEL, 
    DEFAULT_DEVICE, 
    DEFAULT_SEARCH_TYPE, 
    DEFAULT_IGNORED_WORDS
)
from ..utils.prefs import load_prefs, save_prefs


def create_default_args(input_files: List[str], prefs: dict) -> Namespace:
    """
    Create a Namespace with default arguments.
    
    Args:
        input_files: List of input file paths
        prefs: Preferences dictionary
        
    Returns:
        Namespace with default values
    """
    args = Namespace()
    args.inputfile = input_files
    args.outputfile = "supercut.mp4"
    args.export_clips = False
    args.write_vtt = False
    args.search = None
    args.searchtype = prefs.get("search_type", DEFAULT_SEARCH_TYPE)
    args.maxclips = 0
    args.randomize = False
    args.exact_match = False
    
    # Ignored words settings
    args.ignored_words = prefs.get("ignored_words", DEFAULT_IGNORED_WORDS)
    args.use_ignored_words = prefs.get("use_ignored_words", True)
    
    # Transcription settings
    args.padding = None
    args.sync = 0
    args.transcribe = False
    args.model = prefs.get("whisper_model", DEFAULT_WHISPER_MODEL)
    args.device = prefs.get("device", DEFAULT_DEVICE)
    args.compute_type = prefs.get("compute_type", "default")
    args.language = None
    args.prompt = None
    args.beam_size = prefs.get("beam_size", 5)
    args.best_of = prefs.get("best_of", 5)
    args.vad_filter = prefs.get("vad_filter", True)
    args.normalize_audio = prefs.get("normalize_audio", False)
    args.sphinxtranscribe = False
    args.ngrams = 0
    args.preview = prefs.get("preview", False)
    args.demo = prefs.get("demo", False)
    
    return args


def handle_search_workflow(args: Namespace) -> bool:
    """
    Handle the search workflow including preview, export, and settings.
    
    Args:
        args: Namespace with search configuration
        
    Returns:
        True to continue main loop, False to exit
    """
    # Get search terms
    search_input = questionary.text("Enter search terms (comma separated):").ask()
    if not search_input:
        return True
    
    args.search = [s.strip() for s in search_input.split(',') if s.strip()]
    
    # Select search type
    args.searchtype = questionary.select(
        "Search Type",
        choices=["sentence", "fragment", "mash", "semantic"],
        default=args.searchtype
    ).ask()

    # Search workflow loop
    while True:
        default_out = get_default_output_name(args.search)
        
        # Show menu
        action = questionary.select(
            "Next Step:",
            choices=[
                questionary.Choice("Preview Results (MPV)", value="preview"),
                questionary.Choice(f"Export Supercut (to {default_out}.mp4...)", value="export"),
                questionary.Separator(),
                questionary.Choice(f"Settings (Padding: {args.padding or 0}s, Max: {args.maxclips or 'All'})", value="settings"),
                questionary.Choice("Start Over (New Search)", value="cancel")
            ],
            default="preview"
        ).ask()
        
        if action == "cancel":
            return True

        if action == "preview":
            console.print("\n[bold yellow]Generating Preview...[/bold yellow]")
            result = run_voxgrep_search(
                files=args.inputfile,
                query=args.search,
                search_type=args.searchtype,
                output=args.outputfile,
                maxclips=args.maxclips,
                padding=args.padding,
                demo=False,
                random_order=args.randomize,
                resync=args.sync,
                export_clips=args.export_clips,
                write_vtt=args.write_vtt,
                preview=True,
                exact_match=args.exact_match
            )
            
            if isinstance(result, dict):
                print_session_summary(result)
            
            continue

        if action == "settings":
            search_settings_menu(args)
            continue

        if action == "export":
            args.preview = False
            args.demo = False
            args.outputfile = get_output_filename(args.search, default_out)
            
            # Run export with progress
            result = run_voxgrep_search(
                files=args.inputfile,
                query=args.search,
                search_type=args.searchtype,
                output=args.outputfile,
                maxclips=args.maxclips,
                padding=args.padding,
                demo=False,
                random_order=args.randomize,
                resync=args.sync,
                export_clips=args.export_clips,
                write_vtt=args.write_vtt,
                preview=False,
                exact_match=args.exact_match
            )
            
            if isinstance(result, dict) and result.get("success"):
                print_session_summary(result)
            
            # Post-export menu
            while result:
                post_action = post_export_menu(args.outputfile)
                
                if post_action == "edit":
                    break  # Back to search workflow loop
                elif post_action in ("new", "menu"):
                    return True  # Back to main menu
            
            if post_action == "edit":
                continue
            else:
                return True
    
    return True


def get_default_output_name(search_terms: Optional[List[str]]) -> str:
    """Get a safe default output name from search terms."""
    default_out = "supercut"
    if search_terms:
        safe_term = "".join([
            c if c.isalnum() or c in (' ', '-', '_') else '' 
            for c in search_terms[0]
        ]).strip().replace(' ', '_')
        if safe_term:
            default_out = safe_term
    return default_out


def interactive_mode() -> None:
    """
    Run an interactive wizard to gather arguments and execute tasks.
    """
    console.print("[bold yellow]Interactive Mode[/bold yellow]")
    console.print("Let's configure your task.\n")

    prefs = load_prefs()
    
    # Select input files
    input_files = select_input_files()
    if not input_files:
        return

    console.print(f"[green]Selected {len(input_files)} files.[/green]\n")

    # Main loop
    while True:
        args = create_default_args(input_files, prefs)
        
        # Main task selection
        task = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("Search", value="search"),
                questionary.Choice("Transcription Only", value="transcribe"),
                questionary.Choice("Calculate N-grams", value="ngrams"),
                questionary.Separator(),
                questionary.Choice("Settings (Ignored Words, etc.)", value="settings_menu"),
                questionary.Choice("Change Files", value="change_files"),
                questionary.Choice("Exit", value="exit")
            ],
            default="search"
        ).ask()

        if task is None or task == "exit":
            break
            
        if task == "change_files":
            return interactive_mode()  # Restart with new files

        if task == "settings_menu":
            ignored_words, use_ignored_words = settings_menu(prefs)
            args.ignored_words = ignored_words
            args.use_ignored_words = use_ignored_words
            continue

        # Check for transcription needs
        if task == "transcribe":
            args.transcribe = True
            configure_transcription(args, prefs)
        elif task != "search":
            # For ngrams, check if transcription is needed
            should_transcribe, missing_files = check_transcripts(args.inputfile)
            if should_transcribe:
                args.transcribe = True
                configure_transcription(args, prefs)
            elif missing_files and task == "ngrams":
                console.print("[bold red]Error: Cannot calculate n-grams without transcripts.[/bold red]")
                continue
        else:
            # For search, optionally transcribe
            should_transcribe, _ = check_transcripts(args.inputfile)
            if should_transcribe:
                args.transcribe = True
                configure_transcription(args, prefs)

        # Handle specific tasks
        try:
            # Execute transcription if requested/needed (before task-specific workflows)
            if args.transcribe:
                from .commands import run_transcription_whisper
                run_transcription_whisper(
                    args.inputfile,
                    args.model,
                    args.device,
                    args.compute_type,
                    args.language,
                    args.prompt,
                    getattr(args, 'beam_size', 5),
                    getattr(args, 'best_of', 5),
                    getattr(args, 'vad_filter', True),
                    getattr(args, 'normalize_audio', False)
                )
                console.print("[green]✓ Transcription complete[/green]\n")
                args.transcribe = False  # Reset flag

            if task == "search":
                if not handle_search_workflow(args):
                    break
            elif task == "ngrams":
                args.ngrams = int(questionary.text("Enter N for N-grams", default="1").ask())
                interactive_ngrams_workflow(args)
                console.print("\n[dim]--- Task Complete ---[/dim]\n")
            else:
                # Transcription only
                if not args.transcribe:  # Already done above if it was needed
                    console.print("\n[dim]--- Task Complete ---[/dim]\n")
                else:
                    execute_args(args)
                    console.print("\n[dim]--- Task Complete ---[/dim]\n")
        except KeyboardInterrupt:
            # User cancelled - just continue to menu
            console.print("\n[dim]Returning to menu...[/dim]\n")
            continue
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}\n")
            console.print("[dim]Returning to menu...[/dim]\n")
            continue
        
        # Save preferences (update existing prefs to preserve other keys)
        prefs.update({
            "device": args.device,
            "whisper_model": args.model,
            "search_type": args.searchtype,
            "preview": args.preview,
            "demo": args.demo,
            "ignored_words": args.ignored_words,
            "use_ignored_words": args.use_ignored_words
        })
        save_prefs(prefs)
