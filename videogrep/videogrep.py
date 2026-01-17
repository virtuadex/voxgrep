import random
import logging
import sys
import subprocess
import os
from typing import List, Union

from . import search_engine as search_module
from . import exporter
from . import vtt

# Initialize logger
logger = logging.getLogger(__name__)

# Re-export key functions so they can be imported from top level if needed
# though cleaner to import from submodules
find_transcript = search_module.find_transcript
parse_transcript = search_module.parse_transcript
get_ngrams = search_module.get_ngrams
search = search_module.search
create_supercut = exporter.create_supercut
create_supercut_in_batches = exporter.create_supercut_in_batches
export_individual_clips = exporter.export_individual_clips
export_m3u = exporter.export_m3u
export_mpv_edl = exporter.export_mpv_edl
export_xml = exporter.export_xml
cleanup_log_files = exporter.cleanup_log_files
BATCH_SIZE = exporter.BATCH_SIZE
SUB_EXTS = search_module.SUB_EXTS


def remove_overlaps(segments: List[dict]) -> List[dict]:
    """
    Removes any time overlaps from clips
    """
    if len(segments) == 0:
        return []

    segments = sorted(segments, key=lambda k: k["start"])
    out = [segments[0]]
    for segment in segments[1:]:
        prev_end = out[-1]["end"]
        start = segment["start"]
        end = segment["end"]
        if prev_end >= start:
            out[-1]["end"] = end
        else:
            out.append(segment)

    return out


def pad_and_sync(
    segments: List[dict], padding: float = 0, resync: float = 0
) -> List[dict]:
    """
    Adds padding and resyncs
    """
    if len(segments) == 0:
        return []

    for s in segments:
        if padding != 0:
            s["start"] -= padding
            s["end"] += padding
        if resync != 0:
            s["start"] += resync
            s["end"] += resync

        if s["start"] < 0:
            s["start"] = 0
        if s["end"] < 0:
            s["end"] = 0

    out = [segments[0]]
    for segment in segments[1:]:
        prev_file = out[-1]["file"]
        current_file = segment["file"]
        if current_file != prev_file:
            out.append(segment)
            continue
        prev_end = out[-1]["end"]
        start = segment["start"]
        end = segment["end"]
        if prev_end >= start:
            out[-1]["end"] = end
        else:
            out.append(segment)

    return out


def videogrep(
    files: Union[List[str], str],
    query: Union[List[str], str],
    search_type: str = "sentence",
    output: str = "supercut.mp4",
    resync: float = 0,
    padding: float = 0,
    maxclips: int = 0,
    export_clips: bool = False,
    random_order: bool = False,
    demo: bool = False,
    write_vtt: bool = False,
    preview: bool = False,
):
    """
    Creates a supercut of videos based on a search query
    """

    segments = search_module.search(files, query, search_type)

    if len(segments) == 0:
        if isinstance(query, list):
            query = " ".join(query)
        logger.warning(f"No results found for {query}")
        return False

    # default padding for fragment search if not specified is handled in caller or here
    # Original logic:
    if padding == 0 and search_type in ["fragment", "mash"]:
        padding = 0.3

    segments = pad_and_sync(segments, padding=padding, resync=resync)

    # random order
    if random_order:
        random.shuffle(segments)

    # max clips
    if maxclips != 0:
        segments = segments[0:maxclips]

    # demo and exit
    if demo:
        for s in segments:
            print(s["file"], s["start"], s["end"], s["content"])
        return True

    # preview in mpv and exit
    if preview:
        lines = [f"{s['file']},{s['start']},{s['end']-s['start']}" for s in segments]
        edl = "edl://" + ";".join(lines)
        subprocess.run(["mpv", edl])
        return True

    # ensure output directory exists
    output_dir = os.path.dirname(output)
    if output_dir != "" and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # export individual clips
    if export_clips:
        exporter.export_individual_clips(segments, output)
        return True

    # m3u
    if output.endswith(".m3u"):
        exporter.export_m3u(segments, output)
        return True

    # mpv edls
    if output.endswith(".mpv.edl"):
        exporter.export_mpv_edl(segments, output)
        return True

    # fcp xml (compatible with premiere/davinci)
    if output.endswith(".xml"):
        exporter.export_xml(segments, output)
        return True

    # export supercut
    if len(segments) > exporter.BATCH_SIZE:
        exporter.create_supercut_in_batches(segments, output)
    else:
        exporter.create_supercut(segments, output)

    # write WebVTT file
    if write_vtt:
        basename, ext = os.path.splitext(output)
        vtt.render(segments, basename + ".vtt")
    
    return True
