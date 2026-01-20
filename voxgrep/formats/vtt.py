import re
import io
from bs4 import BeautifulSoup
from typing import Union, List


def timestamp_to_secs(ts: str) -> float:
    """
    Convert a timestamp to seconds

    :param ts str: Timestamp
    :rtype float: Seconds
    """
    hours, minutes, seconds = ts.split(":")
    return float(hours) * 60 * 60 + float(minutes) * 60 + float(seconds)


def secs_to_timestamp(secs: float) -> str:
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02f" % (h, m, s)


def parse_cued(data: List[str]) -> List[dict]:
    out = []
    # regex for timestamp tags: <00:00:00.000>
    timestamp_pat = r"<(\d\d:\d\d:\d\d(?:\.\d+)?)>"
    
    for meta, content in data:
        start_match, end_match = meta.split(" --> ")
        seg_start = timestamp_to_secs(start_match)
        # Remove any extra info after the end timestamp
        seg_end = timestamp_to_secs(end_match.split(" ")[0])
        
        # Strip other tags like <c> or </c>
        clean_content = re.sub(r"<(?!/?\d\d:\d\d:\d\d)/?[^>]+>", "", content)
        
        # Split by timestamp tags, keeping the tags in the result
        parts = re.split(timestamp_pat, clean_content)
        
        sentence = {"content": "", "words": [], "start": seg_start, "end": seg_end}
        
        current_time = seg_start
        
        # re.split with one capturing group returns [text, tag, text, tag, ...]
        for i in range(0, len(parts), 2):
            text = parts[i].strip()
            if text:
                # This text belongs to the previous time or the segment start
                # We'll assign it the current_time as start
                # If there's a next timestamp, that's the end. 
                # Otherwise seg_end is the end.
                next_time = seg_end
                if i + 1 < len(parts):
                    next_time = timestamp_to_secs(parts[i+1])
                
                # Split text into words if multiple
                sub_words = text.split()
                for j, sw in enumerate(sub_words):
                    # For sub-words, we don't know the exact timing, so we'll just distribute
                    # them or just keep them together. For better results, let's just 
                    # create one entry per split text for now if it's meant to be one word.
                    sentence["words"].append({
                        "word": sw,
                        "start": current_time,
                        "end": next_time
                    })
            
            if i + 1 < len(parts):
                current_time = timestamp_to_secs(parts[i+1])
                
        if sentence["words"]:
            sentence["content"] = " ".join([w["word"] for w in sentence["words"]])
            out.append(sentence)

    return out


def parse_uncued(data: str) -> List[dict]:
    out = []
    lines = [d.strip() for d in data.split("\n") if d.strip() != ""]
    out = [{"content": "", "start": None, "end": None}]
    for line in lines:
        if " --> " in line:
            start, end = line.split(" --> ")
            end = end.split(" ")[0]
            start = timestamp_to_secs(start)
            end = timestamp_to_secs(end)
            if out[-1]["start"] is None:
                out[-1]["start"] = start
                out[-1]["end"] = end
            else:
                out.append({"content": "", "start": start, "end": end})
        else:
            if out[-1]["start"] is not None:
                out[-1]["content"] += " " + line.strip()

    for o in out:
        o["content"] = o["content"].strip()

    return out


def parse(vtt: Union[io.IOBase, str]) -> List[dict]:
    """
    Parses webvtt and returns timestamps for words and lines
    Tested on automatically generated subtitles from YouTube
    """

    _vtt: str = ""
    if isinstance(vtt, io.IOBase):
        _vtt = vtt.read()
    else:
        _vtt = vtt

    pat = r"<(\d\d:\d\d:\d\d(\.\d+)?)>"
    out = []

    lines = []
    data = _vtt.split("\n")
    data = [d for d in data if re.search(r"\d\d:\d\d:\d\d", d) is not None]
    for i, d in enumerate(data):
        if re.search(pat, d):
            lines.append((data[i - 1], d))

    if len(lines) > 0:
        out = parse_cued(lines)
    else:
        out = parse_uncued(_vtt)

    return out



def render(segments: List[dict], outputfile: str):
    """
    Render a list of segments to a WebVTT file
    
    :param segments: List of segments as returned by voxgrep.search
    :param outputfile: Filename for the WebVTT output
    """

    start = 0.0
    with open(outputfile, "w", encoding="utf-8") as outfile:
        outfile.write("WEBVTT\n")
        for index, s in enumerate(segments):
            clip_duration = s["end"] - s["start"]
            end = start + clip_duration
            start_t = secs_to_timestamp(start)
            end_t = secs_to_timestamp(end)
            outfile.write(f"\n{index}\n{start_t} --> {end_t}\n{s['content']}\n")
            start = end
