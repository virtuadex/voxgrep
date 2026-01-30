"""
Interactive workflow components for VoxGrep CLI.

This module contains reusable workflow functions for interactive mode,
such as file selection, settings management, and search workflows.

Most functions accept an optional CLIContext parameter for dependency
injection, enabling testability without actual user interaction.
"""

import os
import glob
from typing import Any, Optional, TYPE_CHECKING
from argparse import Namespace

import questionary

from .ui import console, open_file, open_folder
from ..utils.config import MEDIA_EXTENSIONS, DEFAULT_IGNORED_WORDS, DEFAULT_WHISPER_MODEL, DEFAULT_DEVICE
from ..utils import mpv_utils
from ..utils.helpers import ensure_directory_exists
from ..utils.prefs import load_prefs, save_prefs
from ..core.engine import find_transcript

if TYPE_CHECKING:
    from .io import CLIContext


def check_ytdlp_available() -> bool:
    """Check if yt-dlp is available in the system."""
    try:
        import yt_dlp
        return True
    except ImportError:
        return False


def download_from_url(url: str, output_dir: str = ".") -> str | None:
    """
    Download video from URL using yt-dlp, with robust error handling and cookie support.
    
    Args:
        url: URL to download from (YouTube, Vimeo, etc.)
        output_dir: Directory to save the downloaded file
        
    Returns:
        Path to the downloaded file, or None if failed
    """
    if not check_ytdlp_available():
        console.print("[bold red]Error:[/bold red] yt-dlp is not installed.")
        console.print("[dim]Install with: pip install yt-dlp[/dim]")
        return None
    
    # Import here to avoid circular dependencies
    from ..modules.youtube import download_video
    
    output_dir = os.path.abspath(output_dir)
    ensure_directory_exists(output_dir)

    console.print(f"\n[bold cyan]Fetching video info from:[/bold cyan] {url}")
    
    cookies_from_browser = None
    
    while True:
        try:
            filepath = None
            
            with console.status(f"[bold cyan]Downloading...{' (using cookies)' if cookies_from_browser else ''}[/bold cyan]") as status:
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        p = d.get('_percent_str', '').strip()
                        eta = d.get('_eta_str', '').strip()
                        status.update(f"[bold cyan]Downloading... {p} (ETA: {eta})[/bold cyan]")
                    elif d['status'] == 'finished':
                        status.update("[bold green]Finalizing download...[/bold green]")

                filepath = download_video(
                    url, 
                    output_template=f"{output_dir}/%(title)s.%(ext)s",
                    progress_hooks=[progress_hook],
                    quiet=True,
                    cookies_from_browser=cookies_from_browser
                )
            
            if filepath and os.path.exists(filepath):
                console.print(f"[bold green]✓ Downloaded:[/bold green] {os.path.basename(filepath)}")
                return filepath
            else:
                console.print("[bold red]Download reported success but file not found.[/bold red]")
                return None
                
        except Exception as e:
            console.print(f"\n[bold red]Download failed:[/bold red] {e}")
            
            # If we already tried with cookies, stop trying
            if cookies_from_browser:
                console.print("[red]Download failed even with cookies. Please check your browser login or the URL.[/red]")
                return None
            
            # Check if likely an auth/bot issue
            is_auth_error = any(x in str(e) for x in ["403", "Forbidden", "Sign in", "bot"])
            
            # Ask user if they want to retry with cookies
            msg = "Download failed (likely anti-bot protections)." if is_auth_error else "Download failed."
            
            if questionary.confirm(f"{msg} Try using browser cookies? (Requires you to be logged into YouTube on the selected browser)").ask():
                cookies_from_browser = questionary.select(
                    "Select browser to load cookies from:",
                    choices=["chrome", "firefox", "safari", "edge", "brave", "opera", "chromium"]
                ).ask()
                
                if not cookies_from_browser:
                    return None
                    
                console.print(f"[yellow]Retrying with cookies from {cookies_from_browser}...[/yellow]")
                continue
            else:
                return None


