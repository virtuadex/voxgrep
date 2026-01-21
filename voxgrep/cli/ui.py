"""
UI components for VoxGrep CLI.

This module contains all Rich-based UI components including
banners, tables, panels, and other visual elements.
"""

import sys
import subprocess
from pathlib import Path
from typing import Any

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


def print_ngrams_table(ngrams: list[tuple[tuple, int]], filtered: bool, n: int) -> None:
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


def format_duration(seconds: float) -> str:
    """Format seconds into a human-readable duration string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def print_session_summary(stats: dict[str, Any]) -> None:
    """
    Print a detailed session summary with statistics.
    
    Args:
        stats: Dictionary containing session statistics:
            - clips_count: Number of clips found
            - supercut_duration: Total duration of supercut
            - original_duration: Total duration of source files
            - time_saved: Time difference (original - supercut)
            - efficiency_percent: Percentage of time saved
            - search_query: The search query used
            - output_file: Path to output file (if any)
            - mode: 'export', 'preview', or 'demo'
    """
    if not stats or not stats.get("success"):
        return
    
    mode = stats.get("mode", "export")
    
    # Build the summary table
    table = Table(
        title="📊 Session Summary",
        box=box.ROUNDED,
        border_style="green" if mode == "export" else "cyan",
        show_header=False,
        padding=(0, 1)
    )
    table.add_column("Metric", style="bold cyan", width=20)
    table.add_column("Value", style="bold white")
    
    # Search query
    query = stats.get("search_query", "")
    if query:
        table.add_row("🔍 Search Query", query[:50] + "..." if len(query) > 50 else query)
    
    # Clips count
    clips_count = stats.get("clips_count", 0)
    table.add_row("📹 Clips Found", str(clips_count))
    
    # Supercut duration
    supercut_dur = stats.get("supercut_duration", 0)
    table.add_row("⏱️ Supercut Duration", format_duration(supercut_dur))
    
    # Original duration (if available)
    original_dur = stats.get("original_duration", 0)
    if original_dur > 0:
        table.add_row("📼 Original Footage", format_duration(original_dur))
        
        # Time saved
        time_saved = stats.get("time_saved", 0)
        if time_saved > 0:
            table.add_row("💾 Time Saved", f"[green]{format_duration(time_saved)}[/green]")
        
        # Efficiency
        efficiency = stats.get("efficiency_percent", 0)
        if efficiency > 0:
            efficiency_style = "green" if efficiency > 50 else "yellow"
            table.add_row("📈 Efficiency", f"[{efficiency_style}]{efficiency:.1f}%[/{efficiency_style}]")
    
    # Output file
    output_file = stats.get("output_file")
    if output_file and mode == "export":
        table.add_row("📁 Output File", str(Path(output_file).name))
    
    console.print()
    console.print(table)
    
    # Print mode-specific message
    if mode == "export" and output_file:
        console.print(f"\n[bold green]✓ Export Complete![/bold green] Saved to: [cyan]{output_file}[/cyan]")
    elif mode == "preview":
        console.print("\n[bold cyan]✓ Preview Complete![/bold cyan]")
    elif mode == "demo":
        console.print("\n[dim]This was a dry run. No files were created.[/dim]")
    
    console.print()



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
