"""Download progress window — polls actual file size on disk."""

import os
import tkinter as tk
from tkinter import ttk

from core.gpu_detector import MODEL_SIZES


# Expected download sizes in bytes (approximate)
MODEL_BYTES = {
    "tiny": 75 * 1024 * 1024,
    "base": 150 * 1024 * 1024,
    "small": 500 * 1024 * 1024,
    "medium": 1500 * 1024 * 1024,
    "large-v3": 3000 * 1024 * 1024,
}


def _get_cache_size(model_name: str) -> int:
    """Get current download size in bytes by checking cache folder."""
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    dir_name = f"models--Systran--faster-whisper-{model_name}"
    path = os.path.join(cache_dir, dir_name)
    if not os.path.exists(path):
        return 0
    total = 0
    for dp, dn, fns in os.walk(path):
        for f in fns:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total


class DownloadWindow:
    """Shows real download progress by polling cache folder size."""

    def __init__(self, parent: tk.Tk, model_name: str):
        self.model_name = model_name
        self.expected = MODEL_BYTES.get(model_name, 100 * 1024 * 1024)

        self.win = tk.Toplevel(parent)
        self.win.title("Загрузка модели")
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.geometry("430x160")
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)

        bg = "#2B2B2B"
        fg = "#E0E0E0"
        self.win.configure(bg=bg)

        main = tk.Frame(self.win, bg=bg, padx=20, pady=14)
        main.pack(fill=tk.BOTH, expand=True)

        size = MODEL_SIZES.get(model_name, "?")
        tk.Label(main, text=f"Загрузка модели «{model_name}» ({size})",
                 font=("Segoe UI", 12, "bold"), fg=fg, bg=bg
                 ).pack(anchor=tk.W, pady=(0, 8))

        self.lbl_status = tk.Label(
            main, text="Скачивание...",
            font=("Segoe UI", 9), fg="#AAAAAA", bg=bg)
        self.lbl_status.pack(anchor=tk.W, pady=(0, 6))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            main, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 6))

        self.lbl_detail = tk.Label(
            main, text="0 MB / {:.0f} MB".format(self.expected / 1024 / 1024),
            font=("Segoe UI", 8), fg="#888888", bg=bg)
        self.lbl_detail.pack(anchor=tk.W)

        self._polling = True
        self._tick = 0
        self._poll()

    def _poll(self):
        """Check cache folder size every 300ms + animate dots."""
        if not self._polling:
            return
        self._tick += 1
        dots = "." * ((self._tick % 4) + 1)

        try:
            current = _get_cache_size(self.model_name)
            mb_done = current / (1024 * 1024)
            mb_total = self.expected / (1024 * 1024)
            pct = min(95, current / self.expected * 100) if self.expected > 0 else 0

            self.progress_var.set(pct)
            self.lbl_detail.configure(
                text=f"{mb_done:.0f} / {mb_total:.0f} MB  ({pct:.0f}%)")
            self.lbl_status.configure(
                text=f"Скачивание{dots}")
        except Exception:
            pass

        self.win.after(300, self._poll)

    def set_status(self, text: str):
        self.win.after(0, self.lbl_status.configure, {"text": text})

    def set_progress(self, percent: float, detail: str = ""):
        self.win.after(0, self.progress_var.set, min(100, percent))
        if detail:
            self.win.after(0, self.lbl_detail.configure, {"text": detail})

    def set_error(self, text: str):
        self._polling = False
        self.win.after(0, self.lbl_status.configure,
                       {"text": text, "fg": "#FF6666"})
        self.win.after(0, self.lbl_detail.configure,
                       {"text": "Закройте это окно"})
        self.win.after(0, self._make_closable)

    def close(self):
        self._polling = False
        try:
            self.win.after(0, self.win.destroy)
        except Exception:
            pass

    def _make_closable(self):
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)