def select_input_files(ctx: Optional["CLIContext"] = None) -> list[str] | None:
    """
    Interactive file selection workflow with URL download support.

    Args:
        ctx: Optional CLI context for prompts

    Returns:
        List of selected file paths, or None if cancelled
    """
    prompts = ctx.prompts if ctx else None

    available_files = []
    for f in os.listdir("."):
        if os.path.isfile(f) and any(f.lower().endswith(ext) for ext in MEDIA_EXTENSIONS):
            available_files.append(f)

    available_files.sort()

    input_files = []

    # Build choice list
    select_choices = []

    # Always offer URL download option
    if check_ytdlp_available():
        select_choices.append(questionary.Choice("Download from URL (YouTube, etc.)", value="__url__"))
        select_choices.append(questionary.Separator())

    if available_files:
        if len(available_files) > 1:
            select_choices.append(questionary.Choice("--- ALL FILES ---", value="__all__"))
            select_choices.append(questionary.Choice("--- CHOOSE MULTIPLE... ---", value="__multiple__"))

        for f in available_files:
            select_choices.append(f)

        select_choices.append(questionary.Separator())
        select_choices.append(questionary.Choice("Enter path manually...", value="__manual__"))
    else:
        select_choices.append(questionary.Choice("Enter path or glob pattern...", value="__manual__"))

    if prompts:
        selection = prompts.select("Select input source:", select_choices)
    else:
        selection = questionary.select(
            "Select input source:",
            choices=select_choices,
            style=questionary.Style([('highlighted', 'fg:black bg:cyan bold')])
        ).ask()

    if selection is None:
        return None

    if selection == "__url__":
        if prompts:
            url = prompts.text("Enter video URL:")
        else:
            url = questionary.text(
                "Enter video URL:",
                validate=lambda x: len(x.strip()) > 0
            ).ask()

        if not url:
            return None

        downloaded_file = download_from_url(url.strip())
        if downloaded_file:
            input_files = [downloaded_file]
        else:
            return None

    elif selection == "__all__":
        input_files = available_files
    elif selection == "__multiple__":
        if prompts:
            input_files = prompts.checkbox(
                "Select multiple files (Space to toggle, Enter to confirm):",
                available_files
            )
        else:
            input_files = questionary.checkbox(
                "Select multiple files (Space to toggle, Enter to confirm):",
                choices=available_files
            ).ask()
        if not input_files:
            return None
    elif selection == "__manual__":
        if prompts:
            manual_path = prompts.text("Enter video file paths (comma separated, supports globs):")
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
    else:
        input_files = [selection]

    return input_files if input_files else None


def check_transcripts(
    input_files: list[str],
    ctx: Optional["CLIContext"] = None,
) -> tuple[bool, list[str]]:
    """
    Check which files are missing transcripts.

    Args:
        input_files: List of input file paths
        ctx: Optional CLI context for prompts

    Returns:
        Tuple of (should_transcribe, missing_files)
    """
    con = ctx.console if ctx else console

    missing_transcripts = []
    for f in input_files:
        if not find_transcript(f):
            missing_transcripts.append(f)

    should_transcribe = False
    if missing_transcripts:
        con.print(f"[yellow]Note: {len(missing_transcripts)} file(s) are missing transcripts.[/yellow]")
        if ctx:
            should_transcribe = ctx.prompts.confirm(
                "Transcribe missing files before processing?",
                default=True
            ) or False
        else:
            should_transcribe = questionary.confirm(
                "Transcribe missing files before processing?",
                default=True
            ).ask()

    return should_transcribe, missing_transcripts


