"""Insert text into target window via clipboard + Ctrl+V.

Preserves original clipboard content.
"""

import time
import threading
import pyperclip
import keyboard

from core.window_tracker import WindowTracker


class TextInserter:
    """Pastes text, preserving clipboard."""

    def __init__(self, window_tracker: WindowTracker):
        self.tracker = window_tracker
        self._lock = threading.Lock()
        self._saved_clipboard = ""
        self._clipboard_saved = False

    def save_clipboard(self):
        """Save clipboard before any paste operations."""
        if not self._clipboard_saved:
            try:
                self._saved_clipboard = pyperclip.paste()
            except Exception:
                self._saved_clipboard = ""
            self._clipboard_saved = True

    def restore_clipboard(self):
        """Restore original clipboard after all paste operations done."""
        if self._clipboard_saved:
            try:
                time.sleep(0.1)
                pyperclip.copy(self._saved_clipboard)
            except Exception:
                pass
            self._clipboard_saved = False
            self._saved_clipboard = ""

    def insert(self, text: str) -> bool:
        """Insert text. Saves and restores clipboard."""
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
        """Append only new words. Preserves clipboard across calls."""
        if not new_text:
            return old_text

        if not old_text:
            self._paste(new_text)
            return new_text

        old_words = old_text.split()
        new_words = new_text.split()

        common = 0
        for i in range(min(len(old_words), len(new_words))):
            if old_words[i] == new_words[i]:
                common = i + 1
            else:
                break

        if common >= len(old_words):
            extra = new_words[common:]
            if extra:
                self._paste(" " + " ".join(extra))
        elif common > 0:
            chars_del = len(old_text) - len(" ".join(old_words[:common]))
            if chars_del > 0:
                for _ in range(chars_del):
                    keyboard.press_and_release("backspace")
                time.sleep(0.02)
            suffix = " ".join(new_words[common:])
            if suffix:
                self._paste(" " + suffix)
        else:
            for _ in range(len(old_text)):
                keyboard.press_and_release("backspace")
            time.sleep(0.02)
            self._paste(new_text)

        return new_text

    def _paste(self, text: str):
        """Quick paste. Clipboard NOT restored here — done at end."""
        pyperclip.copy(text)
        time.sleep(0.02)
        keyboard.press_and_release("ctrl+v")
        time.sleep(0.05)
