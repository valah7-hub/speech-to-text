"""Model loading, caching, and lifecycle management."""

import gc
import threading

from core.recognizer import load_model, create_recognizer, BaseSpeechRecognizer
from core.gpu_detector import get_compute_type


class ModelManager:
    """Lazy-loads and caches Whisper models. Thread-safe."""

    def __init__(self):
        self._models: dict[tuple, object] = {}  # (engine, model, device) -> model
        self._recognizers: dict[tuple, BaseSpeechRecognizer] = {}
        self._loading = False
        self._lock = threading.Lock()

    def get_recognizer(self, engine: str, model_name: str, device: str,
                       on_progress=None) -> BaseSpeechRecognizer:
        """Get or create a recognizer. Loads model if needed."""
        key = (engine, model_name, device)

        with self._lock:
            if key in self._recognizers:
                return self._recognizers[key]

        # Load outside lock (can be slow)
        if on_progress:
            on_progress(f"Загрузка модели {model_name}...")

        self._loading = True
        compute_type = get_compute_type(device)
        model = load_model(engine, model_name, device, compute_type)
        recognizer = create_recognizer(engine, model, device=device)

        with self._lock:
            self._models[key] = model
            self._recognizers[key] = recognizer

        self._loading = False
        if on_progress:
            on_progress("Модель загружена")

        return recognizer

    def unload_all(self):
        """Unload all cached models and free memory."""
        with self._lock:
            self._models.clear()
            self._recognizers.clear()

        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except (ImportError, Exception):
            pass

    def reload(self, engine: str, model_name: str, device: str,
               on_progress=None) -> BaseSpeechRecognizer:
        """Unload everything and load a new model."""
        self.unload_all()
        return self.get_recognizer(engine, model_name, device, on_progress)

    @property
    def is_loading(self) -> bool:
        return self._loading

    @property
    def loaded_models(self) -> list[tuple]:
        """List of (engine, model_name, device) currently loaded."""
        with self._lock:
            return list(self._models.keys())