def configure_transcription(
    args: Namespace,
    prefs: dict[str, Any],
    ctx: Optional["CLIContext"] = None,
) -> None:
    """
    Configure transcription settings interactively.

    Args:
        args: Namespace object to update
        prefs: Preferences dictionary
        ctx: Optional CLI context for prompts
    """
    prompts = ctx.prompts if ctx else None
    con = ctx.console if ctx else console

    if prompts:
        args.device = prompts.select(
            "Transcription Device",
            choices=["cpu", "cuda", "mlx"],
            default=prefs.get("device", DEFAULT_DEVICE)
        ) or DEFAULT_DEVICE
    else:
        args.device = questionary.select(
            "Transcription Device",
            choices=["cpu", "cuda", "mlx"],
            default=prefs.get("device", DEFAULT_DEVICE)
        ).ask()

    if prompts:
        args.model = prompts.select(
            "Whisper Model",
            choices=["tiny", "base", "small", "medium", "large-v3", "distil-large-v3"],
            default=prefs.get("whisper_model", DEFAULT_WHISPER_MODEL)
        ) or DEFAULT_WHISPER_MODEL
    else:
        args.model = questionary.select(
            "Whisper Model",
            choices=["tiny", "base", "small", "medium", "large-v3", "distil-large-v3"],
            default=prefs.get("whisper_model", DEFAULT_WHISPER_MODEL)
        ).ask()

    args.language = None
    if prompts:
        manual_lang = prompts.select(
            "Language",
            choices=[
                questionary.Choice("Auto-detect", value="auto"),
                questionary.Choice("Portuguese (pt)", value="pt"),
                questionary.Choice("English (en)", value="en"),
                questionary.Choice("Spanish (es)", value="es"),
                questionary.Choice("French (fr)", value="fr"),
                questionary.Choice("Custom code...", value="custom")
            ]
        )
    else:
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
        if prompts:
            args.language = prompts.text("Enter language code (e.g. 'de', 'it'):")
        else:
            args.language = questionary.text("Enter language code (e.g. 'de', 'it'):").ask()
    elif manual_lang != "auto":
        args.language = manual_lang

    # Ask about high accuracy mode
    if prompts:
        use_high_accuracy = prompts.confirm(
            "Enable High Accuracy Mode? (slower but better transcription)",
            default=prefs.get("high_accuracy_mode", False)
        ) or False
    else:
        use_high_accuracy = questionary.confirm(
            "Enable High Accuracy Mode? (slower but better transcription)",
            default=prefs.get("high_accuracy_mode", False)
        ).ask()

    # Update prefs
    prefs["high_accuracy_mode"] = use_high_accuracy

    if use_high_accuracy:
        # Apply high accuracy settings
        args.beam_size = 10  # Higher beam size
        args.best_of = 10
        args.vad_filter = True
        con.print("[green]High Accuracy Mode enabled (beam_size=10, VAD enabled)[/green]")
    else:
        # Use default/saved settings
        args.beam_size = prefs.get("beam_size", 5)
        args.best_of = prefs.get("best_of", 5)
        args.vad_filter = prefs.get("vad_filter", True)

    # Update prefs with specific settings (which might have been set by high accuracy)
    prefs["beam_size"] = args.beam_size
    prefs["best_of"] = args.best_of
    prefs["vad_filter"] = args.vad_filter

    # Ask about audio normalization
    if prompts:
        args.normalize_audio = prompts.confirm(
            "Normalize audio levels? (improves accuracy for uneven volumes)",
            default=prefs.get("normalize_audio", False)
        ) or False
    else:
        args.normalize_audio = questionary.confirm(
            "Normalize audio levels? (improves accuracy for uneven volumes)",
            default=prefs.get("normalize_audio", False)
        ).ask()

    prefs["normalize_audio"] = args.normalize_audio

    if args.normalize_audio:
        con.print("[green]Audio normalization enabled (loudnorm filter)[/green]")

    # Ask about project-specific vocabulary
    project_vocab = prefs.get("project_vocabulary", [])
    if project_vocab:
        if prompts:
            use_vocab = prompts.confirm(
                f"Use saved project vocabulary? ({len(project_vocab)} terms)",
                default=True
            ) or False
        else:
            use_vocab = questionary.confirm(
                f"Use saved project vocabulary? ({len(project_vocab)} terms)",
                default=True
            ).ask()
        if use_vocab:
            args.prompt = ", ".join(project_vocab)
            con.print(f"[dim]Using vocabulary: {args.prompt[:100]}...[/dim]")
    else:
        if prompts:
            add_vocab = prompts.confirm(
                "Add project-specific vocabulary? (names, terms, slang)",
                default=False
            ) or False
        else:
            add_vocab = questionary.confirm(
                "Add project-specific vocabulary? (names, terms, slang)",
                default=False
            ).ask()
        if add_vocab:
            if prompts:
                vocab_input = prompts.text("Enter terms (comma separated):", default="")
            else:
                vocab_input = questionary.text(
                    "Enter terms (comma separated):",
                    default=""
                ).ask()
            if vocab_input:
                vocab_list = [v.strip() for v in vocab_input.split(",") if v.strip()]
                args.prompt = ", ".join(vocab_list)
                # Save to prefs
                prefs["project_vocabulary"] = vocab_list
                if ctx:
                    ctx.prefs_saver(prefs)
                else:
                    save_prefs(prefs)
                con.print("[green]Vocabulary saved for future use[/green]")



