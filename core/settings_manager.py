"""Settings management — load/save settings.json with defaults and validation."""

import json
import os

DEFAULTS = {
    "engine": "faster-whisper",
    "device": "auto",
    "model": "base",
    "language": "ru",
    "hotkey": "ctrl+space",
    "remove_filler_words": True,
    "voice_commands": False,
    "streaming_insert": True,
    "sound_notifications": False,
    "ui_language": "ru",
    "vad_enabled": False,
    "ui_mode": "overlay",
    "window_x": 50,
    "window_y": 50,
    "window_width": 280,
    "window_height": 100,
    "indicator_x": 50,
    "indicator_y": 50,
    "font_size": "medium",
    "hf_token": "",
}

VALID_VALUES = {
    "engine": ("whisper", "faster-whisper", "whisperx"),
    "device": ("auto", "cpu", "cuda"),
    "model": ("tiny", "base", "small", "medium", "large-v3"),
    "language": ("ru", "en", "auto"),
    "ui_mode": ("overlay", "indicator"),
    "font_size": ("small", "medium", "large"),
}


class SettingsManager:
    def __init__(self, path: str = None):
        if path is None:
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "settings.json")
        self.path = path
        self._data: dict = {}
        self.load()

    def load(self):
        """Load settings from file, creating with defaults if missing."""
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            # Fill in any missing keys from defaults
            for key, value in DEFAULTS.items():
                if key not in self._data:
                    self._data[key] = value
        else:
            self._data = dict(DEFAULTS)
            self.save()

    def save(self):
        """Save current settings to file."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4, ensure_ascii=False)

    def get(self, key: str, default=None):
        """Get a setting value."""
        return self._data.get(key, default if default is not None else DEFAULTS.get(key))

    def set(self, key: str, value):
        """Set a setting value with validation."""
        if key in VALID_VALUES and value not in VALID_VALUES[key]:
            raise ValueError(
                f"Invalid value '{value}' for '{key}'. "
                f"Must be one of: {VALID_VALUES[key]}"
            )
        self._data[key] = value

    def is_first_run(self) -> bool:
        """Check if this is the first run (no settings file existed)."""
        return not os.path.exists(self.path)

    @property
    def data(self) -> dict:
        return dict(self._data)


if __name__ == "__main__":
    sm = SettingsManager()
    print("Settings loaded:")
    for k, v in sm.data.items():
        print(f"  {k}: {v}")
