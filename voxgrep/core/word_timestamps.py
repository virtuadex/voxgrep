"""
VoxGrep Word Timestamp Utilities

Provides shared functionality for synthesizing word-level timestamps
from sentence-level transcript data.
"""
from ..utils.helpers import setup_logger

logger = setup_logger(__name__)


def synthesize_word_timestamps(
    transcript: list[dict],
    file: str | None = None,
    log_info: bool = True
) -> list[dict]:
    """
    Synthesize word-level timestamps from sentence-level transcript data.

    When transcripts only have sentence-level timing (start/end per sentence),
    this function distributes time evenly across words to create approximate
    word-level timestamps.

    Args:
        transcript: List of transcript segments with 'content', 'start', 'end' keys.
                   May optionally have 'words' key for pre-existing word timestamps.
        file: Optional filename for logging context.
        log_info: Whether to log info message about synthesis.

    Returns:
        List of word dicts with 'word', 'start', 'end' keys.
        If file is provided, also includes 'file' key.
    """
    words = []

    # Check if transcript already has word-level timestamps
    if transcript and "words" in transcript[0]:
        # Use existing word-level timestamps
        for line in transcript:
            for w in line["words"]:
                word_dict = {
                    "word": w["word"],
                    "start": w["start"],
                    "end": w["end"],
                }
                if file:
                    word_dict["file"] = file
                words.append(word_dict)
        return words

    # Synthesize word-level timestamps from sentence-level data
    if log_info and file:
        import os
        logger.info(
            f"Synthesizing word-level timestamps for '{os.path.basename(file)}' "
            f"(original transcript has sentence-level timestamps only)"
        )

    for line in transcript:
        content = line["content"]
        start_time = line["start"]
        end_time = line["end"]
        duration = end_time - start_time

        # Split content into words
        word_list = content.split()
        if not word_list:
            continue

        # Distribute time evenly across words
        time_per_word = duration / len(word_list)

        for i, word in enumerate(word_list):
            word_start = start_time + (i * time_per_word)
            word_end = start_time + ((i + 1) * time_per_word)
            word_dict = {
                "word": word,
                "start": word_start,
                "end": word_end,
            }
            if file:
                word_dict["file"] = file
            words.append(word_dict)

    return words


def extract_words_from_transcript(
    transcript: list[dict],
    file: str | None = None
) -> list[dict]:
    """
    Extract words from transcript, using existing word timestamps if available,
    or synthesizing them if not.

    This is a convenience wrapper around synthesize_word_timestamps() that
    handles the common case of extracting words for search operations.

    Args:
        transcript: List of transcript segments.
        file: Optional filename to include in word dicts.

    Returns:
        List of word dicts with 'word', 'start', 'end' (and optionally 'file') keys.
    """
    return synthesize_word_timestamps(transcript, file=file, log_info=True)
