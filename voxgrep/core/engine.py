import os
import re
import json
import random
from pathlib import Path
from typing import Iterator, Any
from tqdm import tqdm

import numpy as np
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

from .types import SearchType
from .word_timestamps import synthesize_word_timestamps
from ..formats import vtt, srt, sphinx
from ..utils.config import (
    SUBTITLE_EXTENSIONS,
    DEFAULT_SEMANTIC_MODEL,
    DEFAULT_SEMANTIC_THRESHOLD
)
from ..utils.helpers import setup_logger, ensure_list
from ..utils.exceptions import (
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
    def get_instance(cls, model_name: str | None = None):
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
    _cache: dict[str, list[dict]] = {}
    _files_mtime: dict[str, float] = {}

    @classmethod
    def get(cls, subfile: str) -> list[dict] | None:
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
    def set(cls, subfile: str, transcript: list[dict]):
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


def find_transcript(videoname: str, prefer: str | None = None) -> str | None:
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
    videoname: str, prefer: str | None = None
) -> list[dict] | None:
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


def get_embeddings(videoname: str, transcript: list[dict], force: bool = False) -> np.ndarray:
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


def get_ngrams(files: str | list[str], n: int = 1, ignored_words: list[str] | None = None) -> Iterator[tuple]:
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

    if ignored_words:
        normalized_ignored = set(w.lower() for w in ignored_words)
        for g in ngrams:
            # Filter if ANY word in the n-gram is in the ignored list
            if not any(w.lower() in normalized_ignored for w in g):
                yield g
    else:
        yield from ngrams


# =============================================================================
# Search Strategy Implementations
# =============================================================================

def _search_mash(
    files: list[str],
    query: list[str],
    prefer: str | None = None,
) -> list[dict]:
    """
    Mash search: word-level random matching for creative word-mashup cuts.

    Finds individual words and picks random instances for each query word,
    enabling creative remixing of speech.
    """
    all_words = []

    for file in tqdm(files, desc="Indexing words for mash", unit="file", disable=len(files) < 2):
        transcript = parse_transcript(file, prefer=prefer)
        if not transcript:
            continue

        # Get word-level timestamps (synthesized if needed)
        words = synthesize_word_timestamps(transcript, file=file, log_info=True)
        all_words.extend(words)

    if not all_words:
        logger.error("Could not extract any words from the provided files.")
        return []

    segments = []
    for _query in query:
        queries = _query.split(" ")
        for q in queries:
            matches = [w for w in all_words if re.sub(r"[.?!,:\"]+", "", w["word"].lower()) == q.lower()]
            if not matches:
                continue
            word = random.choice(matches)
            segments.append({
                "file": word["file"],
                "start": word["start"],
                "end": word["end"],
                "content": word["word"],
            })

    return segments


def _search_semantic(
    files: list[str],
    query: list[str],
    prefer: str | None = None,
    threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    force_reindex: bool = False,
) -> list[dict]:
    """
    Semantic search: concept-based matching using sentence embeddings.

    Uses sentence-transformers to find semantically similar segments,
    even if they don't contain the exact query words.
    """
    if not SEMANTIC_AVAILABLE:
        raise SemanticSearchNotAvailableError("Semantic search requires sentence-transformers.")

    model = SemanticModel.get_instance()
    query_embeddings = model.encode(query, show_progress_bar=False)

    # Batch processing: Collect all embeddings from all files
    total_embeddings = []
    embedding_metadata = []  # (file, segment)

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

    # Guard against dimension mismatch
    if query_embeddings.ndim < 2 or query_embeddings.shape[1] == 0:
        logger.error("Query embeddings have invalid shape. Check your search terms.")
        return []

    # Compute all scores at once (matrix multiplication)
    cos_scores = util.cos_sim(query_embeddings, combined_embeddings)

    segments = []
    for i, _query in enumerate(query):
        scores = cos_scores[i]
        # Use argwhere or similar for fast thresholding
        indices = np.where(scores >= threshold)[0]
        for idx in indices:
            file_path, segment = embedding_metadata[idx]
            segments.append({
                "file": file_path,
                "start": segment["start"],
                "end": segment["end"],
                "content": segment["content"],
                "score": float(scores[idx])
            })

    return sorted(segments, key=lambda k: k["score"], reverse=True)


