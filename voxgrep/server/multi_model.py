"""
VoxGrep Multi-Model Transcription Module (Phase 3)

Provides unified interface for multiple transcription backends:
- faster-whisper (CTranslate2, CPU/CUDA)
- MLX-Whisper (Apple Silicon GPU)
- OpenAI Whisper API (cloud)
- Local transformers models

Supports model hot-swapping and performance optimization.
"""
import os
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from ..config import (
    DEFAULT_WHISPER_MODEL,
    DEFAULT_MLX_MODEL,
    DEFAULT_DEVICE,
    DEFAULT_COMPUTE_TYPE
)
from ..utils import setup_logger

logger = setup_logger(__name__)


class TranscriptionBackend(str, Enum):
    """Available transcription backends."""
    FASTER_WHISPER = "faster-whisper"
    MLX_WHISPER = "mlx-whisper"
    OPENAI_API = "openai-api"
    TRANSFORMERS = "transformers"


@dataclass
class TranscriptionResult:
    """Result from transcription."""
    segments: List[dict]
    language: Optional[str] = None
    duration: Optional[float] = None
    backend: Optional[str] = None


@dataclass
class ModelInfo:
    """Information about a transcription model."""
    name: str
    backend: TranscriptionBackend
    description: str
    is_available: bool
    requires_gpu: bool = False
    requires_api_key: bool = False
    estimated_speed: str = "1x"  # Relative to real-time
    languages: Optional[List[str]] = None


class TranscriptionProvider(ABC):
    """Abstract base class for transcription providers."""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available."""
        pass
    
    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe an audio/video file."""
        pass
    
    @abstractmethod
    def get_models(self) -> List[ModelInfo]:
        """Get list of available models for this provider."""
        pass


class FasterWhisperProvider(TranscriptionProvider):
    """Provider for faster-whisper (CTranslate2)."""
    
    def __init__(self):
        self._model = None
        self._model_name = None
        
    def is_available(self) -> bool:
        try:
            from faster_whisper import WhisperModel
            return True
        except ImportError:
            return False
    
    def transcribe(
        self,
        audio_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        device: str = DEFAULT_DEVICE,
        compute_type: str = DEFAULT_COMPUTE_TYPE,
        **kwargs
    ) -> TranscriptionResult:
        from faster_whisper import WhisperModel
        
        model_name = model or DEFAULT_WHISPER_MODEL
        
        # Load or reuse model
        if self._model is None or self._model_name != model_name:
            logger.info(f"Loading faster-whisper model: {model_name} on {device}")
            self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
            self._model_name = model_name
        
        # Transcribe
        segments_gen, info = self._model.transcribe(
            audio_path,
            word_timestamps=True,
            language=language,
            initial_prompt=kwargs.get("prompt")
        )
        
        segments = []
        for seg in segments_gen:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": w.start,
                        "end": w.end,
                        "conf": w.probability
                    })
            
            segments.append({
                "content": seg.text.strip(),
                "start": seg.start,
                "end": seg.end,
                "words": words
            })
        
        return TranscriptionResult(
            segments=segments,
            language=info.language,
            duration=info.duration,
            backend=TranscriptionBackend.FASTER_WHISPER.value
        )
    
    def get_models(self) -> List[ModelInfo]:
        whisper_models = [
            ("tiny", "Fastest, lowest quality", "10x"),
            ("base", "Fast, basic quality", "5x"),
            ("small", "Balanced speed/quality", "3x"),
            ("medium", "Good quality", "1.5x"),
            ("large-v2", "High quality", "0.5x"),
            ("large-v3", "Best quality", "0.5x"),
        ]
        
        return [
            ModelInfo(
                name=name,
                backend=TranscriptionBackend.FASTER_WHISPER,
                description=desc,
                is_available=self.is_available(),
                requires_gpu=False,
                estimated_speed=speed
            )
            for name, desc, speed in whisper_models
        ]


class MLXWhisperProvider(TranscriptionProvider):
    """Provider for MLX-Whisper (Apple Silicon)."""
    
    def is_available(self) -> bool:
        try:
            import mlx_whisper
            import platform
            # Only available on Apple Silicon
            return platform.system() == "Darwin" and platform.machine() == "arm64"
        except ImportError:
            return False
    
    def transcribe(
        self,
        audio_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        import mlx_whisper
        
        model_name = model or DEFAULT_MLX_MODEL
        
        logger.info(f"Transcribing with MLX-Whisper: {model_name}")
        
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=model_name,
            word_timestamps=True,
            language=language,
            initial_prompt=kwargs.get("prompt")
        )
        
        segments = []
        for seg in result.get("segments", []):
            words = []
            if "words" in seg:
                for w in seg["words"]:
                    words.append({
                        "word": w["word"].strip(),
                        "start": w["start"],
                        "end": w["end"],
                        "conf": w.get("probability", 1.0)
                    })
            
            segments.append({
                "content": seg["text"].strip(),
                "start": seg["start"],
                "end": seg["end"],
                "words": words
            })
        
        return TranscriptionResult(
            segments=segments,
            language=result.get("language"),
            backend=TranscriptionBackend.MLX_WHISPER.value
        )
    
    def get_models(self) -> List[ModelInfo]:
        mlx_models = [
            ("mlx-community/whisper-tiny-mlx", "Tiny model for MLX", "15x"),
            ("mlx-community/whisper-base-mlx", "Base model for MLX", "8x"),
            ("mlx-community/whisper-small-mlx", "Small model for MLX", "5x"),
            ("mlx-community/whisper-medium-mlx", "Medium model for MLX", "2x"),
            ("mlx-community/whisper-large-v3-mlx", "Large-v3 for MLX", "1x"),
        ]
        
        return [
            ModelInfo(
                name=name,
                backend=TranscriptionBackend.MLX_WHISPER,
                description=desc,
                is_available=self.is_available(),
                requires_gpu=True,
                estimated_speed=speed
            )
            for name, desc, speed in mlx_models
        ]


