"""History of transcriptions — stores last N entries with metadata."""

import json
import os
from datetime import datetime


class HistoryEntry:
    __slots__ = ("text", "timestamp", "engine", "duration", "elapsed")

    def __init__(self, text: str, timestamp: str = None, engine: str = "",
                 duration: float = 0, elapsed: float = 0):
        self.text = text
        self.timestamp = timestamp or datetime.now().isoformat(timespec="seconds")
        self.engine = engine
        self.duration = duration    # recording duration in sec
        self.elapsed = elapsed      # processing time in sec

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "timestamp": self.timestamp,
            "engine": self.engine,
            "duration": round(self.duration, 1),
            "elapsed": round(self.elapsed, 1),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEntry":
        return cls(
            text=d["text"],
            timestamp=d.get("timestamp", ""),
            engine=d.get("engine", ""),
            duration=d.get("duration", 0),
            elapsed=d.get("elapsed", 0),
        )


class HistoryManager:
    """Manages a list of transcription history entries."""

    def __init__(self, max_items: int = 20, path: str = None):
        self.max_items = max_items
        if path is None:
            path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "history.json"
            )
        self.path = path
        self._entries: list[HistoryEntry] = []
        self._load()

    def add(self, text: str, engine: str = "", duration: float = 0,
            elapsed: float = 0):
        """Add a new entry. Auto-removes oldest if over limit."""
        entry = HistoryEntry(
            text=text, engine=engine, duration=duration, elapsed=elapsed
        )
        self._entries.insert(0, entry)  # newest first
        if len(self._entries) > self.max_items:
            self._entries = self._entries[: self.max_items]
        self._save()

    def get_all(self) -> list[HistoryEntry]:
        """Get all entries, newest first."""
        return list(self._entries)

    def clear(self):
        """Clear all history."""
        self._entries.clear()
        self._save()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = [HistoryEntry.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError):
                self._entries = []
        else:
            self._entries = []

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                [e.to_dict() for e in self._entries],
                f, indent=2, ensure_ascii=False,
            )

    def __len__(self) -> int:
        return len(self._entries)
