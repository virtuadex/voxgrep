"""
Interactive n-gram analysis workflow for VoxGrep CLI.

This module handles the complex interactive workflow for n-gram
calculation, selection, filtering, and search operations.
"""

from argparse import Namespace
from typing import List, Set, Tuple, Optional

import questionary

from .ui import console
from .workflows import get_output_filename, post_export_menu
from .commands import calculate_ngrams, run_voxgrep_search
from ..utils.config import DEFAULT_SEARCH_TYPE


def select_ngrams_single_mode(
    most_common: List[Tuple[tuple, int]], 
    selected_ngrams_set: Set[str]
) -> Tuple[Optional[str], Set[str]]:
    """
    Single-select mode for n-gram selection.
    
    Args:
        most_common: List of (ngram, count) tuples
        selected_ngrams_set: Currently selected n-grams
        
    Returns:
        Tuple of (action, updated_selection)
    """
    choices = []
    choices.append(questionary.Choice(
        "[+] Switch to Multi-Select Mode (Checkboxes)", 
        value="__SWITCH_MULTI__"
    ))
    
    if selected_ngrams_set:
        choices.append(questionary.Choice(
            f"  [!] Use Current Selection ({len(selected_ngrams_set)} items)", 
            value="__USE_EXISTING__"
        ))
    
    choices.append(questionary.Separator())
    
    for ngram, count in most_common:
        val = " ".join(ngram)
        label = f"{val} ({count}x)"
        choices.append(questionary.Choice(label, value=val))
    
    choices.append(questionary.Separator())
    choices.append(questionary.Choice("  [Back to Main Menu]", value="__EXIT__"))
    
    console.print("\n[bold cyan]--- Select N-gram (Type to filter, Enter to select) ---[/bold cyan]")
    selection = questionary.select(
        "Select n-gram:",
        choices=choices,
        style=questionary.Style([('highlighted', 'fg:cyan bold')]),
        use_indicator=True
    ).ask()
    
    if selection is None or selection == "__EXIT__":
        return "__EXIT__", selected_ngrams_set
        
    if selection == "__SWITCH_MULTI__":
        return "__SWITCH_MULTI__", selected_ngrams_set
        
    if selection == "__USE_EXISTING__":
        return "__DONE__", selected_ngrams_set

    # Immediate selection
    return "__DONE__", {selection}


def select_ngrams_multi_mode(
    most_common: List[Tuple[tuple, int]], 
    selected_ngrams_set: Set[str]
) -> Tuple[Optional[str], Set[str]]:
    """
    Multi-select mode for n-gram selection.
    
    Args:
        most_common: List of (ngram, count) tuples
        selected_ngrams_set: Currently selected n-grams
        
    Returns:
        Tuple of (action, updated_selection)
    """
    checkbox_choices = []
    
    for ngram, count in most_common:
        val = " ".join(ngram)
        label = f"{val} ({count}x)"
        is_checked = val in selected_ngrams_set
        checkbox_choices.append(questionary.Choice(label, value=val, checked=is_checked))
        
    checkbox_choices.append(questionary.Separator())
    checkbox_choices.append(questionary.Choice("  ✓ Done / Confirm Selection", value="__DONE__"))
    checkbox_choices.append(questionary.Choice("  [x] Switch back to Single Select", value="__SWITCH_SINGLE__"))
    
    console.print("\n[bold cyan]--- Multi-Select N-grams (Space to toggle, Enter to confirm) ---[/bold cyan]")
    page_selection = questionary.checkbox(
        "Select n-grams:",
        choices=checkbox_choices,
        style=questionary.Style([('highlighted', 'fg:cyan bold')])
    ).ask()
    
    if page_selection is None:
        return "__EXIT__", selected_ngrams_set
        
    # Handle control options
    if "__SWITCH_SINGLE__" in page_selection:
        # Capture valid selections before switching
        for val in page_selection:
            if val and not val.startswith("__"):
                selected_ngrams_set.add(val)
        return "__SWITCH_SINGLE__", selected_ngrams_set
        
    # Extract valid selections
    new_set = set()
    for val in page_selection:
        if val and not val.startswith("__"):
            new_set.add(val)
    
    if not new_set and "__DONE__" not in page_selection:
        # User hit enter without selecting anything
        console.print("[yellow]No n-grams selected.[/yellow]")
        return "__CONTINUE__", selected_ngrams_set
    
    return "__DONE__", new_set


def ngram_selection_phase(most_common: List[Tuple[tuple, int]]) -> Optional[List[str]]:
    """
    Handle the interactive n-gram selection phase.
    
    Args:
        most_common: List of (ngram, count) tuples
        
    Returns:
        List of selected n-grams, or None if cancelled
    """
    if not most_common:
        console.print("[yellow]No n-grams found.[/yellow]")
        return None
    
    console.print("\n[green]Select n-gram to search (or switch to Multi-Select):[/green]")
    
    selected_ngrams_set: Set[str] = set()
    mode = "single"
    
    while True:
        if mode == "single":
            action, selected_ngrams_set = select_ngrams_single_mode(most_common, selected_ngrams_set)
        else:
            action, selected_ngrams_set = select_ngrams_multi_mode(most_common, selected_ngrams_set)
        
        if action == "__EXIT__":
            return None
        elif action == "__SWITCH_MULTI__":
            mode = "multi"
        elif action == "__SWITCH_SINGLE__":
            mode = "single"
        elif action == "__DONE__":
            return list(selected_ngrams_set)
        elif action == "__CONTINUE__":
            continue


