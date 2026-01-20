import random
import subprocess
import os
import sys
from typing import List, Union, Optional

from rich.console import Console
from rich.table import Table
from rich import box

from . import search_engine as search_module
from . import exporter
from . import vtt
from .config import DEFAULT_PADDING, BATCH_SIZE
from .utils import setup_logger, ensure_list, ensure_directory_exists

logger = setup_logger(__name__)


def remove_overlaps(segments: List[dict]) -> List[dict]:
    """
    Removes any time overlaps from clips, merging them into single segments.
    """
    if not segments:
        return []

    # Sort by start time
    segments = sorted(segments, key=lambda k: k["start"])
    
    out = [segments[0]]
    for segment in segments[1:]:
        # Only merge if it's the same file
        if segment["file"] == out[-1]["file"] and out[-1]["end"] >= segment["start"]:
            out[-1]["end"] = max(out[-1]["end"], segment["end"])
        else:
            out.append(segment)

    return out


def pad_and_sync(
    segments: List[dict], padding: float = 0, resync: float = 0
) -> List[dict]:
    """
    Adds padding and resyncs timestamps.
    """
    if not segments:
        return []

    processed = []
    for s in segments:
        new_segment = s.copy()
        if padding != 0:
            new_segment["start"] -= padding
            new_segment["end"] += padding
        if resync != 0:
            new_segment["start"] += resync
            new_segment["end"] += resync

        # Ensure bounds
        new_segment["start"] = max(0, new_segment["start"])
        new_segment["end"] = max(0, new_segment["end"])
        
        processed.append(new_segment)

    # Merge overlaps that were created by padding
    return remove_overlaps(processed)


def voxgrep(
    files: Union[List[str], str],
    query: Union[List[str], str],
    search_type: str = "sentence",
    output: str = "supercut.mp4",
    resync: float = 0,
    padding: Optional[float] = None,
    maxclips: int = 0,
    export_clips: bool = False,
    random_order: bool = False,
    demo: bool = False,
    write_vtt: bool = False,
    preview: bool = False,
    exact_match: bool = False,
    console: Optional[Console] = None,
) -> bool:
    """
    Main entry point for creating a supercut based on a search query.
    """
    files = ensure_list(files)
    query = ensure_list(query)

    # Perform search
    segments = search_module.search(files, query, search_type, exact_match=exact_match)

    if not segments:
        query_str = " ".join(query) if isinstance(query, list) else query
        logger.warning(f"No results found for: {query_str}")
        return False

    # Handle default padding
    if padding is None:
        if search_type in ["fragment", "mash"]:
            padding = DEFAULT_PADDING
        else:
            padding = 0

    # Apply padding and handle overlaps
    segments = pad_and_sync(segments, padding=padding, resync=resync)

    # Random order
    if random_order:
        random.shuffle(segments)

    # Limit clips
    if maxclips > 0:
        segments = segments[:maxclips]

    # Mode: Demo (dry run)
    if demo:
        if console:
            table = Table(title=f"Search Results ({len(segments)} segments)", box=box.ROUNDED)
            table.add_column("File", style="cyan")
            table.add_column("Start", justify="right", style="green")
            table.add_column("End", justify="right", style="red")
            table.add_column("Content", style="white")

            for s in segments:
                table.add_row(
                    os.path.basename(s['file']),
                    f"{s['start']:.2f}s",
                    f"{s['end']:.2f}s",
                    s['content']
                )
            console.print(table)
        else:
            for s in segments:
                print(f"{s['file']} | {s['start']:.2f} - {s['end']:.2f} | {s['content']}")
        return True

    # Mode: Preview (MPV)
    if preview:
        # Calculate statistics
        total_clip_duration = sum(s['end'] - s['start'] for s in segments)
        
        # Display search results summary
        if console:
            stats_table = Table(title="🎬 Preview Statistics", box=box.ROUNDED, border_style="cyan")
            stats_table.add_column("Metric", style="bold cyan", no_wrap=True)
            stats_table.add_column("Value", style="bold white", justify="right")
            
            stats_table.add_row("Clips Found", f"{len(segments)}")
            stats_table.add_row("Total Duration", f"{total_clip_duration:.1f}s ({total_clip_duration/60:.1f}m)")
            
            if segments:
                first_match = segments[0]['start']
                last_match = segments[-1]['end']
                stats_table.add_row("First Match", f"{first_match:.1f}s ({first_match/60:.1f}m)")
                stats_table.add_row("Last Match", f"{last_match:.1f}s ({last_match/60:.1f}m)")
                stats_table.add_row("Time Span", f"{(last_match - first_match):.1f}s")
            
            console.print()
            console.print(stats_table)
            console.print()
            console.print("[bold yellow]▶ Launching MPV Preview...[/bold yellow]")
            console.print("[dim]Press 'q' to quit, Space to pause, Arrow keys to seek[/dim]\n")
        
        lines = [f"{os.path.abspath(s['file'])},{s['start']},{s['end']-s['start']}" for s in segments]
        playlist_str = "edl://" + ";".join(lines)
        try:
            subprocess.run(["mpv", "--playlist=-"], input=playlist_str.encode("utf-8"), check=True)
            
            if console:
                console.print()
                console.print("[bold green]✓ Preview Complete[/bold green]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            error_msg = "Could not launch mpv for preview. Is it installed?"
            if sys.platform == "darwin":
                error_msg += " (Try: 'brew install mpv')"
            logger.error(error_msg)
            if console:
                console.print(f"[bold red]Error:[/bold red] {error_msg}")
            return False
        return True

    # Ensure output directory exists
    ensure_directory_exists(os.path.dirname(os.path.abspath(output)))

    # Export Logic
    if export_clips:
        exporter.export_individual_clips(segments, output)
    elif output.endswith(".m3u"):
        exporter.export_m3u(segments, output)
    elif output.endswith(".mpv.edl"):
        exporter.export_mpv_edl(segments, output)
    elif output.endswith(".xml"):
        exporter.export_xml(segments, output)
    else:
        # Create full supercut
        if len(segments) > BATCH_SIZE:
            exporter.create_supercut_in_batches(segments, output)
        else:
            exporter.create_supercut(segments, output)

    # Write WebVTT if requested
    if write_vtt:
        vtt_path = os.path.splitext(output)[0] + ".vtt"
        vtt.render(segments, vtt_path)
        logger.info(f"Subtitle file written to: {vtt_path}")
    
    return True
