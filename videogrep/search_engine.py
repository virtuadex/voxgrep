import os
import re
import json
import random
import logging
from pathlib import Path
from typing import Optional, List, Union, Iterator
from tqdm import tqdm

from . import vtt, srt, sphinx

logger = logging.getLogger(__name__)

SUB_EXTS = [".json", ".vtt", ".srt", ".transcript"]

def find_transcript(videoname: str, prefer: Optional[str] = None) -> Optional[str]:
    subfile = None
    _sub_exts = SUB_EXTS
    if prefer is not None:
        _sub_exts = [prefer] + SUB_EXTS

    # pathlib approach
    video_path = Path(videoname)
    parent = video_path.parent
    name_stem = video_path.stem
    
    # We look for files that start with the same name
    # But regex is safer for varying extensions
    all_files = [str(f) for f in parent.iterdir() if f.is_file()]

    for ext in _sub_exts:
        # Escaping might be tricky if paths have regex chars
        # But generally we want to match: /path/to/video.*\.ext
        # actually the original logic was flawed if videoname itself had regex chars
        # Using pathlib is cleaner
        
        # Simple check first
        candidate = video_path.with_suffix(ext)
        if candidate.exists():
            return str(candidate)

        # Iterate all files for fuzzy match (like original code did?)
        # Only do this if we suspect multi-part extensions or other behaviors
        # The original code used regex.
        pattern = (
            re.escape(os.path.splitext(videoname)[0].replace("\\", "/"))
            + r"\..*?\.?"
            + ext.replace(".", "")
        )
        for f in all_files:
            if re.search(pattern, f.replace("\\", "/")):
                subfile = f
                break
        if subfile:
            break

    return subfile


def parse_transcript(
    videoname: str, prefer: Optional[str] = None
) -> Optional[List[dict]]:

    subfile = find_transcript(videoname, prefer)

    if subfile is None:
        logger.error(f"No subtitle file found for {videoname}")
        return None

    transcript = None

    with open(subfile, "r", encoding="utf8") as infile:
        if subfile.endswith(".srt"):
            transcript = srt.parse(infile)
        elif subfile.endswith(".vtt"):
            transcript = vtt.parse(infile)
        elif subfile.endswith(".json"):
            transcript = json.load(infile)
        elif subfile.endswith(".transcript"):
            transcript = sphinx.parse(infile)

    return transcript


def get_ngrams(files: Union[str, list], n: int = 1) -> Iterator[tuple]:
    if not isinstance(files, list):
        files = [files]

    words = []

    for file in files:
        transcript = parse_transcript(file)
        if transcript is None:
            continue
        for line in transcript:
            if "words" in line:
                words += [w["word"] for w in line["words"]]
            else:
                words += re.split(r"[.?!,:\"]+\s*|\s+", line["content"])

    ngrams = zip(*[words[i:] for i in range(n)])
    return ngrams


def search(
    files: Union[str, list],
    query: Union[str, list],
    search_type: str = "sentence",
    prefer: Optional[str] = None,
) -> List[dict]:
    if not isinstance(files, list):
        files = [files]

    if not isinstance(query, list):
        query = [query]

    all_segments = []

    for file in tqdm(files, desc="Searching files", unit="file", disable=len(files) < 2):
        segments = []
        transcript = parse_transcript(file, prefer=prefer)
        if transcript is None:
            continue

        if search_type == "sentence":
            for line in transcript:
                for _query in query:
                    if re.search(_query, line["content"], re.IGNORECASE):
                        segments.append(
                            {
                                "file": file,
                                "start": line["start"],
                                "end": line["end"],
                                "content": line["content"],
                            }
                        )

        elif search_type == "fragment":
            if "words" not in transcript[0]:
                logger.error(f"Could not find word-level timestamps for {file}")
                continue

            words = []
            for line in transcript:
                words += line["words"]

            for _query in query:
                queries = _query.split(" ")
                queries = [q.strip() for q in queries if q.strip() != ""]
                fragments = zip(*[words[i:] for i in range(len(queries))])
                for fragment in fragments:
                    found = all(
                        re.search(q, w["word"], re.IGNORECASE) for q, w in zip(queries, fragment)
                    )
                    if found:
                        phrase = " ".join([w["word"] for w in fragment])
                        segments.append(
                            {
                                "file": file,
                                "start": fragment[0]["start"],
                                "end": fragment[-1]["end"],
                                "content": phrase,
                            }
                        )

        elif search_type == "mash":
            if "words" not in transcript[0]:
                logger.error(f"Could not find word-level timestamps for {file}")
                continue

            words = []
            for line in transcript:
                words += line["words"]

            for _query in query:
                queries = _query.split(" ")

                for q in queries:
                    matches = [w for w in words if w["word"].lower() == q.lower()]
                    if len(matches) == 0:
                        logger.error(f"Could not find {q} in transcript")
                        return []
                    random.shuffle(matches)
                    word = matches[0]
                    segments.append(
                        {
                            "file": file,
                            "start": word["start"],
                            "end": word["end"],
                            "content": word["word"],
                        }
                    )

        segments = sorted(segments, key=lambda k: k["start"])

        all_segments += segments

    return all_segments