def ngram_action_phase(args: Namespace, selected_ngrams: List[str]) -> bool:
    """
    Handle the n-gram action phase (demo, preview, export).
    
    Args:
        args: Original arguments namespace
        selected_ngrams: List of selected n-grams
        
    Returns:
        True to go back to selection, False to exit
    """
    # Create search args
    search_args = Namespace()
    search_args.inputfile = args.inputfile
    search_args.search = selected_ngrams
    search_args.searchtype = "sentence"
    search_args.maxclips = 0
    search_args.padding = None
    search_args.randomize = False
    search_args.resync = 0
    search_args.sync = 0
    search_args.export_clips = False
    search_args.write_vtt = False
    search_args.exact_match = False
    search_args.ignored_words = getattr(args, 'ignored_words', [])
    search_args.use_ignored_words = getattr(args, 'use_ignored_words', True)
    
    # Show demo if requested
    if questionary.confirm("Show text results table (Demo Mode)?", default=True).ask():
        search_args.demo = True
        search_args.preview = False
        search_args.outputfile = "ngram_supercut.mp4"
        
        run_voxgrep_search(
            files=search_args.inputfile,
            query=search_args.search,
            search_type=search_args.searchtype,
            output=search_args.outputfile,
            maxclips=search_args.maxclips,
            padding=search_args.padding,
            demo=True,
            random_order=search_args.randomize,
            resync=search_args.sync,
            export_clips=search_args.export_clips,
            write_vtt=search_args.write_vtt,
            preview=False,
            exact_match=search_args.exact_match
        )
    
    # Reset demo flag
    search_args.demo = False
    
    # Action loop
    while True:
        console.print(f"\n[bold cyan]--- Action Menu ({' + '.join(selected_ngrams)}) ---[/bold cyan]")
        
        default_ngram_out = get_output_filename(search_args.search, "ngram_supercut")
        
        action = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("Preview Results (MPV)", value="preview"),
                questionary.Choice("Export Supercut", value="export"),
                questionary.Choice("Settings (Search Type, Padding, etc.)", value="settings"),
                questionary.Choice("Edit Selection (Add/Remove N-grams)", value="edit_selection"),
                questionary.Choice("Start Over (New Search)", value="start_over"),
                questionary.Choice("Cancel / Back", value="cancel")
            ]
        ).ask()
        
        if action == "cancel" or action == "start_over":
            return False
            
        if action == "edit_selection":
            return True  # Go back to selection phase
            
        if action == "settings":
            search_args.searchtype = questionary.select(
                "Search Type",
                choices=["sentence", "fragment", "mash", "semantic"],
                default=search_args.searchtype
            ).ask()

            p = questionary.text(
                "Padding (seconds, e.g., 0.5):", 
                default=str(search_args.padding) if search_args.padding else ""
            ).ask()
            search_args.padding = float(p) if p else None
            
            m = questionary.text("Max clips (0 for all):", default=str(search_args.maxclips)).ask()
            search_args.maxclips = int(m) if m else 0
            
            search_args.randomize = questionary.confirm(
                "Randomize order?", 
                default=search_args.randomize
            ).ask()
            
            console.print(f"[green]Settings updated. Search Type: {search_args.searchtype}[/green]")
            continue

        if action == "preview":
            search_args.preview = True
            search_args.outputfile = "preview_temp.mp4"
            run_voxgrep_search(
                files=search_args.inputfile,
                query=search_args.search,
                search_type=search_args.searchtype,
                output=search_args.outputfile,
                maxclips=search_args.maxclips,
                padding=search_args.padding,
                demo=False,
                random_order=search_args.randomize,
                resync=search_args.sync,
                export_clips=search_args.export_clips,
                write_vtt=search_args.write_vtt,
                preview=True,
                exact_match=search_args.exact_match
            )
            search_args.preview = False
            continue
            
        if action == "export":
            search_args.outputfile = get_output_filename(search_args.search, default_ngram_out)
            search_args.preview = False
            
            result = run_voxgrep_search(
                files=search_args.inputfile,
                query=search_args.search,
                search_type=search_args.searchtype,
                output=search_args.outputfile,
                maxclips=search_args.maxclips,
                padding=search_args.padding,
                demo=False,
                random_order=search_args.randomize,
                resync=search_args.sync,
                export_clips=search_args.export_clips,
                write_vtt=search_args.write_vtt,
                preview=False,
                exact_match=search_args.exact_match
            )
            
            if result:
                post_act = post_export_menu(search_args.outputfile)
                
                if post_act == "edit":
                    continue
                elif post_act == "new":
                    return False
                elif post_act == "main":
                    return False
            else:
                console.print("[red]Export failed.[/red]")
            continue


def interactive_ngrams_workflow(args: Namespace) -> None:
    """
    Main interactive workflow for n-gram analysis.
    
    Args:
        args: Arguments namespace with ngrams, inputfile, and filter settings
    """
    # Calculate n-grams
    most_common, filtered = calculate_ngrams(
        args.inputfile,
        args.ngrams,
        getattr(args, 'ignored_words', None),
        getattr(args, 'use_ignored_words', True)
    )
    
    from .ui import print_ngrams_table
    print_ngrams_table(most_common, filtered, args.ngrams)
    
    # Selection and action loop
    while True:
        selected_ngrams = ngram_selection_phase(most_common)
        
        if not selected_ngrams:
            return  # User cancelled or no selection
        
        # Enter action phase
        back_to_selection = ngram_action_phase(args, selected_ngrams)
        
        if not back_to_selection:
            return  # User wants to exit or start over
