"""Speech recognition engines — Strategy pattern with Whisper, Faster-Whisper, WhisperX."""

from abc import ABC, abstractmethod

import numpy as np


class BaseSpeechRecognizer(ABC):
    """Base interface for all speech recognition engines."""

    @abstractmethod
    def transcribe(self, audio: np.ndarray, language: str = "ru",
                   initial_prompt: str = None) -> str:
        """Transcribe audio array to text.

        Args:
            audio: float32 numpy array, 16kHz mono
            language: language code ('ru', 'en', 'auto')
            initial_prompt: vocabulary hint for the model
        Returns:
            Transcribed text string
        """
        pass


class WhisperRecognizer(BaseSpeechRecognizer):
    """OpenAI Whisper engine — оригинальный движок от OpenAI."""

    def __init__(self, model):
        self.model = model

    def transcribe(self, audio: np.ndarray, language: str = "ru",
                   initial_prompt: str = None) -> str:
        options = {"suppress_tokens": []}
        if language and language != "auto":
            options["language"] = language
        if initial_prompt:
            options["initial_prompt"] = initial_prompt

        result = self.model.transcribe(audio, **options)
        return result["text"].strip()


class FasterWhisperRecognizer(BaseSpeechRecognizer):
    """Faster-Whisper engine (CTranslate2) — в 2-4x быстрее оригинала."""

    def __init__(self, model):
        self.model = model

    def transcribe(self, audio: np.ndarray, language: str = "ru",
                   initial_prompt: str = None) -> str:
        lang = language if language and language != "auto" else None
        kwargs = {}
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt

        segments, _info = self.model.transcribe(audio, language=lang, **kwargs)
        text = " ".join(seg.text.strip() for seg in segments)
        return text.strip()


class WhisperXRecognizer(BaseSpeechRecognizer):
    """WhisperX engine — точные таймкоды + word-level alignment."""

    def __init__(self, model, device: str = "cpu"):
        self.model = model
        self.device = device

    def transcribe(self, audio: np.ndarray, language: str = "ru",
                   initial_prompt: str = None) -> str:
        import whisperx

        lang = language if language and language != "auto" else None
        result = self.model.transcribe(audio, language=lang)

        # WhisperX alignment for precise word timestamps
        if result.get("segments"):
            try:
                align_model, align_meta = whisperx.load_align_model(
                    language_code=result.get("language", "ru"),
                    device=self.device,
                )
                result = whisperx.align(
                    result["segments"], align_model, align_meta,
                    audio, self.device,
                )
            except Exception:
                pass  # Fallback to unaligned

        segments = result.get("segments", [])
        text = " ".join(seg.get("text", "").strip() for seg in segments)
        return text.strip()


def create_recognizer(engine: str, model, device: str = "cpu") -> BaseSpeechRecognizer:
    """Factory — create recognizer by engine name."""
    if engine == "whisper":
        return WhisperRecognizer(model)
    elif engine == "faster-whisper":
        return FasterWhisperRecognizer(model)
    elif engine == "whisperx":
        return WhisperXRecognizer(model, device=device)
    raise ValueError(f"Unknown engine: {engine}")


def load_model(engine: str, model_name: str, device: str,
               compute_type: str = None):
    """Load a Whisper model.

    Returns the raw model object (not wrapped in a recognizer).
    """
    if engine == "whisper":
        try:
            import whisper
        except ImportError:
            raise ImportError(
                "openai-whisper не установлен. Используйте faster-whisper "
                "или установите: pip install openai-whisper"
            )
        return whisper.load_model(model_name, device=device)
    elif engine == "faster-whisper":
        from faster_whisper import WhisperModel
        if compute_type is None:
            compute_type = "float16" if device == "cuda" else "int8"
        return WhisperModel(model_name, device=device,
                            compute_type=compute_type)
    elif engine == "whisperx":
        import whisperx
        if compute_type is None:
            compute_type = "float16" if device == "cuda" else "int8"
        return whisperx.load_model(model_name, device=device,
                                    compute_type=compute_type)
    raise ValueError(f"Unknown engine: {engine}")
