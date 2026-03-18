"""Voice Activity Detection — auto-listen and trigger recording."""

import threading
import time
import numpy as np
import sounddevice as sd


class VADListener:
    """Continuously listens to microphone and detects speech.

    When speech is detected, calls on_speech_start.
    When silence is detected after speech, calls on_speech_end.
    """

    def __init__(self, sample_rate: int = 16000,
                 threshold: float = 0.02,
                 silence_duration: float = 2.0,
                 min_speech_duration: float = 0.8):
        """
        Args:
            sample_rate: audio sample rate
            threshold: RMS level above which is considered speech
            silence_duration: seconds of silence before stopping
            min_speech_duration: minimum speech duration to trigger
        """
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration

        self._running = False
        self._stream: sd.InputStream | None = None
        self._thread: threading.Thread | None = None

        # State
        self._is_speaking = False
        self._speech_start_time = 0.0
        self._last_speech_time = 0.0
        self._audio_frames: list[np.ndarray] = []

        # Callbacks
        self.on_speech_start: callable = None
        self.on_speech_end: callable = None  # on_speech_end(audio: np.ndarray)
        self.on_audio_level: callable = None

    def start(self):
        """Start listening for speech."""
        if self._running:
            return
        self._running = True
        self._is_speaking = False
        self._audio_frames = []

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * 0.1),  # 100ms blocks
        )
        self._stream.start()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop listening."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._is_speaking = False

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio chunk."""
        if not self._running:
            return

        chunk = indata.copy()
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        level = min(1.0, rms * 15)

        if self.on_audio_level:
            self.on_audio_level(level)

        if rms > self.threshold:
            self._last_speech_time = time.time()

            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start_time = time.time()
                self._audio_frames = []

        if self._is_speaking:
            self._audio_frames.append(chunk)

    def _monitor_loop(self):
        """Monitor for silence after speech."""
        while self._running:
            time.sleep(0.1)

            if not self._is_speaking:
                continue

            silence_elapsed = time.time() - self._last_speech_time
            speech_duration = time.time() - self._speech_start_time

            if silence_elapsed >= self.silence_duration:
                self._is_speaking = False

                if speech_duration >= self.min_speech_duration and self._audio_frames:
                    audio = np.concatenate(self._audio_frames, axis=0).flatten()
                    self._audio_frames = []

                    if self.on_speech_end:
                        self.on_speech_end(audio)
                else:
                    self._audio_frames = []

    @property
    def is_listening(self) -> bool:
        return self._running

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
