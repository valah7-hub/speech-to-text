"""Insert text into target window via clipboard + Ctrl+V.

Preserves original clipboard content.
NEVER deletes existing text in the field — only appends.
"""

import time
import threading
import pyperclip
import keyboard

from core.window_tracker import WindowTracker


class TextInserter:
    """Pastes text, preserving clipboard. Never deletes existing content."""

    def __init__(self, window_tracker: WindowTracker):
        self.tracker = window_tracker
        self._lock = threading.Lock()
        self._saved_clipboard = ""
        self._clipboard_saved = False

    def save_clipboard(self):
        if not self._clipboard_saved:
            try:
                self._saved_clipboard = pyperclip.paste()
            except Exception:
                self._saved_clipboard = ""
            self._clipboard_saved = True

    def restore_clipboard(self):
        if self._clipboard_saved:
            try:
                time.sleep(0.1)
                pyperclip.copy(self._saved_clipboard)
            except Exception:
                pass
            self._clipboard_saved = False
            self._saved_clipboard = ""

    def insert(self, text: str) -> bool:
        if not text:
            return False
        if not self._lock.acquire(blocking=False):
            return False
        try:
            self.save_clipboard()
            pyperclip.copy(text)
            time.sleep(0.05)
            target = self.tracker.get_target_window()
            if target:
                self.tracker.activate_target()
            time.sleep(0.1)
            keyboard.press_and_release("ctrl+v")
            time.sleep(0.1)
            self.restore_clipboard()
            return True
        except Exception as e:
            print(f"Insert error: {e}")
            return False
        finally:
            self._lock.release()

    def copy_only(self, text: str):
        pyperclip.copy(text)

    def append_diff(self, old_text: str, new_text: str) -> str:
        """Only APPEND new words. Never send backspace. Never delete."""
        if not new_text:
            return old_text

        # Filter out garbage (dots, ellipsis, single chars)
        clean = new_text.strip().rstrip(".")
        if len(clean) < 2 or clean in ("...", "..", "…"):
            return old_text

        if not old_text:
            self._paste(new_text)
            return new_text

        old_words = old_text.split()
        new_words = new_text.split()

        if len(new_words) <= len(old_words):
            # Text didn't grow — nothing to append, wait for final
            return new_text

        # Find common prefix
        common = 0
        for i in range(min(len(old_words), len(new_words))):
            if old_words[i] == new_words[i]:
                common = i + 1
            else:
                break

        if common >= len(old_words):
            # All old words match — append new ones
            extra = new_words[common:]
        else:
            # Some words changed — just append words beyond old length
            extra = new_words[len(old_words):]

        if extra:
            self._paste(" " + " ".join(extra))

        return new_text

    def _paste(self, text: str):
        pyperclip.copy(text)
        time.sleep(0.02)
        keyboard.press_and_release("ctrl+v")
        time.sleep(0.05)
