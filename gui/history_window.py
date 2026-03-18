"""History window — list of past transcriptions with copy/paste."""

import tkinter as tk
from tkinter import ttk

import pyperclip

from core.history_manager import HistoryManager


class HistoryWindow:
    """Shows transcription history in a scrollable list."""

    def __init__(self, parent: tk.Tk, history: HistoryManager,
                 on_insert=None):
        """
        Args:
            parent: parent tk window
            history: HistoryManager instance
            on_insert: callback(text) to insert text into active window
        """
        self.history = history
        self.on_insert = on_insert

        self.win = tk.Toplevel(parent)
        self.win.title("История распознаваний")
        self.win.attributes("-topmost", True)
        self.win.geometry("500x400")

        # Theme
        self.bg = "#2B2B2B"
        self.fg = "#E0E0E0"
        self.win.configure(bg=self.bg)

        self._create_widgets()
        self._populate()

    def _create_widgets(self):
        # Top bar
        top = tk.Frame(self.win, bg=self.bg)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))

        tk.Label(top, text=f"Записей: {len(self.history)}",
                 font=("Segoe UI", 9), fg="#888888", bg=self.bg
                 ).pack(side=tk.LEFT)

        tk.Button(
            top, text="Очистить", font=("Segoe UI", 9),
            bg="#5C3030", fg=self.fg, relief=tk.FLAT,
            activebackground="#7A4040", cursor="hand2",
            command=self._clear_history,
        ).pack(side=tk.RIGHT)

        # Listbox with scrollbar
        list_frame = tk.Frame(self.win, bg=self.bg)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            list_frame,
            font=("Segoe UI", 10),
            bg="#1E1E1E", fg=self.fg,
            selectbackground="#3A5FCD",
            selectforeground="#FFFFFF",
            activestyle="none",
            yscrollcommand=scrollbar.set,
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Bindings
        self.listbox.bind("<ButtonRelease-1>", self._on_click)
        self.listbox.bind("<Double-ButtonRelease-1>", self._on_double_click)

        # Bottom hint
        hint = tk.Label(
            self.win,
            text="Клик — скопировать  |  Двойной клик — вставить",
            font=("Segoe UI", 8), fg="#666666", bg=self.bg,
        )
        hint.pack(pady=(0, 6))

    def _populate(self):
        """Fill listbox with history entries."""
        self.listbox.delete(0, tk.END)
        for entry in self.history.get_all():
            ts = entry.timestamp[11:19] if len(entry.timestamp) > 10 else ""
            preview = entry.text[:80].replace("\n", " ")
            if len(entry.text) > 80:
                preview += "..."
            line = f"[{ts}]  {preview}"
            if entry.elapsed > 0:
                line += f"  ({entry.elapsed:.1f}s)"
            self.listbox.insert(tk.END, line)

    def _on_click(self, event):
        """Copy selected entry to clipboard."""
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        entries = self.history.get_all()
        if idx < len(entries):
            pyperclip.copy(entries[idx].text)

    def _on_double_click(self, event):
        """Insert selected entry into active window."""
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        entries = self.history.get_all()
        if idx < len(entries) and self.on_insert:
            self.on_insert(entries[idx].text)

    def _clear_history(self):
        self.history.clear()
        self._populate()
