"""Model management window — view downloaded models, delete to free space."""

import os
import shutil
import tkinter as tk
from tkinter import messagebox

from core.gpu_detector import get_downloaded_models, MODEL_SIZES


CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")


class ModelsWindow:
    """Shows downloaded models with sizes and delete buttons."""

    def __init__(self, parent: tk.Tk):
        self.win = tk.Toplevel(parent)
        self.win.title("Управление моделями")
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.geometry("400x340")

        self.bg = "#2B2B2B"
        self.fg = "#E0E0E0"
        self.win.configure(bg=self.bg)

        main = tk.Frame(self.win, bg=self.bg, padx=16, pady=12)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(main, text="Скачанные модели",
                 font=("Segoe UI", 12, "bold"), fg=self.fg, bg=self.bg
                 ).pack(anchor=tk.W, pady=(0, 4))

        tk.Label(main,
                 text="Каждая модель независима — base не включает tiny",
                 font=("Segoe UI", 8), fg="#888888", bg=self.bg
                 ).pack(anchor=tk.W, pady=(0, 10))

        # Model list
        self.list_frame = tk.Frame(main, bg=self.bg)
        self.list_frame.pack(fill=tk.BOTH, expand=True)

        self._refresh()

        # Total size
        self.lbl_total = tk.Label(main, text="", font=("Segoe UI", 9),
                                   fg="#AAAAAA", bg=self.bg)
        self.lbl_total.pack(anchor=tk.W, pady=(8, 0))
        self._update_total()

    def _refresh(self):
        """Rebuild the model list."""
        for w in self.list_frame.winfo_children():
            w.destroy()

        downloaded = get_downloaded_models()

        for name in MODEL_SIZES:
            size_mb = downloaded.get(name, 0)
            expected = MODEL_SIZES[name]

            row = tk.Frame(self.list_frame, bg=self.bg)
            row.pack(fill=tk.X, pady=2)

            if size_mb > 0:
                # Downloaded
                tk.Label(row, text=f"✓  {name}", font=("Segoe UI", 10),
                         fg="#66CC66", bg=self.bg, width=14, anchor=tk.W
                         ).pack(side=tk.LEFT)
                tk.Label(row, text=f"{size_mb} MB",
                         font=("Segoe UI", 9), fg="#AAAAAA", bg=self.bg,
                         width=8).pack(side=tk.LEFT)
                tk.Button(row, text="Удалить", font=("Segoe UI", 8),
                          bg="#5C3030", fg=self.fg, relief=tk.FLAT,
                          cursor="hand2",
                          command=lambda n=name: self._delete(n)
                          ).pack(side=tk.RIGHT)
            else:
                # Not downloaded
                tk.Label(row, text=f"✗  {name}", font=("Segoe UI", 10),
                         fg="#888888", bg=self.bg, width=14, anchor=tk.W
                         ).pack(side=tk.LEFT)
                tk.Label(row, text=f"({expected})",
                         font=("Segoe UI", 9), fg="#666666", bg=self.bg
                         ).pack(side=tk.LEFT)

    def _delete(self, model_name: str):
        ok = messagebox.askyesno(
            "Удалить модель",
            f"Удалить модель «{model_name}»?\n"
            f"Можно будет скачать заново.",
            parent=self.win,
        )
        if not ok:
            return

        dir_name = f"models--Systran--faster-whisper-{model_name}"
        path = os.path.join(CACHE_DIR, dir_name)
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"Deleted model: {model_name}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить: {e}",
                                 parent=self.win)
            return

        self._refresh()
        self._update_total()

    def _update_total(self):
        downloaded = get_downloaded_models()
        total = sum(downloaded.values())
        self.lbl_total.configure(
            text=f"Всего занято: {total} MB"
        )
