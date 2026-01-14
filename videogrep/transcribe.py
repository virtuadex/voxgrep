try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

import os
import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

MAX_CHARS = 36


def transcribe_whisper(videofile: str, model_name: str = "medium", prompt: Optional[str] = None, language: Optional[str] = None) -> List[dict]:
    """
    Transcribes a video file using faster-whisper (CTranslate2)
    With word-level timestamps enabled.
    """
    if not WHISPER_AVAILABLE:
        raise ImportError("faster-whisper is not installed. Install with 'pip install faster-whisper'")

    logger.info(f"Transcribing {videofile} using faster-whisper ({model_name} model)")
    
    # Check for caching env var if we want to support it, otherwise default
    # download_root = os.getenv("WHISPER_CACHE_DIR", None) 
    
    # Load model
    try:
        # device="auto" usually selects CPU on Macs if CTranslate2 doesn't find CUDA.
        # compute_type="int8" is efficient for CPU.
        model = WhisperModel(model_name, device="auto", compute_type="int8")
    except Exception as e:
        logger.error(f"Could not load model {model_name}: {e}")
        raise e
    
    # Transcribe
    try:
        logger.info(f"Starting transcription with {model_name} model...")
        segments_generator, info = model.transcribe(
            videofile, 
            word_timestamps=True, 
            initial_prompt=prompt,
            language=language
        )
        
        # faster-whisper returns a generator, so we iterate to get results
        segments = list(segments_generator)
        logger.info(f"Transcription finished. Detected language: {info.language}")
        
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        raise e
    
    out = []
    
    try:
        for segment in segments:
            # segment has .text, .start, .end, .words (list of Word objects)
            
            content = segment.text.strip()
            start_sec = segment.start
            end_sec = segment.end
            
            w_list = []
            if segment.words:
                for w in segment.words:
                    w_list.append({
                        "word": w.word.strip(),
                        "start": w.start,
                        "end": w.end,
                        "conf": w.probability
                    })
            
            item = {
                "content": content,
                "start": start_sec,
                "end": end_sec,
                "words": w_list
            }
            
            out.append(item)
            
        logger.info(f"Processed {len(out)} segments.")
    except Exception as e:
        logger.error(f"Error processing segments: {e}")
        raise e
        
    return out


def transcribe(videofile: str, model_name: str = "medium", method: str = "whisper", prompt: Optional[str] = None, language: Optional[str] = None) -> List[dict]:
    """
    Transcribes a video file using Whisper.
    """
    transcript_file = os.path.splitext(videofile)[0] + ".json"

    if os.path.exists(transcript_file):
        with open(transcript_file, "r") as infile:
            try:
                data = json.load(infile)
                return data
            except json.JSONDecodeError:
                pass

    if not os.path.exists(videofile):
        logger.error(f"Could not find file {videofile}")
        return []

    if not WHISPER_AVAILABLE:
        logger.error("faster-whisper is not available. Please install it with 'pip install faster-whisper'")
        return []

    # Default model if None provided
    _model = model_name if model_name else "medium"
    
    try:
        out = transcribe_whisper(videofile, _model, prompt=prompt, language=language)
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return []

    if len(out) == 0:
        logger.warning(f"No words found in {videofile}")
        return []

    with open(transcript_file, "w", encoding="utf-8") as outfile:
        json.dump(out, outfile)

    return out
