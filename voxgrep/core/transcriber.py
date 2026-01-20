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

from ..utils.config import (
    DEFAULT_WHISPER_MODEL,
    DEFAULT_MLX_MODEL,
    DEFAULT_DEVICE,
    DEFAULT_COMPUTE_TYPE
)
from ..utils.helpers import setup_logger
from ..utils.exceptions import (
    TranscriptionModelNotAvailableError,
    TranscriptionFailedError,
    FileNotFoundError as VoxGrepFileNotFoundError
)
from ..utils.audio import normalize_audio as norm_audio, get_normalized_cache_path, should_normalize_audio

logger = setup_logger(__name__)


def transcribe_whisper(
    videofile: str, 
    model_name: str = DEFAULT_WHISPER_MODEL, 
    prompt: Optional[str] = None, 
    language: Optional[str] = None, 
    device: str = DEFAULT_DEVICE, 
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    progress_callback: Optional[callable] = None,
    beam_size: int = 5,
    best_of: int = 5,
    vad_filter: bool = True,
    vad_parameters: Optional[dict] = None,
    normalize_audio: bool = False
) -> List[dict]:
    """
    Transcribes a video file using faster-whisper (CTranslate2)
    With word-level timestamps enabled.
    
    Args:
        progress_callback: Optional callback function(current_seconds, total_seconds)
        beam_size: Beam size for beam search (higher = more accurate but slower). Default: 5
        best_of: Number of candidates when sampling (higher = better quality). Default: 5
        vad_filter: Enable Voice Activity Detection to filter out non-speech. Default: True
        vad_parameters: Optional VAD parameters dict
        normalize_audio: Pre-process audio with loudnorm filter for better quality. Default: False
    """
    if not WHISPER_AVAILABLE:
        raise TranscriptionModelNotAvailableError(
            "faster-whisper is not installed. Install with 'pip install faster-whisper'"
        )

    logger.info(f"Transcribing {videofile} using faster-whisper ({model_name} model) on {device}")
    logger.info(f"Accuracy settings: beam_size={beam_size}, best_of={best_of}, vad_filter={vad_filter}, normalize_audio={normalize_audio}")
    
    # Audio normalization pre-processing
    actual_input_file = videofile
    if normalize_audio:
        try:
            from ..utils.audio import normalize_audio as norm_audio, get_normalized_cache_path, should_normalize_audio
            
            cache_path = get_normalized_cache_path(videofile)
            
            if should_normalize_audio(videofile):
                logger.info("Normalizing audio levels for improved transcription...")
                actual_input_file = norm_audio(videofile, output_file=cache_path)
                logger.info(f"Using normalized audio: {actual_input_file}")
            else:
                actual_input_file = cache_path
                logger.info(f"Using cached normalized audio: {actual_input_file}")
                
        except Exception as e:
            logger.warning(f"Audio normalization failed: {e}. Continuing with original audio.")
            actual_input_file = videofile
    
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
    
    # Transcribe with advanced parameters
    try:
        logger.info(f"Starting transcription with {model_name} model...")
        
        # Build transcription parameters
        transcribe_params = {
            "word_timestamps": True,
            "initial_prompt": prompt,
            "language": language,
            "beam_size": beam_size,
            "best_of": best_of,
            "vad_filter": vad_filter
        }
        
        # Add VAD parameters if provided
        if vad_parameters:
            transcribe_params["vad_parameters"] = vad_parameters
        
        segments_generator, info = model.transcribe(actual_input_file, **transcribe_params)
        
        logger.info(f"Transcription started. Detected language: {info.language}")
        
        out = []
        
        # Use callback if provided, otherwise use tqdm
        try:
            if progress_callback:
                current_time = 0
                for segment in segments_generator:
                    current_time = segment.end
                    
                    content = segment.text.strip()
                    # Pass text to callback if it accepts kwargs or 3 args
                    try:
                        progress_callback(current_time, info.duration, text=content)
                    except TypeError:
                        # Fallback for old callbacks
                        progress_callback(current_time, info.duration)
                    
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
                    # Print active segment to tqdm
                    pbar.write(f"[{segment.start:.2f}s] {content}")
                    
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
        
        except KeyboardInterrupt:
            logger.warning(f"Transcription cancelled by user. Saving {len(out)} partial segments...")
            if not progress_callback:
                pbar.close()
            # Continue to save partial results below
        
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
    prompt: Optional[str] = None,
    normalize_audio: bool = False
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

    # Audio normalization pre-processing
    actual_input_file = videofile
    if normalize_audio:
        try:
            cache_path = get_normalized_cache_path(videofile)
            
            if should_normalize_audio(videofile):
                logger.info("Normalizing audio levels for improved transcription...")
                actual_input_file = norm_audio(videofile, output_file=cache_path)
                logger.info(f"Using normalized audio: {actual_input_file}")
            else:
                actual_input_file = cache_path
                logger.info(f"Using cached normalized audio: {actual_input_file}")
                
        except Exception as e:
            logger.warning(f"Audio normalization failed: {e}. Continuing with original audio.")
            actual_input_file = videofile

    try:
        # mlx_whisper.transcribe returns "text" and "segments" in a dict
        result = mlx_whisper.transcribe(
            actual_input_file,
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
    progress_callback: Optional[callable] = None,
    on_existing_transcript: Optional[callable] = None,
    beam_size: int = 5,
    best_of: int = 5,
    vad_filter: bool = True,
    vad_parameters: Optional[dict] = None,
    normalize_audio: bool = False
) -> List[dict]:
    """
    Transcribes a video file using Whisper, handling caching and backend selection.
    
    Args:
        progress_callback: Optional callback function(current_seconds, total_seconds)
        on_existing_transcript: Optional callback(metadata) -> bool to ask user about reusing transcript.
                                Should return True to reuse, False to regenerate.
        beam_size: Beam size for accuracy (higher = better but slower)
        best_of: Number of candidates for sampling
        vad_filter: Enable Voice Activity Detection
        vad_parameters: Optional VAD parameters
        normalize_audio: Pre-process audio with loudnorm filter
    """
    if not os.path.exists(videofile):
        raise VoxGrepFileNotFoundError(f"Could not find file {videofile}")

    # Transcript file is based on the input filename
    transcript_file = os.path.splitext(videofile)[0] + ".json"
    metadata_file = os.path.splitext(videofile)[0] + ".transcript_meta.json"
    
    # Determine the model to use
    if device == "mlx":
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
    else:
        _model = model_name or DEFAULT_WHISPER_MODEL
    
    # Current transcription metadata
    current_metadata = {
        "model": _model,
        "device": device,
        "language": language,
        "compute_type": compute_type if device != "mlx" else None,
        "beam_size": beam_size,
        "vad_filter": vad_filter,
        "has_prompt": bool(prompt),
        "normalize_audio": normalize_audio
    }

    if os.path.exists(transcript_file):
        # Check if metadata exists and matches
        should_reuse = True
        
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "r", encoding="utf-8") as meta_file:
                    existing_metadata = json.load(meta_file)
                    
                # Check significant changes
                changes = []
                if existing_metadata.get("model") != current_metadata["model"]:
                    changes.append(f"Model: {existing_metadata.get('model')} -> {current_metadata['model']}")
                
                if existing_metadata.get("device") != current_metadata["device"]:
                    changes.append(f"Device: {existing_metadata.get('device')} -> {current_metadata['device']}")
                
                # Check detailed settings (default to standard values if missing)
                existing_beam = existing_metadata.get("beam_size", 5)
                if existing_beam != current_metadata["beam_size"]:
                    changes.append(f"Beam Size: {existing_beam} -> {current_metadata['beam_size']}")
                
                existing_vad = existing_metadata.get("vad_filter", True)
                if existing_vad != current_metadata["vad_filter"]:
                    changes.append(f"VAD: {existing_vad} -> {current_metadata['vad_filter']}")
                
                existing_prompt = existing_metadata.get("has_prompt", False)
                if existing_prompt != current_metadata["has_prompt"]:
                    changes.append(f"Vocabulary Prompt: {existing_prompt} -> {current_metadata['has_prompt']}")

                if changes:
                    if on_existing_transcript:
                        # Ask user what to do
                        should_reuse = on_existing_transcript(existing_metadata, current_metadata)
                    else:
                        # Non-interactive mode: log warning and reuse
                        logger.warning(
                            f"Existing transcript settings differ from requested: {', '.join(changes)}. "
                            f"Reusing existing transcript. Delete {transcript_file} to regenerate."
                        )
            except (json.JSONDecodeError, KeyError):
                logger.warning(f"Could not read metadata file {metadata_file}")
        
        if should_reuse:
            try:
                with open(transcript_file, "r", encoding="utf-8") as infile:
                    data = json.load(infile)
                    logger.info(f"Using existing transcript file: {transcript_file}")
                    return data
            except json.JSONDecodeError:
                logger.warning(f"Existing transcript file {transcript_file} is corrupt. Regenerating...")

    out = []
    
    # Check backend selection and transcribe
    if device == "mlx":
        out = transcribe_mlx(videofile, _model, language=language, prompt=prompt, normalize_audio=normalize_audio)
    else:
        out = transcribe_whisper(
            videofile, 
            _model, 
            prompt=prompt, 
            language=language, 
            device=device, 
            compute_type=compute_type,
            progress_callback=progress_callback,
            beam_size=beam_size,
            best_of=best_of,
            vad_filter=vad_filter,
            vad_parameters=vad_parameters,
            normalize_audio=normalize_audio
        )

    if not out:
        logger.warning(f"No speech detected in {videofile}")
        return []

    # Save transcript
    logger.info(f"Saving transcript to {transcript_file}")
    with open(transcript_file, "w", encoding="utf-8") as outfile:
        json.dump(out, outfile)
    
    # Save metadata
    with open(metadata_file, "w", encoding="utf-8") as meta_file:
        json.dump(current_metadata, meta_file, indent=2)

    return out
