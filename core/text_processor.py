"""Post-processing of transcribed text — filler words, replacements, capitalization."""

import json
import os
import re


# Default filler words (Russian)
FILLER_WORDS = [
    "э-э", "эм", "ну", "вот", "как бы", "типа", "короче",
    "значит", "так сказать", "в общем", "слушай", "смотри",
]


class TextProcessor:
    """Applies post-processing to transcribed text."""

    def __init__(self, settings_manager=None, project_dir: str = None):
        self.settings = settings_manager
        if project_dir is None:
            project_dir = os.path.dirname(os.path.dirname(__file__))
        self.project_dir = project_dir
        self._replacements: dict[str, str] = {}
        self._load_replacements()

    def process(self, text: str) -> str:
        """Apply all active post-processing steps."""
        if not text:
            return text

        # 1. Remove filler words (if enabled)
        if self.settings and self.settings.get("remove_filler_words"):
            text = self._remove_fillers(text)

        # 2. Apply custom replacements
        text = self._apply_replacements(text)

        # 3. Auto-capitalize after sentence-ending punctuation
        text = self._auto_capitalize(text)

        # 4. Clean up double spaces
        text = re.sub(r"  +", " ", text).strip()

        return text

    def _remove_fillers(self, text: str) -> str:
        """Remove filler words while preserving sentence structure."""
        for filler in FILLER_WORDS:
            # Word-boundary aware removal (case-insensitive)
            pattern = r"\b" + re.escape(filler) + r"\b[,]?\s*"
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
        return text

    def _apply_replacements(self, text: str) -> str:
        """Apply custom word replacements from replacements.json."""
        for src, dst in self._replacements.items():
            # Word-boundary replacement, case-insensitive
            pattern = r"\b" + re.escape(src) + r"\b"
            text = re.sub(pattern, dst, text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def _auto_capitalize(text: str) -> str:
        """Capitalize first letter after . ! ?"""
        if not text:
            return text
        # Capitalize the very first character
        text = text[0].upper() + text[1:]
        # Capitalize after sentence endings
        text = re.sub(
            r"([.!?])\s+([a-zа-яё])",
            lambda m: m.group(1) + " " + m.group(2).upper(),
            text,
        )
        return text

    # --- Replacements management ---

    def _load_replacements(self):
        """Load custom replacements from replacements.json."""
        path = os.path.join(self.project_dir, "replacements.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._replacements = json.load(f)
        else:
            self._replacements = {}

    def _save_replacements(self):
        """Save replacements to file."""
        path = os.path.join(self.project_dir, "replacements.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._replacements, f, indent=2, ensure_ascii=False)

    def add_replacement(self, source: str, target: str):
        """Add a replacement rule."""
        self._replacements[source.lower()] = target
        self._save_replacements()

    def remove_replacement(self, source: str):
        """Remove a replacement rule."""
        key = source.lower()
        if key in self._replacements:
            del self._replacements[key]
            self._save_replacements()

    @property
    def replacements(self) -> dict[str, str]:
        return dict(self._replacements)

    def reload(self):
        """Reload replacements from disk."""
        self._load_replacements()
