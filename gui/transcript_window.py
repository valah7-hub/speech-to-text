"""Transcript results window — display, copy, export."""

import tkinter as tk
from tkinter import filedialog

import pyperclip

from core.file_transcriber import (
    Segment, format_segments_plain, format_segments_srt, format_segments_vtt,
)


class TranscriptWindow:
    """Shows transcription results with export options."""

    def __init__(self, parent: tk.Tk, segments: list[Segment],
                 source_file: str = ""):
        self.segments = segments
        self.source_file = source_file

        self.win = tk.Toplevel(parent)
        self.win.title(f"Результат — {source_file}" if source_file else "Результат")
        self.win.attributes("-topmost", True)
        self.win.geometry("600x450")

        self.bg = "#2B2B2B"
        self.fg = "#E0E0E0"
        self.win.configure(bg=self.bg)

        self._create_widgets()

    def _create_widgets(self):
        # Text area with scrollbar
        text_frame = tk.Frame(self.win, bg=self.bg)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area = tk.Text(
            text_frame,
            font=("Consolas", 10),
            bg="#1E1E1E", fg=self.fg,
            insertbackground=self.fg,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_area.yview)

        # Fill with formatted text
        plain = format_segments_plain(self.segments)
        self.text_area.insert(tk.END, plain)

        # Bottom buttons
        btn_frame = tk.Frame(self.win, bg=self.bg)
        btn_frame.pack(fill=tk.X, padx=8, pady=(4, 8))

        buttons = [
            ("Копировать", self._copy_all),
            ("Экспорт .txt", lambda: self._export("txt")),
            ("Экспорт .srt", lambda: self._export("srt")),
            ("Экспорт .vtt", lambda: self._export("vtt")),
        ]

        for label, cmd in buttons:
            tk.Button(
                btn_frame, text=label, font=("Segoe UI", 9),
                bg="#3C3C3C", fg=self.fg, relief=tk.FLAT,
                activebackground="#555555", cursor="hand2",
                command=cmd,
            ).pack(side=tk.LEFT, padx=(0, 6))

        # Segment count
        tk.Label(
            btn_frame,
            text=f"{len(self.segments)} сегментов",
            font=("Segoe UI", 8), fg="#888888", bg=self.bg,
        ).pack(side=tk.RIGHT)

    def _copy_all(self):
        plain = format_segments_plain(self.segments)
        pyperclip.copy(plain)

    def _export(self, fmt: str):
        filetypes = {
            "txt": ("Text files", "*.txt"),
            "srt": ("SubRip subtitles", "*.srt"),
            "vtt": ("WebVTT subtitles", "*.vtt"),
        }

        ft = filetypes.get(fmt, ("All files", "*.*"))
        path = filedialog.asksaveasfilename(
            parent=self.win,
            defaultextension=f".{fmt}",
            filetypes=[ft],
        )
        if not path:
            return

        if fmt == "srt":
            content = format_segments_srt(self.segments)
        elif fmt == "vtt":
            content = format_segments_vtt(self.segments)
        else:
            content = format_segments_plain(self.segments)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
