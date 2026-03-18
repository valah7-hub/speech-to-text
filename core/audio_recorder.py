"""Audio recording via sounddevice with callback-based non-blocking capture."""

import numpy as np
import sounddevice as sd


class AudioRecorder:
    """Records audio from microphone. Non-blocking start/stop interface."""

    def __init__(self, sample_rate: int = 16000, device: int = None):
        self.sample_rate = sample_rate
        self.device = device  # None = system default
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._recording = False

    def start(self):
        """Start recording. Non-blocking — audio captured via callback."""
        self._frames = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return captured audio as float32 numpy array."""
        self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return np.array([], dtype=np.float32)
        audio = np.concatenate(self._frames, axis=0).flatten()
        self._frames = []
        return audio

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice in its own thread for each audio chunk."""
        if self._recording:
            self._frames.append(indata.copy())

    @property
    def is_recording(self) -> bool:
        return self._recording

    def get_duration(self) -> float:
        """Estimated duration of recorded audio in seconds."""
        if not self._frames:
            return 0.0
        total_samples = sum(f.shape[0] for f in self._frames)
        return total_samples / self.sample_rate

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices (deduplicated).

        Prefers WASAPI devices on Windows, filters out system/virtual devices.
        """
        devices = sd.query_devices()
        apis = {i: sd.query_hostapis(i)["name"] for i in range(len(sd.query_hostapis()))}

        # Collect all input devices grouped by base name
        by_name: dict[str, dict] = {}
        # Priority: WASAPI > DirectSound > MME > WDM-KS
        api_priority = {"Windows WASAPI": 4, "Windows DirectSound": 3,
                        "MME": 2, "Windows WDM-KS": 1}

        skip_keywords = ["стерео микшер", "stereo mix", "переназначение",
                         "первичный драйвер", "primary driver"]

        for i, d in enumerate(devices):
            if d["max_input_channels"] <= 0:
                continue

            name = d["name"].strip()
            name_lower = name.lower()

            # Skip virtual/system devices
            if any(kw in name_lower for kw in skip_keywords):
                continue

            api_name = apis.get(d["hostapi"], "")
            priority = api_priority.get(api_name, 0)

            # Use short base name for dedup (strip API suffixes)
            base = name.split("(")[0].strip() if "(" in name else name
            base = base[:30]

            if base not in by_name or priority > by_name[base].get("_priority", 0):
                by_name[base] = {
                    "index": i,
                    "name": name,
                    "channels": d["max_input_channels"],
                    "sample_rate": d["default_samplerate"],
                    "_priority": priority,
                }

        return [
            {k: v for k, v in info.items() if k != "_priority"}
            for info in by_name.values()
        ]


if __name__ == "__main__":
    import time
    print("Available microphones:")
    for d in AudioRecorder.list_devices():
        print(f"  [{d['index']}] {d['name']}")
    print()

    recorder = AudioRecorder()
    print("Recording 3 seconds...")
    recorder.start()
    time.sleep(3)
    audio = recorder.stop()

    print(f"Recorded: {audio.shape[0]} samples")
    print(f"Duration: {audio.shape[0] / 16000:.2f} sec")
    print(f"Dtype: {audio.dtype}")
    print(f"Range: [{audio.min():.4f}, {audio.max():.4f}]")