def settings_menu(
    prefs: dict[str, Any],
    ctx: Optional["CLIContext"] = None,
) -> tuple[list[str], bool]:
    """
    Interactive settings menu for ignored words and filters.

    Args:
        prefs: Preferences dictionary
        ctx: Optional CLI context for prompts

    Returns:
        Tuple of (ignored_words_list, use_ignored_words_flag)
    """
    prompts = ctx.prompts if ctx else None
    con = ctx.console if ctx else console
    prefs_saver = ctx.prefs_saver if ctx else save_prefs

    ignored_words = prefs.get("ignored_words", DEFAULT_IGNORED_WORDS)
    use_ignored_words = prefs.get("use_ignored_words", True)

    while True:
        current_ignored = ", ".join(ignored_words)
        status_text = "ENABLED" if use_ignored_words else "DISABLED"

        if prompts:
            action = prompts.select(
                "Settings",
                choices=[
                    questionary.Choice(f"Filter Ignored Words [{status_text}]", value="toggle_filter"),
                    questionary.Choice("Edit Ignored Words List", value="edit_ignored"),
                    questionary.Separator(),
                    questionary.Choice("Back", value="back")
                ]
            )
        else:
            action = questionary.select(
                "Settings",
                choices=[
                    questionary.Choice(f"Filter Ignored Words [{status_text}]", value="toggle_filter"),
                    questionary.Choice("Edit Ignored Words List", value="edit_ignored"),
                    questionary.Separator(),
                    questionary.Choice("Back", value="back")
                ]
            ).ask()

        if action == "back" or action is None:
            break

        if action == "toggle_filter":
            use_ignored_words = not use_ignored_words
            prefs["use_ignored_words"] = use_ignored_words
            prefs_saver(prefs)
            continue

        if action == "edit_ignored":
            con.print(f"\n[yellow]Current Ignored Words:[/yellow] {current_ignored}\n")
            if prompts:
                new_ignored = prompts.text(
                    "Enter ignored words (comma separated, leave empty to clear):",
                    default=current_ignored
                ) or ""
            else:
                new_ignored = questionary.text(
                    "Enter ignored words (comma separated, leave empty to clear):",
                    default=current_ignored
                ).ask() or ""
            ignored_words = [w.strip() for w in new_ignored.split(",") if w.strip()]
            prefs["ignored_words"] = ignored_words
            prefs_saver(prefs)
            con.print("[green]Settings saved.[/green]\n")

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


def _validate_padding(value: str) -> bool | str:
    """Validate padding input is a non-negative number."""
    try:
        num = float(value)
        if num < 0:
            return "Padding cannot be negative"
        if num > 60:
            return "Padding over 60 seconds is likely a mistake"
        return True
    except ValueError:
        return "Please enter a valid number"


def _validate_maxclips(value: str) -> bool | str:
    """Validate max clips input is a non-negative integer."""
    try:
        num = int(value)
        if num < 0:
            return "Max clips cannot be negative"
        return True
    except ValueError:
        return "Please enter a valid integer"


def search_settings_menu(
    args: Namespace,
    ctx: Optional["CLIContext"] = None,
) -> None:
    """
    Configure search-specific settings (padding, max clips, randomize).

    Args:
        args: Namespace object to update
        ctx: Optional CLI context for prompts
    """
    prompts = ctx.prompts if ctx else None

    if prompts:
        padding_str = prompts.text(
            "Padding (seconds):",
            default=str(args.padding or 0),
            validate=_validate_padding
        ) or "0"
    else:
        padding_str = questionary.text(
            "Padding (seconds):",
            default=str(args.padding or 0),
            validate=_validate_padding
        ).ask()
    args.padding = float(padding_str) if padding_str else 0

    if prompts:
        maxclips_str = prompts.text(
            "Max Clips (0 for all):",
            default=str(args.maxclips),
            validate=_validate_maxclips
        ) or "0"
    else:
        maxclips_str = questionary.text(
            "Max Clips (0 for all):",
            default=str(args.maxclips),
            validate=_validate_maxclips
        ).ask()
    args.maxclips = int(maxclips_str) if maxclips_str else 0

    if prompts:
        args.randomize = prompts.confirm(
            "Randomize clip order?",
            default=args.randomize
        ) or False
    else:
        args.randomize = questionary.confirm(
            "Randomize clip order?",
            default=args.randomize
        ).ask()

    if prompts:
        args.burn_in_subtitles = prompts.confirm(
            "Burn-in Subtitles in output supercut?",
            default=getattr(args, 'burn_in_subtitles', False)
        ) or False
    else:
        args.burn_in_subtitles = questionary.confirm(
            "Burn-in Subtitles in output supercut?",
            default=getattr(args, 'burn_in_subtitles', False)
        ).ask()


