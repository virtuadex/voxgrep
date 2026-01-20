import os
import json
from typing import List, Optional
from tqdm import tqdm

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import mlx_whisper
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False

from .config import (
    DEFAULT_WHISPER_MODEL,
    DEFAULT_MLX_MODEL,
    DEFAULT_DEVICE,
    DEFAULT_COMPUTE_TYPE
)
from .utils import setup_logger
from .exceptions import (
    TranscriptionModelNotAvailableError,
    TranscriptionFailedError,
    FileNotFoundError as VoxGrepFileNotFoundError
)

logger = setup_logger(__name__)


def transcribe_whisper(
    videofile: str, 
    model_name: str = DEFAULT_WHISPER_MODEL, 
    prompt: Optional[str] = None, 
    language: Optional[str] = None, 
    device: str = DEFAULT_DEVICE, 
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    progress_callback: Optional[callable] = None
) -> List[dict]:
    """
    Transcribes a video file using faster-whisper (CTranslate2)
    With word-level timestamps enabled.
    
    Args:
        progress_callback: Optional callback function(current_seconds, total_seconds)
    """
    if not WHISPER_AVAILABLE:
        raise TranscriptionModelNotAvailableError(
            "faster-whisper is not installed. Install with 'pip install faster-whisper'"
        )

    logger.info(f"Transcribing {videofile} using faster-whisper ({model_name} model) on {device}")
    
    # Load model
    try:
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
    except Exception as e:
        logger.error(f"Could not load model {model_name} on {device}: {e}")
        if device == "cuda":
            logger.info("Falling back to CPU...")
            try:
                model = WhisperModel(model_name, device="cpu", compute_type="int8")
            except Exception as e2:
                raise TranscriptionFailedError(f"Fallback to CPU failed: {e2}") from e2
        else:
            raise TranscriptionFailedError(f"Failed to load Whisper model: {e}") from e
    
    # Transcribe
    try:
        logger.info(f"Starting transcription with {model_name} model...")
        segments_generator, info = model.transcribe(
            videofile, 
            word_timestamps=True, 
            initial_prompt=prompt,
            language=language
        )
        
        logger.info(f"Transcription started. Detected language: {info.language}")
        
        out = []
        
        # Use callback if provided, otherwise use tqdm
        if progress_callback:
            current_time = 0
            for segment in segments_generator:
                current_time = segment.end
                progress_callback(current_time, info.duration)
                
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
        else:
            # Fallback to tqdm for non-CLI usage
            pbar = tqdm(total=info.duration, unit="sec", desc="Transcribing", bar_format="{l_bar}{bar}| {n:.2f}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]")
            
            for segment in segments_generator:
                pbar.update(segment.end - pbar.n)
                
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
            
            pbar.close()
        
        logger.info(f"Processed {len(out)} segments.")
        
        # Explicitly cleanup model to avoid crashes on return
        del model
        import gc
        gc.collect()
        
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        raise TranscriptionFailedError(f"Whisper transcription failed: {e}") from e
        
    return out


def transcribe_mlx(
    videofile: str, 
    model_name: str = DEFAULT_MLX_MODEL, 
    language: Optional[str] = None, 
    prompt: Optional[str] = None
) -> List[dict]:
    """
    Transcribes a video file using mlx-whisper (Apple Silicon GPU)
    With word-level timestamps enabled.
    """
    if not MLX_AVAILABLE:
        raise TranscriptionModelNotAvailableError(
            "mlx-whisper is not installed. Install with 'pip install mlx-whisper'"
        )

    logger.info(f"Transcribing {videofile} using mlx-whisper ({model_name})")

    try:
        # mlx_whisper.transcribe returns "text" and "segments" in a dict
        result = mlx_whisper.transcribe(
            videofile,
            path_or_hf_repo=model_name,
            word_timestamps=True,
            language=language,
            initial_prompt=prompt
        )
        
        out = []
        # result["segments"] is a list of dicts
        for segment in result["segments"]:
            content = segment["text"].strip()
            start_sec = segment["start"]
            end_sec = segment["end"]
            
            w_list = []
            if "words" in segment:
                for w in segment["words"]:
                    w_list.append({
                        "word": w["word"].strip(),
                        "start": w["start"],
                        "end": w["end"],
                        "conf": w.get("probability", 1.0)
                    })
            
            item = {
                "content": content,
                "start": start_sec,
                "end": end_sec,
                "words": w_list
            }
            out.append(item)
            
        logger.info(f"Processed {len(out)} segments.")
        return out

    except Exception as e:
        logger.error(f"Error during mlx transcription: {e}")
        raise TranscriptionFailedError(f"MLX transcription failed: {e}") from e


def transcribe(
    videofile: str, 
    model_name: Optional[str] = None, 
    prompt: Optional[str] = None, 
    language: Optional[str] = None, 
    device: str = DEFAULT_DEVICE, 
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    progress_callback: Optional[callable] = None
) -> List[dict]:
    """
    Transcribes a video file using Whisper, handling caching and backend selection.
    
    Args:
        progress_callback: Optional callback function(current_seconds, total_seconds)
    """
    if not os.path.exists(videofile):
        raise VoxGrepFileNotFoundError(f"Could not find file {videofile}")

    # Transcript file is based on the input filename
    transcript_file = os.path.splitext(videofile)[0] + ".json"

    if os.path.exists(transcript_file):
        with open(transcript_file, "r", encoding="utf-8") as infile:
            try:
                data = json.load(infile)
                logger.info(f"Using existing transcript file: {transcript_file}")
                return data
            except json.JSONDecodeError:
                logger.warning(f"Existing transcript file {transcript_file} is corrupt.")

    out = []
    
    # Check backend selection
    if device == "mlx":
        # Map short names to MLX community repos
        MLX_MODEL_MAPPING = {
            "tiny": "mlx-community/whisper-tiny-mlx",
            "base": "mlx-community/whisper-base-mlx",
            "small": "mlx-community/whisper-small-mlx",
            "medium": "mlx-community/whisper-medium-mlx",
            "large": "mlx-community/whisper-large-v3-mlx",
            "large-v3": "mlx-community/whisper-large-v3-mlx",
            "large-v2": "mlx-community/whisper-large-v2-mlx",
            "distil-large-v3": "mlx-community/distil-whisper-large-v3"
        }
        
        _model = model_name or DEFAULT_MLX_MODEL
        if _model in MLX_MODEL_MAPPING:
            _model = MLX_MODEL_MAPPING[_model]
            
        out = transcribe_mlx(videofile, _model, language=language, prompt=prompt)
    else:
        _model = model_name or DEFAULT_WHISPER_MODEL
        out = transcribe_whisper(
            videofile, 
            _model, 
            prompt=prompt, 
            language=language, 
            device=device, 
            compute_type=compute_type,
            progress_callback=progress_callback
        )

    if not out:
        logger.warning(f"No speech detected in {videofile}")
        return []

    logger.info(f"Saving transcript to {transcript_file}")
    with open(transcript_file, "w", encoding="utf-8") as outfile:
        json.dump(out, outfile)

    return out
