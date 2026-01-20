"""
Interactive workflow components for VoxGrep CLI.

This module contains reusable workflow functions for interactive mode,
such as file selection, settings management, and search workflows.
"""

import os
import glob
from typing import List, Optional, Dict, Any
from argparse import Namespace

import questionary

from .ui import console, open_file, open_folder
from ..utils.config import MEDIA_EXTENSIONS
from ..utils.prefs import load_prefs, save_prefs
from ..core.engine import find_transcript


def select_input_files() -> Optional[List[str]]:
    """
    Interactive file selection workflow.
    
    Returns:
        List of selected file paths, or None if cancelled
    """
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
            return None

        if selection == "__all__":
            input_files = available_files
        elif selection == "__multiple__":
            input_files = questionary.checkbox(
                "Select multiple files (Space to toggle, Enter to confirm):",
                choices=available_files
            ).ask()
            if not input_files:
                return None
        else:
            input_files = [selection]
    else:
        manual_path = questionary.text("Enter video file paths (comma separated, supports globs):").ask()
        if not manual_path:
            return None
            
        for path in manual_path.split(','):
            path = path.strip()
            expanded = glob.glob(path)
            if expanded:
                input_files.extend(expanded)
            else:
                input_files.append(path)

    return input_files if input_files else None


def check_transcripts(input_files: List[str]) -> tuple[bool, List[str]]:
    """
    Check which files are missing transcripts.
    
    Args:
        input_files: List of input file paths
        
    Returns:
        Tuple of (should_transcribe, missing_files)
    """
    missing_transcripts = []
    for f in input_files:
        if not find_transcript(f):
            missing_transcripts.append(f)
    
    should_transcribe = False
    if missing_transcripts:
        console.print(f"[yellow]Note: {len(missing_transcripts)} file(s) are missing transcripts.[/yellow]")
        should_transcribe = questionary.confirm(
            "Transcribe missing files before processing?", 
            default=True
        ).ask()
    
    return should_transcribe, missing_transcripts


def configure_transcription(args: Namespace, prefs: Dict[str, Any]) -> None:
    """
    Configure transcription settings interactively.
    
    Args:
        args: Namespace object to update
        prefs: Preferences dictionary
    """
    from ..utils.config import DEFAULT_WHISPER_MODEL, DEFAULT_DEVICE
    
    args.device = questionary.select(
        "Transcription Device", 
        choices=["cpu", "cuda", "mlx"], 
        default=prefs.get("device", DEFAULT_DEVICE)
    ).ask()
    
    args.model = questionary.select(
        "Whisper Model", 
        choices=["tiny", "base", "small", "medium", "large-v3", "distil-large-v3"], 
        default=prefs.get("whisper_model", DEFAULT_WHISPER_MODEL)
    ).ask()
    
    args.language = None
    manual_lang = questionary.select(
        "Language",
        choices=[
            questionary.Choice("Auto-detect", value="auto"),
            questionary.Choice("Portuguese (pt)", value="pt"),
            questionary.Choice("English (en)", value="en"),
            questionary.Choice("Spanish (es)", value="es"),
            questionary.Choice("French (fr)", value="fr"),
            questionary.Choice("Custom code...", value="custom")
        ]
    ).ask()
    
    if manual_lang == "custom":
        args.language = questionary.text("Enter language code (e.g. 'de', 'it'):").ask()
    elif manual_lang != "auto":
        args.language = manual_lang
    
    # Ask about high accuracy mode
    use_high_accuracy = questionary.confirm(
        "Enable High Accuracy Mode? (slower but  better transcription)",
        default=prefs.get("high_accuracy_mode", False)
    ).ask()
    
    if use_high_accuracy:
        # Apply high accuracy settings
        args.beam_size = 10  # Higher beam size
        args.best_of = 10
        args.vad_filter = True
        console.print("[green]✓ High Accuracy Mode enabled (beam_size=10, VAD enabled)[/green]")
    else:
        # Use default/saved settings
        args.beam_size = prefs.get("beam_size", 5)
        args.best_of = prefs.get("best_of", 5)
        args.vad_filter = prefs.get("vad_filter", True)
    
    # Ask about audio normalization
    args.normalize_audio = questionary.confirm(
        "Normalize audio levels? (improves accuracy for uneven volumes)",
        default=prefs.get("normalize_audio", False)
    ).ask()
    
    if args.normalize_audio:
        console.print("[green]✓ Audio normalization enabled (loudnorm filter)[/green]")
    
    # Ask about project-specific vocabulary
    project_vocab = prefs.get("project_vocabulary", [])
    if project_vocab:
        use_vocab = questionary.confirm(
            f"Use saved project vocabulary? ({len(project_vocab)} terms)",
            default=True
        ).ask()
        if use_vocab:
            args.prompt = ", ".join(project_vocab)
            console.print(f"[dim]Using vocabulary: {args.prompt[:100]}...[/dim]")
    else:
        add_vocab = questionary.confirm(
            "Add project-specific vocabulary? (names, terms, slang)",
            default=False
        ).ask()
        if add_vocab:
            vocab_input = questionary.text(
                "Enter terms (comma separated):",
                default=""
            ).ask()
            if vocab_input:
                vocab_list = [v.strip() for v in vocab_input.split(",") if v.strip()]
                args.prompt = ", ".join(vocab_list)
                # Save to prefs
                prefs["project_vocabulary"] = vocab_list
                save_prefs(prefs)
                console.print(f"[green]✓ Vocabulary saved for future use[/green]")



