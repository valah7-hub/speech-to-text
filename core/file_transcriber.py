"""Transcribe audio files — supports mp3, wav, m4a, ogg, flac."""

import os
import numpy as np


SUPPORTED_FORMATS = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".wma", ".webm")


class Segment:
    """A single transcription segment with timestamps."""
    __slots__ = ("start", "end", "text", "speaker")

    def __init__(self, start: float, end: float, text: str, speaker: str = ""):
        self.start = start
        self.end = end
        self.text = text
        self.speaker = speaker

    def __repr__(self):
        prefix = f"[{self.speaker}] " if self.speaker else ""
        return f"{prefix}[{self._fmt(self.start)}-{self._fmt(self.end)}] {self.text}"

    @staticmethod
    def _fmt(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


def load_audio_file(path: str, target_sr: int = 16000) -> np.ndarray:
    """Load an audio file and convert to 16kHz mono float32.

    Requires pydub + ffmpeg in PATH.
    """
    from pydub import AudioSegment

    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {ext}. "
                         f"Supported: {SUPPORTED_FORMATS}")

    audio = AudioSegment.from_file(path)
    # Convert to mono 16kHz
    audio = audio.set_channels(1).set_frame_rate(target_sr)
    # Convert to float32 numpy array
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    samples /= 2 ** 15  # int16 -> float32 [-1, 1]
    return samples


class FileTranscriber:
    """Transcribes audio files using a loaded recognizer."""

    def __init__(self, recognizer, text_processor=None, language: str = "ru",
                 initial_prompt: str = None):
        self.recognizer = recognizer
        self.text_processor = text_processor
        self.language = language
        self.initial_prompt = initial_prompt

    def transcribe_file(self, path: str,
                        on_progress=None) -> list[Segment]:
        """Transcribe an audio file into segments.

        Args:
            path: path to audio file
            on_progress: callback(percent: int, message: str)

        Returns:
            list of Segment objects
        """
        if on_progress:
            on_progress(0, "Загрузка файла...")

        audio = load_audio_file(path)
        total_duration = len(audio) / 16000

        if on_progress:
            on_progress(10, f"Файл загружен ({total_duration:.0f} сек)")

        # Use faster-whisper segments if available
        segments = self._transcribe_with_timestamps(audio, on_progress)

        # Post-process each segment
        if self.text_processor:
            for seg in segments:
                seg.text = self.text_processor.process(seg.text)

        if on_progress:
            on_progress(100, "Готово")

        return segments

    def _transcribe_with_timestamps(self, audio: np.ndarray,
                                     on_progress=None) -> list[Segment]:
        """Get segments with timestamps from the recognizer."""
        model = self.recognizer.model

        # Try faster-whisper (returns segments natively)
        if hasattr(model, "transcribe") and not hasattr(model, "decode"):
            return self._transcribe_faster_whisper(model, audio, on_progress)

        # Fallback: openai-whisper
        return self._transcribe_whisper(model, audio, on_progress)

    def _transcribe_faster_whisper(self, model, audio, on_progress):
        """Transcribe using faster-whisper with segment timestamps."""
        lang = self.language if self.language != "auto" else None
        kwargs = {}
        if self.initial_prompt:
            kwargs["initial_prompt"] = self.initial_prompt

        raw_segments, info = model.transcribe(
            audio, language=lang, **kwargs
        )

        segments = []
        for i, seg in enumerate(raw_segments):
            segments.append(Segment(
                start=seg.start, end=seg.end, text=seg.text.strip()
            ))
            if on_progress and info.duration > 0:
                pct = min(95, 10 + int(85 * seg.end / info.duration))
                on_progress(pct, f"Обработка... {seg.end:.0f}/{info.duration:.0f} сек")

        return segments

    def _transcribe_whisper(self, model, audio, on_progress):
        """Transcribe using openai-whisper with segment timestamps."""
        options = {"suppress_tokens": []}
        if self.language and self.language != "auto":
            options["language"] = self.language
        if self.initial_prompt:
            options["initial_prompt"] = self.initial_prompt

        if on_progress:
            on_progress(15, "Распознавание...")

        result = model.transcribe(audio, **options)

        segments = []
        for seg in result.get("segments", []):
            segments.append(Segment(
                start=seg["start"], end=seg["end"],
                text=seg["text"].strip(),
            ))

        return segments


def format_segments_plain(segments: list[Segment]) -> str:
    """Format segments as plain text with timestamps."""
    lines = []
    for seg in segments:
        ts = f"[{Segment._fmt(seg.start)}-{Segment._fmt(seg.end)}]"
        prefix = f"[{seg.speaker}] " if seg.speaker else ""
        lines.append(f"{ts} {prefix}{seg.text}")
    return "\n".join(lines)


def format_segments_srt(segments: list[Segment]) -> str:
    """Format segments as SRT subtitles."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _srt_time(seg.start)
        end = _srt_time(seg.end)
        prefix = f"[{seg.speaker}] " if seg.speaker else ""
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(f"{prefix}{seg.text}")
        lines.append("")
    return "\n".join(lines)


def format_segments_vtt(segments: list[Segment]) -> str:
    """Format segments as WebVTT subtitles."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _vtt_time(seg.start)
        end = _vtt_time(seg.end)
        prefix = f"<v {seg.speaker}>" if seg.speaker else ""
        lines.append(f"{start} --> {end}")
        lines.append(f"{prefix}{seg.text}")
        lines.append("")
    return "\n".join(lines)


def _srt_time(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_time(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