def get_output_filename(
    search_terms: list[str],
    default_prefix: str = "supercut",
    ctx: Optional["CLIContext"] = None,
) -> str:
    """
    Get output filename from user, with smart default based on search terms.

    Args:
        search_terms: List of search terms
        default_prefix: Default prefix if no valid search term available
        ctx: Optional CLI context for prompts

    Returns:
        Output filename with .mp4 extension
    """
    prompts = ctx.prompts if ctx else None

    MAX_FILENAME_LENGTH = 100  # Reasonable limit for filenames

    default_out = default_prefix
    if search_terms:
        # Join all search terms with '+'
        combined_terms = "+".join(search_terms)
        # Sanitize: keep only alphanumeric, spaces, hyphens, underscores, and plus signs
        safe_term = "".join([
            c if c.isalnum() or c in (' ', '-', '_', '+') else ''
            for c in combined_terms
        ]).strip().replace(' ', '+')

        # Truncate if too long
        if safe_term and len(safe_term) > MAX_FILENAME_LENGTH:
            safe_term = safe_term[:MAX_FILENAME_LENGTH].rstrip('+')

        if safe_term:
            default_out = safe_term

    if prompts:
        out_name = prompts.text(
            f"Output Filename (default: {default_out})",
            default=""
        ) or ""
    else:
        out_name = questionary.text(
            f"Output Filename (default: {default_out})",
            default=""
        ).ask()

    if not out_name:
        out_name = default_out
    if not out_name.lower().endswith(".mp4"):
        out_name += ".mp4"

    return out_name


def _delete_files(files: list[str], current_selection: list[str]) -> int:
    """
    Helper to delete files and their transcripts, updating the selection list.
    
    Args:
        files: List of files to delete
        current_selection: The active selection list to update (remove deleted files from)

    Returns:
        Number of files successfully deleted
    """
    deleted_count = 0
    # Copy file list to avoid modification valid issues if passing current_selection itself
    # although we iterate over 'files', if 'files' IS 'current_selection', we need to be careful.
    # But current_selection is only modified, not iterated here.
    # The caller manages iteration safely.

    for f in files:
        try:
            # Delete the video file
            if os.path.exists(f):
                os.remove(f)
            
            # Delete associated transcript
            transcript_path = find_transcript(f)
            if transcript_path and os.path.exists(transcript_path):
                os.remove(transcript_path)
                console.print(f"[dim]  └─ Deleted transcript: {os.path.basename(transcript_path)}[/dim]")
            
            # Remove from selection list
            if f in current_selection:
                current_selection.remove(f)
            
            deleted_count += 1
            console.print(f"[green]Deleted: {os.path.basename(f)}[/green]")
        except OSError as e:
            console.print(f"[red]Failed to delete {os.path.basename(f)}: {e}[/red]")
            
    return deleted_count


