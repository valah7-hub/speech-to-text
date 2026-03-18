"""Streaming speech recognition — shows text in real-time as user speaks."""

import threading
import time
import numpy as np

from core.audio_recorder import AudioRecorder


class StreamRecognizer:
    """Real-time streaming transcription.

    Accumulates audio and sends chunks to the recognizer every few seconds,
    providing intermediate results. On stop, runs a final pass for correction.
    """

    def __init__(self, recognizer, language: str = "ru",
                 initial_prompt: str = None,
                 chunk_interval: float = 2.5):
        """
        Args:
            recognizer: BaseSpeechRecognizer instance
            language: language code
            initial_prompt: vocabulary hint
            chunk_interval: seconds between intermediate transcriptions
        """
        self.recognizer = recognizer
        self.language = language
        self.initial_prompt = initial_prompt
        self.chunk_interval = chunk_interval

        self._recorder = AudioRecorder()
        self._running = False
        self._thread: threading.Thread | None = None
        self._all_audio: list[np.ndarray] = []

        # Callbacks
        self.on_partial: callable = None   # on_partial(text) — intermediate
        self.on_final: callable = None     # on_final(text) — final result
        self.on_error: callable = None     # on_error(message)
        self.on_audio_level: callable = None  # on_audio_level(float 0-1)

    def start(self):
        """Start streaming recording + recognition."""
        self._running = True
        self._all_audio = []
        self._recorder.start()
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop streaming. Triggers final transcription pass."""
        self._running = False
        audio = self._recorder.stop()
        if audio is not None and len(audio) > 0:
            self._all_audio.append(audio)

        # Final pass on complete audio
        threading.Thread(target=self._final_pass, daemon=True).start()

    def _stream_loop(self):
        """Periodically transcribe accumulated audio for partial results."""
        last_transcribe_time = time.time()

        while self._running:
            time.sleep(0.05)

            # Calculate and report audio level every iteration
            if self.on_audio_level and self._recorder._frames:
                try:
                    # Use last few frames for smoother reading
                    frames = self._recorder._frames[-3:]
                    chunk = np.concatenate(frames, axis=0).flatten()
                    rms = float(np.sqrt(np.mean(chunk ** 2)))
                    # Amplify heavily for visible response
                    level = min(1.0, rms * 40)
                    self.on_audio_level(level)
                except (IndexError, ValueError):
                    pass

            elapsed = time.time() - last_transcribe_time
            if elapsed < self.chunk_interval:
                continue

            # Get audio accumulated so far
            current_frames = list(self._recorder._frames)
            if not current_frames:
                continue

            audio = np.concatenate(current_frames, axis=0).flatten()
            if len(audio) / 16000 < 0.5:
                continue

            last_transcribe_time = time.time()

            # Transcribe current buffer (partial)
            try:
                text = self.recognizer.transcribe(
                    audio, language=self.language,
                    initial_prompt=self.initial_prompt,
                )
                if text and self.on_partial:
                    self.on_partial(text)
            except Exception:
                pass  # Don't interrupt streaming on partial errors

    def _final_pass(self):
        """Run final transcription on the complete audio."""
        if not self._all_audio:
            # Grab whatever was recorded
            frames = list(self._recorder._frames)
            if frames:
                self._all_audio = [np.concatenate(frames, axis=0).flatten()]

        if not self._all_audio:
            if self.on_error:
                self.on_error("Нет аудио для распознавания")
            return

        full_audio = np.concatenate(self._all_audio, axis=0).flatten()
        duration = len(full_audio) / 16000

        if duration < 0.8:
            # Too short — skip (Whisper hallucinates on very short audio)
            if self.on_error:
                self.on_error("")  # Silent skip
            return

        # Check if audio is mostly silence
        rms = float(np.sqrt(np.mean(full_audio ** 2)))
        if rms < 0.01:
            # Audio is silence — Whisper would hallucinate
            if self.on_error:
                self.on_error("")  # Silent skip
            return

        try:
            text = self.recognizer.transcribe(
                full_audio, language=self.language,
                initial_prompt=self.initial_prompt,
            )

            # Filter known Whisper hallucinations on near-silence
            if text and self._is_hallucination(text):
                if self.on_error:
                    self.on_error("")
                return

            if text and self.on_final:
                self.on_final(text, duration)
            elif not text and self.on_error:
                self.on_error("")
        except Exception as e:
            if self.on_error:
                self.on_error(f"Ошибка: {e}")

    @staticmethod
    def _is_hallucination(text: str) -> bool:
        """Detect common Whisper hallucination patterns on silence."""
        t = text.lower().strip()
        # Common Russian hallucinations
        hallucination_phrases = [
            "редактор субтитров",
            "субтитры",
            "корректор",
            "егорова",
            "переводчик",
            "продолжение следует",
            "подписывайтесь",
            "спасибо за просмотр",
            "до свидания",
            "благодарю за внимание",
            "srt",
            "www.",
            "http",
            "амара",
            "amara",
        ]
        for phrase in hallucination_phrases:
            if phrase in t:
                return True
        # Dots, ellipsis, very short junk
        if len(t) < 4:
            return True
        # Only dots, commas, spaces, dashes
        cleaned = t.replace(".", "").replace(",", "").replace(" ", "").replace("-", "").replace("…", "").replace("?", "").replace("!", "")
        if len(cleaned) < 2:
            return True
        return False

    @property
    def is_running(self) -> bool:
        return self._running
