"""GPU detection, model recommendation, and model cache info."""

import os

# Cache result so we don't spam console
_cached_device: str | None = None


def detect_device(verbose: bool = False) -> str:
    """Detect available compute device. Returns 'cuda' or 'cpu'."""
    global _cached_device
    if _cached_device is not None:
        return _cached_device

    # Try PyTorch CUDA
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            if verbose:
                print(f"GPU: {gpu_name} ({vram_gb:.1f} GB VRAM)")
            _cached_device = "cuda"
            return "cuda"
    except ImportError:
        pass

    # Try CTranslate2
    try:
        import ctranslate2
        if "cuda" in ctranslate2.get_supported_compute_types("cuda"):
            _cached_device = "cuda"
            return "cuda"
    except Exception:
        pass

    _cached_device = "cpu"
    return "cpu"


def get_vram_gb() -> float:
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    except (ImportError, Exception):
        pass
    return 0.0


def get_recommended_model(device: str) -> str:
    """Medium recommended for Russian language quality."""
    if device == "cpu":
        return "medium"
    vram = get_vram_gb()
    if vram >= 6:
        return "medium"
    elif vram >= 4:
        return "small"
    return "medium"


def get_compute_type(device: str) -> str:
    return "float16" if device == "cuda" else "int8"


# --- Model cache info ---

MODEL_SIZES = {
    "tiny": "~75 MB",
    "base": "~150 MB",
    "small": "~500 MB",
    "medium": "~1.5 GB",
    "large-v3": "~3 GB",
}


def get_downloaded_models() -> dict[str, int]:
    """Check which models are already downloaded.

    Returns dict: model_name -> size_in_mb (0 if not downloaded).
    """
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    downloaded = {}

    for model_name in MODEL_SIZES:
        # Check faster-whisper cache
        dir_name = f"models--Systran--faster-whisper-{model_name}"
        path = os.path.join(cache_dir, dir_name)
        if os.path.exists(path):
            size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, dn, fns in os.walk(path)
                for f in fns
            )
            downloaded[model_name] = size // (1024 * 1024)
        else:
            downloaded[model_name] = 0

    return downloaded


def get_installed_engines() -> dict[str, bool]:
    """Check which speech engines are installed."""
    engines = {}
    try:
        import whisper
        engines["whisper"] = True
    except ImportError:
        engines["whisper"] = False
    try:
        from faster_whisper import WhisperModel
        engines["faster-whisper"] = True
    except ImportError:
        engines["faster-whisper"] = False
    try:
        import whisperx
        engines["whisperx"] = True
    except ImportError:
        engines["whisperx"] = False
    return engines


def format_engine_label(name: str, installed: dict[str, bool]) -> str:
    """Format engine name with install status — short."""
    ok = "✓" if installed.get(name) else "✗"
    short = {"whisper": "OpenAI", "faster-whisper": "быстрый",
             "whisperx": "таймкоды"}
    return f"{name}  {short.get(name, '')}  [{ok}]"


def format_model_label(name: str, downloaded: dict[str, int],
                       recommended: str) -> str:
    """Format model name — short."""
    size = MODEL_SIZES.get(name, "?")
    if downloaded.get(name, 0) > 0:
        st = "✓"
    else:
        st = size
    rec = " ★" if name == recommended else ""
    return f"{name}  ({st}){rec}"