def manage_files_menu(input_files: list[str]) -> list[str]:
    """
    Interactive menu to manage selected files (Action -> File Selection).
    Allows bulk actions on multiple files.
    
    Args:
        input_files: List of absolute file paths
        
    Returns:
        Updated list of file paths
    """
    current_files = input_files.copy()
    
    while True:
        if not current_files:
            console.print("[yellow]No files remaining in selection.[/yellow]")
            return []

        console.print("\n[bold]Current Selection:[/bold]")
        for i, f in enumerate(current_files, 1):
            name = os.path.basename(f)
            console.print(f"  {i}. {name} [dim]({f})[/dim]")
        
        # Action First Menu
        action = questionary.select(
            "What do you want to do with these files?",
            choices=[
                "Back to Main Menu",
                questionary.Separator(),
                "Unselect Files (Bulk selection)",
                "Delete Files (Bulk selection from disk)",
                "Unselect ALL Files (Immediate)",
                "Delete ALL Files (Immediate Permanent)",
                questionary.Separator(),
                "Rename a File",
                "Preview a File (MPV)",
                "Reveal File in Explorer",
                "Open Transcript",
            ]
        ).ask()
        
        if not action or action == "Back to Main Menu":
            break
            
        # --- Immediate ALL Actions ---
        if "ALL" in action:
            if action.startswith("Unselect ALL"):
                if questionary.confirm(f"Remove ALL {len(current_files)} files from selection?").ask():
                    current_files.clear()
                    console.print("[green]All files removed from selection.[/green]")
                    return []
            
            elif action.startswith("Delete ALL"):
                console.print(f"[bold red]WARNING: This will PERMANENTLY DELETE ALL {len(current_files)} files from disk![/bold red]")
                if questionary.confirm(f"Are you sure you want to DELETE ALL {len(current_files)} files?").ask():
                    # We pass a copy because _delete_files helps modify current_files
                    _delete_files(current_files.copy(), current_files)
                    return current_files
        
        # --- Bulk Actions (Selection) ---
        elif "Bulk" in action:
            # Create choices for checkbox
            file_choices = [
                questionary.Choice(os.path.basename(f), value=f) 
                for f in current_files
            ]
            
            selected_files = questionary.checkbox(
                f"Select files to {action.split(' ')[0].lower()}:",
                choices=file_choices
            ).ask()
            
            if not selected_files:
                continue
                
            if action.startswith("Unselect"):
                if questionary.confirm(f"Remove {len(selected_files)} files from list?").ask():
                    for f in selected_files:
                        if f in current_files:
                            current_files.remove(f)
                    console.print(f"[green]Removed {len(selected_files)} files from selection.[/green]")

            elif action.startswith("Delete"):
                console.print(f"[bold red]WARNING: This will PERMANENTLY DELETE {len(selected_files)} files from disk![/bold red]")
                if questionary.confirm(f"Are you sure you want to DELETE {len(selected_files)} files?").ask():
                    _delete_files(selected_files, current_files)
    
        # --- Single Selection Actions ---
        else:
             # Reuse single selection logic
            target_file = None
            if len(current_files) == 1:
                target_file = current_files[0]
            else:
                 target_file = questionary.select(
                    "Select file:",
                    choices=[questionary.Choice(os.path.basename(f), value=f) for f in current_files]
                ).ask()
            
            if not target_file:
                continue
                
            if action.startswith("Rename"):
                new_name = questionary.text("New filename:", default=os.path.basename(target_file)).ask()
                if new_name and new_name != os.path.basename(target_file):
                    dir_path = os.path.dirname(target_file)
                    new_path = os.path.join(dir_path, new_name)
                    if os.path.exists(new_path):
                        console.print(f"[red]Error: '{new_name}' already exists.[/red]")
                    else:
                        try:
                            os.rename(target_file, new_path)
                            idx = current_files.index(target_file)
                            current_files[idx] = new_path
                            console.print(f"[green]Renamed to '{new_name}'[/green]")
                        except OSError as e:
                            console.print(f"[red]Rename failed: {e}[/red]")

            elif action.startswith("Preview"):
                 if mpv_utils.check_mpv_available():
                     success = mpv_utils.launch_mpv_file(target_file)
                     if not success:
                         console.print("[red]Failed to launch MPV. Check log for details.[/red]")
                 else:
                     console.print("[yellow]MPV not found. Cannot preview.[/yellow]")
                     console.print(mpv_utils.get_mpv_install_instructions())

            elif action.startswith("Reveal"):
                open_folder(os.path.dirname(target_file))

            elif action.startswith("Open Transcript"):
                t_path = find_transcript(target_file)
                if t_path and os.path.exists(t_path):
                    open_file(t_path)
                    console.print(f"[green]Opened transcript: {os.path.basename(t_path)}[/green]")
                else:
                    console.print("[yellow]No transcript found for this file.[/yellow]")

    return current_files
