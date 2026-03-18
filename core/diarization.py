"""Speaker diarization — identify who speaks when using whisperX + pyannote."""

from core.file_transcriber import Segment


class Diarizer:
    """Speaker diarization using whisperX pipeline."""

    def __init__(self, hf_token: str = ""):
        self.hf_token = hf_token
        self._available = None

    @property
    def is_available(self) -> bool:
        """Check if whisperX and pyannote are installed."""
        if self._available is None:
            try:
                import whisperx
                self._available = True
            except ImportError:
                self._available = False
        return self._available

    def diarize(self, audio_path: str, segments: list[Segment],
                num_speakers: int = 0,
                on_progress=None) -> list[Segment]:
        """Add speaker labels to existing segments.

        Args:
            audio_path: path to the audio file
            segments: existing transcription segments
            num_speakers: expected number of speakers (0 = auto)
            on_progress: callback(percent, message)

        Returns:
            segments with speaker labels filled in
        """
        if not self.is_available:
            raise RuntimeError(
                "whisperX не установлен. Установите: pip install whisperx"
            )

        if not self.hf_token:
            raise RuntimeError(
                "Нужен Hugging Face токен для pyannote.\n"
                "Получите на huggingface.co/settings/tokens\n"
                "и укажите в настройках."
            )

        import whisperx

        if on_progress:
            on_progress(0, "Загрузка аудио для diarization...")

        audio = whisperx.load_audio(audio_path)

        if on_progress:
            on_progress(30, "Определение говорящих...")

        # Build diarization pipeline
        diarize_model = whisperx.DiarizationPipeline(
            use_auth_token=self.hf_token
        )

        diarize_kwargs = {}
        if num_speakers > 0:
            diarize_kwargs["num_speakers"] = num_speakers

        diarize_segments = diarize_model(audio, **diarize_kwargs)

        if on_progress:
            on_progress(70, "Привязка говорящих к сегментам...")

        # Convert our segments to whisperX format for assignment
        wx_segments = [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in segments
        ]

        result = whisperx.assign_word_speakers(diarize_segments, {
            "segments": wx_segments
        })

        # Update segments with speaker info
        for i, wx_seg in enumerate(result.get("segments", [])):
            if i < len(segments):
                speaker = wx_seg.get("speaker", "")
                if speaker:
                    # Convert SPEAKER_00 -> Говорящий 1
                    try:
                        num = int(speaker.split("_")[-1]) + 1
                        segments[i].speaker = f"Говорящий {num}"
                    except (ValueError, IndexError):
                        segments[i].speaker = speaker

        if on_progress:
            on_progress(100, "Diarization завершена")

        return segments
