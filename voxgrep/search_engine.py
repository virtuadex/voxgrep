import os
import re
import json
import random
from pathlib import Path
from typing import Optional, List, Union, Iterator, Dict
from tqdm import tqdm

import numpy as np
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

from . import vtt, srt, sphinx
from .config import (
    SUBTITLE_EXTENSIONS,
    DEFAULT_SEMANTIC_MODEL,
    DEFAULT_SEMANTIC_THRESHOLD,
    get_cache_dir
)
from .utils import setup_logger, ensure_list
from .exceptions import (
    TranscriptNotFoundError,
    SemanticSearchNotAvailableError,
    InvalidSearchTypeError
)

logger = setup_logger(__name__)

# Legacy constant for backwards compatibility
SUB_EXTS = SUBTITLE_EXTENSIONS

class SemanticModel:
    """Singleton class for managing the semantic search model."""
    _instance = None
    _device = None

    @classmethod
    def get_instance(cls, model_name: Optional[str] = None):
        """Get or create the semantic model instance with device detection."""
        if cls._instance is None:
            if not SEMANTIC_AVAILABLE:
                raise SemanticSearchNotAvailableError(
                    "sentence-transformers is not installed. "
                    "Install with 'pip install sentence-transformers'"
                )
            
            model_name = model_name or DEFAULT_SEMANTIC_MODEL
            
            # Device detection for acceleration
            if torch.cuda.is_available():
                cls._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                cls._device = "mps"
            else:
                cls._device = "cpu"
                
            logger.info(f"Loading semantic model: {model_name} on {cls._device}")
            cls._instance = SentenceTransformer(model_name, device=cls._device)
            
        return cls._instance


class TranscriptCache:
    """Singleton for caching parsed transcripts to avoid redundant I/O."""
    _cache: Dict[str, List[dict]] = {}
    _files_mtime: Dict[str, float] = {}

    @classmethod
    def get(cls, subfile: str) -> Optional[List[dict]]:
        """Get transcript from cache if available and file hasn't changed."""
        if not os.path.exists(subfile):
            return None
            
        try:
            mtime = os.path.getmtime(subfile)
            if subfile in cls._cache and cls._files_mtime.get(subfile) == mtime:
                return cls._cache[subfile]
        except OSError:
            pass
        return None

    @classmethod
    def set(cls, subfile: str, transcript: List[dict]):
        """Cache the transcript and its modification time."""
        try:
            cls._cache[subfile] = transcript
            cls._files_mtime[subfile] = os.path.getmtime(subfile)
        except OSError:
            pass

    @classmethod
    def clear(cls):
        """Clear the cache."""
        cls._cache.clear()
        cls._files_mtime.clear()


def find_transcript(videoname: str, prefer: Optional[str] = None) -> Optional[str]:
    """
    Find a transcript file for a given video file.
    
    Searches for subtitle/transcript files with the same base name as the video,
    trying various extensions and fuzzy matching strategies.
    
    Args:
        videoname: Path to the video file
        prefer: Preferred subtitle extension to try first (e.g., '.srt')
    
    Returns:
        Path to the transcript file if found, None otherwise
    """
    video_path = Path(videoname)
    if not video_path.parent.exists():
        return None
        
    _sub_exts = list(SUBTITLE_EXTENSIONS)
    if prefer is not None:
        _sub_exts = [prefer] + _sub_exts

    parent = video_path.parent
    name_stem = video_path.stem
    
    # Strategy 1: Exact match (video.mp4 -> video.srt)
    for ext in _sub_exts:
        candidate = video_path.with_suffix(ext)
        if candidate.exists():
            return candidate.as_posix()

    # Pre-list files once for efficiency
    try:
        all_files = list(parent.iterdir())
    except OSError:
        return None

    # Strategy 2: Fuzzy match for filenames with language codes (video.en.srt)
    for ext in _sub_exts:
        for f in all_files:
            if f.is_file() and f.name.startswith(name_stem) and f.suffix == ext:
                return f.as_posix()
            
    # Strategy 3: Legacy regex-based fallback for complex multi-part extensions
    for ext in _sub_exts:
        pattern = re.escape(name_stem) + r".*?\.?" + ext.replace(".", "")
        for f in all_files:
            if f.is_file() and re.search(pattern, f.name):
                return f.as_posix()

    return None


def parse_transcript(
    videoname: str, prefer: Optional[str] = None
) -> Optional[List[dict]]:
    """
    Parse a transcript file for a given video.
    
    Args:
        videoname: Path to the video file
        prefer: Preferred subtitle format to try first
    
    Returns:
        List of transcript segments with 'content', 'start', 'end' keys,
        and optionally 'words' for word-level timestamps
    """
    subfile = find_transcript(videoname, prefer)

    if subfile is None:
        logger.error(f"No subtitle file found for {videoname}")
        return None

    # Check cache first
    cached = TranscriptCache.get(subfile)
    if cached is not None:
        return cached

    transcript = None

    try:
        with open(subfile, "r", encoding="utf8") as infile:
            if subfile.endswith(".srt"):
                transcript = srt.parse(infile)
            elif subfile.endswith(".vtt"):
                transcript = vtt.parse(infile)
            elif subfile.endswith(".json"):
                transcript = json.load(infile)
            elif subfile.endswith(".transcript"):
                transcript = sphinx.parse(infile)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, IndexError) as e:
        logger.error(f"Error parsing transcript file {subfile}: {e}")
        return None

    if transcript is not None:
        TranscriptCache.set(subfile, transcript)

    return transcript


def get_embeddings_path(videoname: str) -> str:
    """Get the path where embeddings for a video are cached."""
    return os.path.splitext(videoname)[0] + ".embeddings.npy"


