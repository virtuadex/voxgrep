try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

import os
import json
import logging
from typing import List, Optional
from tqdm import tqdm

logger = logging.getLogger(__name__)

try:
    import mlx_whisper
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False

MAX_CHARS = 36


def transcribe_whisper(videofile: str, model_name: str = "large-v3", prompt: Optional[str] = None, language: Optional[str] = None, device: str = "cpu", compute_type: str = "int8") -> List[dict]:
    """
    Transcribes a video file using faster-whisper (CTranslate2)
    With word-level timestamps enabled.
    """
    if not WHISPER_AVAILABLE:
        raise ImportError("faster-whisper is not installed. Install with 'pip install faster-whisper'")

    logger.info(f"Transcribing {videofile} using faster-whisper ({model_name} model) on {device}")
    
    # Load model
    try:
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
    except Exception as e:
        logger.error(f"Could not load model {model_name} on {device}: {e}")
        if device == "cuda":
            logger.info("Falling back to CPU...")
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
        else:
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
        
        logger.info(f"Transcription started. Detected language: {info.language}")
        
        out = []
        pbar = tqdm(total=round(info.duration), unit="sec", desc="Transcribing")
        last_pos = 0
        for segment in segments_generator:
            # segment has .text, .start, .end, .words (list of Word objects)
            pbar.update(round(segment.end - last_pos))
            last_pos = segment.end
            
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
            # print(f"DEBUG: Processed segment: {content}")
        
        pbar.close()
        logger.info(f"Processed {len(out)} segments.")
        
        # Explicitly cleanup model to avoid crashes on return
        del model
        import gc
        gc.collect()
        
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        raise e
        
    return out


def transcribe_mlx(videofile: str, model_name: str = "mlx-community/whisper-large-v3-mlx", language: Optional[str] = None) -> List[dict]:
    """
    Transcribes a video file using mlx-whisper (Apple Silicon GPU)
    With word-level timestamps enabled.
    """
    if not MLX_AVAILABLE:
        raise ImportError("mlx-whisper is not installed. Install with 'pip install mlx-whisper'")

    logger.info(f"Transcribing {videofile} using mlx-whisper ({model_name})")

    try:
        # mlx_whisper.transcribe returns "text" and "segments" in a dict
        result = mlx_whisper.transcribe(
            videofile,
            path_or_hf_repo=model_name,
            word_timestamps=True,
            language=language
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
                    # mlx-whisper (like openai-whisper) returns words as dicts
                    w_list.append({
                        "word": w["word"].strip(),
                        "start": w["start"],
                        "end": w["end"],
                        "conf": w.get("probability", 1.0) # mlx might use probability
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
        raise e


def transcribe(videofile: str, model_name: str = "large-v3", method: str = "whisper", prompt: Optional[str] = None, language: Optional[str] = None, device: str = "cpu", compute_type: str = "int8") -> List[dict]:
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
    
    # Check if MLX is requested
    if device == "mlx":
        if not MLX_AVAILABLE:
             logger.error("mlx-whisper is not available. Please install it with 'pip install mlx-whisper'")
             return []
        # Use default MLX model if generic "large-v3" is passed, otherwise use what user provided
        if model_name == "large-v3" or model_name is None:
             _model = "mlx-community/whisper-large-v3-mlx"
        else:
             _model = model_name
             
        try:
             out = transcribe_mlx(videofile, _model, language=language)
             # Save logic is duplicated below, maybe return out here and let it fall through?
             # But "out" variable scope needs to be handled.
        except Exception as e:
             logger.error(f"MLX transcription failed: {e}")
             return []
    else:
        if not WHISPER_AVAILABLE:
            logger.error("faster-whisper is not available. Please install it with 'pip install faster-whisper'")
            return []

        # Default model if None provided
        _model = model_name if model_name else "large-v3"
        
        try:
            out = transcribe_whisper(videofile, _model, prompt=prompt, language=language, device=device, compute_type=compute_type)
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return []


    if len(out) == 0:
        logger.warning(f"No words found in {videofile}")
        return []

    logger.info(f"Saving transcript to {transcript_file}")
    with open(transcript_file, "w", encoding="utf-8") as outfile:
        json.dump(out, outfile)

    return out
