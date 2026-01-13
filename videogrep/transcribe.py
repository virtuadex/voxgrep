try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

import imageio_ffmpeg
import os
import subprocess
import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

MAX_CHARS = 36
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")


def transcribe_whisper(videofile: str, model_name: str = "large", prompt: Optional[str] = None) -> List[dict]:
    """
    Transcribes a video file using OpenAI Whisper
    """
    if not WHISPER_AVAILABLE:
        raise ImportError("Whisper is not installed. Install with 'pip install openai-whisper'")

    logger.info(f"Transcribing {videofile} using Whisper ({model_name} model)")
    
    # Load model
    model = whisper.load_model(model_name)
    
    # Transcribe with word timestamps for compatibility with fragment search
    result = model.transcribe(videofile, word_timestamps=True, initial_prompt=prompt)
    
    out = []
    for segment in result['segments']:
        words = []
        if 'words' in segment:
            for w in segment['words']:
                words.append({
                    "word": w['word'].strip(),
                    "start": w['start'],
                    "end": w['end'],
                    "conf": w.get('probability', 1.0)
                })
        
        item = {
            "content": segment['text'].strip(),
            "start": segment['start'],
            "end": segment['end'],
            "words": words
        }
        out.append(item)
        
    return out


def transcribe_vosk(videofile: str, model_path: Optional[str] = None) -> List[dict]:
    """
    Transcribes a video file using Vosk
    """
    if not VOSK_AVAILABLE:
        raise ImportError("Vosk is not installed. Install with 'pip install vosk'")

    _model_path: str = MODEL_PATH
    if model_path is not None:
        _model_path = model_path

    if not os.path.exists(_model_path):
        logger.error(f"Could not find Vosk model folder at {_model_path}")
        return []

    logger.info(f"Transcribing {videofile} using Vosk")
    SetLogLevel(-1)

    sample_rate = 16000
    model = Model(_model_path)
    rec = KaldiRecognizer(model, sample_rate)
    rec.SetWords(True)

    process = subprocess.Popen(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-nostdin",
            "-loglevel",
            "quiet",
            "-i",
            videofile,
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-f",
            "s16le",
            "-",
        ],
        stdout=subprocess.PIPE,
    )

    result = []
    while True:
        data = process.stdout.read(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result.append(json.loads(rec.Result()))
    result.append(json.loads(rec.FinalResult()))

    out = []
    for r in result:
        if "result" not in r:
            continue
        words = [w for w in r["result"]]
        item = {"content": "", "start": None, "end": None, "words": []}
        for w in words:
            item["content"] += w["word"] + " "
            item["words"].append(w)
            if len(item["content"]) > MAX_CHARS or w == words[-1]:
                item["content"] = item["content"].strip()
                item["start"] = item["words"][0]["start"]
                item["end"] = item["words"][-1]["end"]
                out.append(item)
                item = {"content": "", "start": None, "end": None, "words": []}
    return out


def transcribe(videofile: str, model_path: Optional[str] = None, method: str = "whisper", prompt: Optional[str] = None) -> List[dict]:
    """
    Transcribes a video file. Tries Whisper first if method is whisper, 
    otherwise falls back to Vosk.
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

    out = []
    
    # Try the intended method first
    if method == "whisper" and WHISPER_AVAILABLE:
        try:
            # For whisper, model_path is actually the model name (e.g. 'base', 'medium', 'large')
            _model = "large"
            if model_path is not None:
                _model = model_path
            out = transcribe_whisper(videofile, _model, prompt=prompt)
        except Exception as e:
            logger.warning(f"Whisper transcription failed, falling back to Vosk: {e}")
            if VOSK_AVAILABLE:
                out = transcribe_vosk(videofile, model_path)
    elif VOSK_AVAILABLE:
        out = transcribe_vosk(videofile, model_path)
    elif method == "whisper":
        logger.error("Whisper is not available and Vosk fallback failed.")
    else:
        logger.error("Vosk is not available.")

    if len(out) == 0:
        logger.warning(f"No words found in {videofile}")
        return []

    with open(transcript_file, "w", encoding="utf-8") as outfile:
        json.dump(out, outfile)

    return out