def get_embeddings(videoname: str, transcript: List[dict], force: bool = False) -> np.ndarray:
    """
    Get or generate semantic embeddings for a transcript.
    """
    emb_path = get_embeddings_path(videoname)
    if os.path.exists(emb_path) and not force:
        return np.load(emb_path)
    
    model = SemanticModel.get_instance()
    sentences = [line["content"] for line in transcript]
    logger.info(f"Generating embeddings for {videoname}...")
    embeddings = model.encode(sentences, show_progress_bar=False)
    np.save(emb_path, embeddings)
    return embeddings


def get_ngrams(files: Union[str, List[str]], n: int = 1) -> Iterator[tuple]:
    """
    Extract n-grams from transcript files.
    """
    files = ensure_list(files)
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
    files: Union[str, List[str]],
    query: Union[str, List[str]],
    search_type: str = "sentence",
    prefer: Optional[str] = None,
    threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    force_reindex: bool = False,
    exact_match: bool = False,
) -> List[dict]:
    """
    Search through video/audio files for a specific query.
    """
    files = ensure_list(files)
    query = ensure_list(query)
    all_segments = []

    if search_type == "mash":
        all_words = []
        for file in tqdm(files, desc="Indexing words for mash", unit="file", disable=len(files) < 2):
            transcript = parse_transcript(file, prefer=prefer)
            if transcript and len(transcript) > 0 and "words" in transcript[0]:
                for line in transcript:
                    for w in line["words"]:
                        w["file"] = file
                        all_words.append(w)
        
        if not all_words:
            logger.error("Could not find word-level timestamps in any of the provided files.")
            return []

        for _query in query:
            queries = _query.split(" ")
            for q in queries:
                matches = [w for w in all_words if re.sub(r"[.?!,:\"]+", "", w["word"].lower()) == q.lower()]
                if not matches:
                    continue 
                word = random.choice(matches)
                all_segments.append({
                    "file": word["file"],
                    "start": word["start"],
                    "end": word["end"],
                    "content": word["word"],
                })
        return all_segments

    if search_type == "semantic":
        if not SEMANTIC_AVAILABLE:
            raise SemanticSearchNotAvailableError("Semantic search requires sentence-transformers.")
        
        model = SemanticModel.get_instance()
        query_embeddings = model.encode(query, show_progress_bar=False)
        
        # Batch processing: Collect all embeddings from all files
        total_embeddings = []
        embedding_metadata = [] # (file, index_in_transcript)
        
        for file in tqdm(files, desc="Loading embeddings", unit="file", disable=len(files) < 2):
            transcript = parse_transcript(file, prefer=prefer)
            if not transcript:
                continue
            
            embeddings = get_embeddings(file, transcript, force=force_reindex)
            total_embeddings.append(embeddings)
            for j in range(len(transcript)):
                embedding_metadata.append((file, transcript[j]))
        
        if not total_embeddings or len(query_embeddings) == 0:
            return []
            
        # Combine into one large matrix
        combined_embeddings = np.vstack(total_embeddings)
        
        # Guard against dimension mismatch (mat1 shape 1x0 usually means empty query results)
        if query_embeddings.ndim < 2 or query_embeddings.shape[1] == 0:
            logger.error("Query embeddings have invalid shape. Check your search terms.")
            return []
            
        # Compute all scores at once (matrix multiplication)
        cos_scores = util.cos_sim(query_embeddings, combined_embeddings)
        
        for i, _query in enumerate(query):
            scores = cos_scores[i]
            # Use argwhere or similar for fast thresholding
            indices = np.where(scores >= threshold)[0]
            for idx in indices:
                file_path, segment = embedding_metadata[idx]
                all_segments.append({
                    "file": file_path,
                    "start": segment["start"],
                    "end": segment["end"],
                    "content": segment["content"],
                    "score": float(scores[idx])
                })
        
        return sorted(all_segments, key=lambda k: k["score"], reverse=True)

    # Standard regex/fragment search
    compiled_queries = []
    for q in query:
        pattern = q
        if exact_match:
            # Escape the query to treat it as literal string, then add boundaries
            pattern = r"\b" + re.escape(q) + r"\b"
            
        compiled_queries.append((q, re.compile(pattern, re.IGNORECASE)))

    for file in tqdm(files, desc="Searching files", unit="file", disable=len(files) < 2):
        segments = []
        transcript = parse_transcript(file, prefer=prefer)
        if transcript is None:
            continue

        if search_type == "sentence":
            for line in transcript:
                content = line["content"]
                for _query_str, _query_regex in compiled_queries:
                    if _query_regex.search(content):
                        segments.append({
                            "file": file,
                            "start": line["start"],
                            "end": line["end"],
                            "content": content,
                        })

        elif search_type == "fragment":
            if not transcript or "words" not in transcript[0]:
                continue

            words = []
            for line in transcript:
                words += line["words"]

            for _query_str, _query_regex in compiled_queries:
                queries = [q.strip() for q in _query_str.split(" ") if q.strip()]
                if not queries: continue
                
                fragment_len = len(queries)
                for i in range(len(words) - fragment_len + 1):
                    fragment = words[i:i+fragment_len]
                    if all(re.search(q, w["word"], re.IGNORECASE) for q, w in zip(queries, fragment)):
                        all_segments.append({
                            "file": file,
                            "start": fragment[0]["start"],
                            "end": fragment[-1]["end"],
                            "content": " ".join([w["word"] for w in fragment]),
                        })
        else:
            raise InvalidSearchTypeError(f"Unsupported search type: {search_type}")

        all_segments += sorted(segments, key=lambda k: k["start"])

    return all_segments