def _search_sentence(
    files: list[str],
    query: list[str],
    compiled_queries: list[tuple[str, re.Pattern]],
    prefer: str | None = None,
) -> list[dict]:
    """
    Sentence search: full sentence matching with regex.

    Matches entire transcript segments where the query pattern appears
    anywhere in the sentence content.
    """
    segments = []

    for file in tqdm(files, desc="Searching files", unit="file", disable=len(files) < 2):
        transcript = parse_transcript(file, prefer=prefer)
        if transcript is None:
            continue

        file_segments = []
        for line in transcript:
            content = line["content"]
            for _query_str, _query_regex in compiled_queries:
                if _query_regex.search(content):
                    file_segments.append({
                        "file": file,
                        "start": line["start"],
                        "end": line["end"],
                        "content": content,
                    })

        segments.extend(sorted(file_segments, key=lambda k: k["start"]))

    return segments


def _search_fragment(
    files: list[str],
    query: list[str],
    compiled_queries: list[tuple[str, re.Pattern]],
    prefer: str | None = None,
    exact_match: bool = False,
) -> list[dict]:
    """
    Fragment search: word-level precise matching with timing.

    Uses word-level timestamps to find exact multi-word phrases,
    returning tightly-timed clips of just the matched words.
    """
    segments = []

    for file in tqdm(files, desc="Searching files", unit="file", disable=len(files) < 2):
        transcript = parse_transcript(file, prefer=prefer)
        if not transcript:
            continue

        # Get word-level timestamps (synthesized if needed)
        words = synthesize_word_timestamps(transcript, file=file, log_info=True)

        if not words:
            continue

        for _query_str, _query_regex in compiled_queries:
            queries = [q.strip() for q in _query_str.split(" ") if q.strip()]
            if not queries:
                continue

            fragment_len = len(queries)

            # Compile individual regex patterns for each query word
            query_patterns = []
            for q in queries:
                if exact_match:
                    pattern = r"\b" + re.escape(q) + r"\b"
                else:
                    pattern = re.escape(q)
                query_patterns.append(re.compile(pattern, re.IGNORECASE))

            for i in range(len(words) - fragment_len + 1):
                fragment = words[i:i+fragment_len]
                # Match each query word against its corresponding fragment word
                if all(query_patterns[j].search(fragment[j]["word"]) for j in range(fragment_len)):
                    segments.append({
                        "file": file,
                        "start": fragment[0]["start"],
                        "end": fragment[-1]["end"],
                        "content": " ".join([w["word"] for w in fragment]),
                    })

    return segments


# =============================================================================
# Main Search Function
# =============================================================================

def search(
    files: str | list[str],
    query: str | list[str],
    search_type: str | SearchType = "sentence",
    prefer: str | None = None,
    threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    force_reindex: bool = False,
    exact_match: bool = False,
) -> list[dict]:
    """
    Search through video/audio files for a specific query.

    Args:
        files: Path(s) to media files to search.
        query: Search query or list of queries.
        search_type: Search strategy - "sentence", "fragment", "mash", or "semantic".
        prefer: Preferred subtitle format extension.
        threshold: Semantic similarity threshold (for semantic search).
        force_reindex: Force regeneration of embeddings (for semantic search).
        exact_match: Use word boundary matching for exact words.

    Returns:
        List of matched segments with file, start, end, and content.
    """
    files = ensure_list(files)
    query = ensure_list(query)

    # Normalize search_type to enum
    if isinstance(search_type, str):
        try:
            search_type = SearchType(search_type.lower())
        except ValueError:
            raise InvalidSearchTypeError(f"Unsupported search type: {search_type}")

    # Dispatch to appropriate search strategy
    if search_type == SearchType.MASH:
        return _search_mash(files, query, prefer=prefer)

    if search_type == SearchType.SEMANTIC:
        return _search_semantic(
            files, query, prefer=prefer,
            threshold=threshold, force_reindex=force_reindex
        )

    # For sentence and fragment search, pre-compile regex patterns
    compiled_queries = []
    for q in query:
        pattern = q
        if exact_match:
            # Escape the query to treat it as literal string, then add boundaries
            pattern = r"\b" + re.escape(q) + r"\b"
        compiled_queries.append((q, re.compile(pattern, re.IGNORECASE)))

    if search_type == SearchType.SENTENCE:
        return _search_sentence(files, query, compiled_queries, prefer=prefer)

    if search_type == SearchType.FRAGMENT:
        return _search_fragment(
            files, query, compiled_queries,
            prefer=prefer, exact_match=exact_match
        )

    raise InvalidSearchTypeError(f"Unsupported search type: {search_type}")