class OpenAIAPIProvider(TranscriptionProvider):
    """Provider for OpenAI's Whisper API (cloud)."""
    
    def is_available(self) -> bool:
        try:
            import openai
            return bool(os.getenv("OPENAI_API_KEY"))
        except ImportError:
            return False
    
    def transcribe(
        self,
        audio_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        from openai import OpenAI
        
        client = OpenAI()
        
        # OpenAI API only supports whisper-1
        with open(audio_path, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )
        
        segments = []
        for seg in result.segments:
            words = []
            if hasattr(result, "words"):
                seg_words = [w for w in result.words if seg.start <= w.start < seg.end]
                for w in seg_words:
                    words.append({
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "conf": 1.0
                    })
            
            segments.append({
                "content": seg.text.strip(),
                "start": seg.start,
                "end": seg.end,
                "words": words
            })
        
        return TranscriptionResult(
            segments=segments,
            language=result.language,
            backend=TranscriptionBackend.OPENAI_API.value
        )
    
    def get_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                name="whisper-1",
                backend=TranscriptionBackend.OPENAI_API,
                description="OpenAI's cloud Whisper API",
                is_available=self.is_available(),
                requires_gpu=False,
                requires_api_key=True,
                estimated_speed="10x"
            )
        ]


class ModelManager:
    """
    Manages transcription models and provides unified interface.
    """
    
    def __init__(self):
        self._providers: Dict[TranscriptionBackend, TranscriptionProvider] = {}
        self._default_backend: Optional[TranscriptionBackend] = None
        
        # Initialize providers
        self._register_providers()
    
    def _register_providers(self):
        """Register all available providers."""
        providers = [
            (TranscriptionBackend.FASTER_WHISPER, FasterWhisperProvider()),
            (TranscriptionBackend.MLX_WHISPER, MLXWhisperProvider()),
            (TranscriptionBackend.OPENAI_API, OpenAIAPIProvider()),
        ]
        
        for backend, provider in providers:
            self._providers[backend] = provider
        
        # Set default backend
        self._default_backend = self._detect_best_backend()
    
    def _detect_best_backend(self) -> Optional[TranscriptionBackend]:
        """Detect the best available backend based on hardware."""
        import platform
        
        # Prefer MLX on Apple Silicon
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            if self._providers[TranscriptionBackend.MLX_WHISPER].is_available():
                logger.info("Detected Apple Silicon, using MLX-Whisper")
                return TranscriptionBackend.MLX_WHISPER
        
        # Fall back to faster-whisper
        if self._providers[TranscriptionBackend.FASTER_WHISPER].is_available():
            return TranscriptionBackend.FASTER_WHISPER
        
        # Fall back to OpenAI API
        if self._providers[TranscriptionBackend.OPENAI_API].is_available():
            return TranscriptionBackend.OPENAI_API
        
        return None
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get all available models from all providers."""
        models = []
        for provider in self._providers.values():
            models.extend(provider.get_models())
        return models
    
    def get_available_backends(self) -> List[dict]:
        """Get information about available backends."""
        return [
            {
                "backend": backend.value,
                "available": provider.is_available(),
                "is_default": backend == self._default_backend
            }
            for backend, provider in self._providers.items()
        ]
    
    def transcribe(
        self,
        audio_path: str,
        backend: Optional[TranscriptionBackend] = None,
        model: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe using the specified or best available backend.
        
        Args:
            audio_path: Path to audio/video file
            backend: Specific backend to use (auto-detect if None)
            model: Model name for the backend
            language: Language code
            **kwargs: Additional arguments for the provider
            
        Returns:
            TranscriptionResult with segments
        """
        target_backend = backend or self._default_backend
        
        if target_backend is None:
            raise RuntimeError("No transcription backend available")
        
        provider = self._providers.get(target_backend)
        if provider is None or not provider.is_available():
            raise RuntimeError(f"Backend {target_backend.value} is not available")
        
        logger.info(f"Transcribing with {target_backend.value}")
        return provider.transcribe(audio_path, model=model, language=language, **kwargs)
    
    def set_default_backend(self, backend: TranscriptionBackend):
        """Set the default transcription backend."""
        if backend in self._providers and self._providers[backend].is_available():
            self._default_backend = backend
            logger.info(f"Default backend set to {backend.value}")
        else:
            raise ValueError(f"Backend {backend.value} is not available")


# Global model manager instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get or create the global model manager."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
