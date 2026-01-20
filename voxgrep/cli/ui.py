"""
UI components for VoxGrep CLI.

This module contains all Rich-based UI components including
banners, tables, panels, and other visual elements.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .. import __version__

# Initialize Rich Console
console = Console()


def print_banner() -> None:
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


def print_ngrams_table(ngrams: List[Tuple[tuple, int]], filtered: bool, n: int) -> None:
    """
    Print a formatted table of n-grams.
    
    Args:
        ngrams: List of (ngram_tuple, count) pairs
        filtered: Whether the results are filtered
        n: The n value for n-grams
    """
    table_title = f"Top 100 {n}-grams ({'Filtered' if filtered else 'Unfiltered'})"
    table = Table(title=table_title, box=box.SIMPLE)
    table.add_column("N-gram", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta", justify="right")

    for ngram, count in ngrams:
        table.add_row(" ".join(ngram), str(count))
    
    console.print(table)


def print_success_panel(output_path: str) -> None:
    """
    Print a success panel with the output file path.
    
    Args:
        output_path: Path to the created output file
    """
    panel = Panel(
        Text.assemble(
            ("Supercut Created Successfully!\n", "bold green"),
            (f"Output saved to: {Path(output_path).absolute()}", "white")
        ),
        title="Session Summary",
        border_style="green",
        box=box.ROUNDED
    )
    console.print()
    console.print(panel)


def open_file(filepath: str) -> None:
    """
    Open a file with the default system application.
    
    Args:
        filepath: Path to the file to open
    """
    if sys.platform == 'win32':
        import os
        os.startfile(filepath)
    elif sys.platform == 'darwin':
        subprocess.call(('open', filepath))
    else:
        subprocess.call(('xdg-open', filepath))


def open_folder(filepath: str) -> None:
    """
    Open the folder containing the specified file.
    
    Args:
        filepath: Path to a file whose parent folder should be opened
    """
    folder = str(Path(filepath).parent.absolute())
    if sys.platform == 'win32':
        import os
        os.startfile(folder)
    elif sys.platform == 'darwin':
        subprocess.call(('open', folder))
    else:
        subprocess.call(('xdg-open', folder))