def settings_menu(prefs: Dict[str, Any]) -> tuple[List[str], bool]:
    """
    Interactive settings menu for ignored words and filters.
    
    Args:
        prefs: Preferences dictionary
        
    Returns:
        Tuple of (ignored_words_list, use_ignored_words_flag)
    """
    ignored_words = prefs.get("ignored_words", [
        "a", "o", "as", "os", "e", "é", "de", "do", "da", "dos", "das", 
        "em", "no", "na", "nos", "nas", "que", "para", "por", "com", 
        "um", "uma", "uns", "umas", "não", "se"
    ])
    use_ignored_words = prefs.get("use_ignored_words", True)
    
    while True:
        current_ignored = ", ".join(ignored_words)
        status_text = "ENABLED" if use_ignored_words else "DISABLED"
        
        action = questionary.select(
            "Settings",
            choices=[
                questionary.Choice(f"Filter Ignored Words [{status_text}]", value="toggle_filter"),
                questionary.Choice("Edit Ignored Words List", value="edit_ignored"),
                questionary.Separator(),
                questionary.Choice("Back", value="back")
            ]
        ).ask()
        
        if action == "back":
            break
        
        if action == "toggle_filter":
            use_ignored_words = not use_ignored_words
            prefs["use_ignored_words"] = use_ignored_words
            save_prefs(prefs)
            continue

        if action == "edit_ignored":
            console.print(f"\n[yellow]Current Ignored Words:[/yellow] {current_ignored}\n")
            new_ignored = questionary.text(
                "Enter ignored words (comma separated, leave empty to clear):", 
                default=current_ignored
            ).ask()
            ignored_words = [w.strip() for w in new_ignored.split(",") if w.strip()]
            prefs["ignored_words"] = ignored_words
            save_prefs(prefs)
            console.print("[green]Settings saved.[/green]\n")
    
    return ignored_words, use_ignored_words


def post_export_menu(output_file: str) -> str:
    """
    Show post-export action menu.
    
    Args:
        output_file: Path to the exported file
        
    Returns:
        Action string: "open", "folder", "edit", "new", "menu"
    """
    choices = [
        questionary.Choice("Open Result File", value="open"),
        questionary.Choice("Show in Folder", value="folder"),
        questionary.Separator(),
        questionary.Choice("Edit Settings & Re-Export", value="edit"),
        questionary.Choice("New Search", value="new"),
        questionary.Choice("Main Menu", value="menu")
    ]
    
    action = questionary.select("Task Complete. What next?", choices=choices).ask()
    
    if action == "open":
        open_file(output_file)
    elif action == "folder":
        open_folder(output_file)
    
    return action


def search_settings_menu(args: Namespace) -> None:
    """
    Configure search-specific settings (padding, max clips, randomize).
    
    Args:
        args: Namespace object to update
    """
    args.padding = float(questionary.text(
        "Padding (seconds):", 
        default=str(args.padding or 0)
    ).ask())
    
    args.maxclips = int(questionary.text(
        "Max Clips (0 for all):", 
        default=str(args.maxclips)
    ).ask())
    
    args.randomize = questionary.confirm(
        "Randomize clip order?", 
        default=args.randomize
    ).ask()


def get_output_filename(search_terms: List[str], default_prefix: str = "supercut") -> str:
    """
    Get output filename from user, with smart default based on search terms.
    
    Args:
        search_terms: List of search terms
        default_prefix: Default prefix if no valid search term available
        
    Returns:
        Output filename with .mp4 extension
    """
    default_out = default_prefix
    if search_terms:
        safe_term = "".join([
            c if c.isalnum() or c in (' ', '-', '_') else '' 
            for c in search_terms[0]
        ]).strip().replace(' ', '_')
        if safe_term:
            default_out = safe_term
    
    out_name = questionary.text(
        f"Output Filename (default: {default_out})", 
        default=""
    ).ask()
    
    if not out_name:
        out_name = default_out
    if not out_name.lower().endswith(".mp4"):
        out_name += ".mp4"
    
    return out_name
