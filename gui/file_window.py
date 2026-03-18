"""File transcription window — import files, batch queue, diarization."""

import os
import tkinter as tk
from tkinter import filedialog, ttk
import threading

from core.file_transcriber import FileTranscriber, SUPPORTED_FORMATS


class FileWindow:
    """Window for file-based transcription with batch queue."""

    def __init__(self, parent: tk.Tk, recognizer, text_processor=None,
                 language: str = "ru", initial_prompt: str = None,
                 hf_token: str = ""):
        self.parent = parent
        self.recognizer = recognizer
        self.text_processor = text_processor
        self.language = language
        self.initial_prompt = initial_prompt
        self.hf_token = hf_token

        self._queue: list[str] = []
        self._processing = False
        self._cancel = False

        self.win = tk.Toplevel(parent)
        self.win.title("Транскрибация файлов")
        self.win.attributes("-topmost", True)
        self.win.geometry("520x420")

        self.bg = "#2B2B2B"
        self.fg = "#E0E0E0"
        self.win.configure(bg=self.bg)

        self._create_widgets()

    def _create_widgets(self):
        main = tk.Frame(self.win, bg=self.bg, padx=12, pady=8)
        main.pack(fill=tk.BOTH, expand=True)

        # --- Add files ---
        top = tk.Frame(main, bg=self.bg)
        top.pack(fill=tk.X, pady=(0, 8))

        tk.Button(
            top, text="Добавить файлы", font=("Segoe UI", 10),
            bg="#3C6E3C", fg=self.fg, relief=tk.FLAT,
            activebackground="#4A8A4A", cursor="hand2",
            command=self._add_files,
        ).pack(side=tk.LEFT)

        formats = " ".join(f"*{f}" for f in SUPPORTED_FORMATS)
        tk.Label(
            top, text=f"Форматы: {formats}",
            font=("Segoe UI", 8), fg="#888888", bg=self.bg,
        ).pack(side=tk.LEFT, padx=(10, 0))

        # --- Queue list ---
        list_frame = tk.Frame(main, bg=self.bg)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            list_frame, font=("Segoe UI", 9),
            bg="#1E1E1E", fg=self.fg,
            selectbackground="#3A5FCD",
            activestyle="none",
            yscrollcommand=scrollbar.set,
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # --- Diarization options ---
        diar_frame = tk.Frame(main, bg=self.bg)
        diar_frame.pack(fill=tk.X, pady=(0, 8))

        self.diar_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            diar_frame, text="Определять говорящих",
            variable=self.diar_var,
            font=("Segoe UI", 10), fg=self.fg, bg=self.bg,
            selectcolor="#3C3C3C", activebackground=self.bg,
            activeforeground=self.fg,
        ).pack(side=tk.LEFT)

        tk.Label(
            diar_frame, text="Кол-во:", font=("Segoe UI", 9),
            fg=self.fg, bg=self.bg,
        ).pack(side=tk.LEFT, padx=(16, 4))

        self.speakers_var = tk.StringVar(value="0")
        tk.Spinbox(
            diar_frame, from_=0, to=10, width=4,
            textvariable=self.speakers_var,
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT)

        tk.Label(
            diar_frame, text="(0 = авто)", font=("Segoe UI", 8),
            fg="#888888", bg=self.bg,
        ).pack(side=tk.LEFT, padx=(4, 0))

        # --- Progress ---
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            main, variable=self.progress_var, maximum=100,
        )
        self.progress.pack(fill=tk.X, pady=(0, 4))

        self.lbl_status = tk.Label(
            main, text="Добавьте файлы для обработки",
            font=("Segoe UI", 9), fg="#888888", bg=self.bg, anchor=tk.W,
        )
        self.lbl_status.pack(fill=tk.X, pady=(0, 8))

        # --- Action buttons ---
        btn_frame = tk.Frame(main, bg=self.bg)
        btn_frame.pack(fill=tk.X)

        self.btn_start = tk.Button(
            btn_frame, text="Начать", font=("Segoe UI", 10),
            bg="#3C6E3C", fg=self.fg, relief=tk.FLAT,
            activebackground="#4A8A4A", cursor="hand2",
            command=self._start_processing,
        )
        self.btn_start.pack(side=tk.LEFT)

        self.btn_cancel = tk.Button(
            btn_frame, text="Отмена", font=("Segoe UI", 10),
            bg="#5C3030", fg=self.fg, relief=tk.FLAT,
            activebackground="#7A4040", cursor="hand2",
            command=self._cancel_processing,
            state=tk.DISABLED,
        )
        self.btn_cancel.pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(
            btn_frame, text="Очистить", font=("Segoe UI", 10),
            bg="#3C3C3C", fg=self.fg, relief=tk.FLAT,
            activebackground="#555555", cursor="hand2",
            command=self._clear_queue,
        ).pack(side=tk.RIGHT)

    def _add_files(self):
        filetypes = [
            ("Audio files", " ".join(f"*{f}" for f in SUPPORTED_FORMATS)),
            ("All files", "*.*"),
        ]
        paths = filedialog.askopenfilenames(
            parent=self.win, filetypes=filetypes,
        )
        for p in paths:
            if p not in self._queue:
                self._queue.append(p)
                name = os.path.basename(p)
                self.listbox.insert(tk.END, f"⏳ {name}")

    def _clear_queue(self):
        self._queue.clear()
        self.listbox.delete(0, tk.END)
        self.progress_var.set(0)
        self.lbl_status.configure(text="Очередь пуста")

    def _start_processing(self):
        if not self._queue or self._processing:
            return
        self._processing = True
        self._cancel = False
        self.btn_start.configure(state=tk.DISABLED)
        self.btn_cancel.configure(state=tk.NORMAL)
        threading.Thread(target=self._process_queue, daemon=True).start()

    def _cancel_processing(self):
        self._cancel = True

    def _process_queue(self):
        """Process all files in queue sequentially."""
        total = len(self._queue)
        transcriber = FileTranscriber(
            self.recognizer, self.text_processor,
            self.language, self.initial_prompt,
        )

        use_diar = self.diar_var.get()
        num_speakers = int(self.speakers_var.get())

        for i, path in enumerate(self._queue):
            if self._cancel:
                self._update_status(f"Отменено ({i}/{total})")
                break

            name = os.path.basename(path)
            self._update_listbox(i, f"▶ {name}")

            def on_progress(pct, msg):
                overall = (i / total + pct / 100 / total) * 100
                self._update_progress(overall, f"[{i+1}/{total}] {name}: {msg}")

            try:
                segments = transcriber.transcribe_file(path, on_progress)

                # Diarization
                if use_diar and segments:
                    from core.diarization import Diarizer
                    diarizer = Diarizer(self.hf_token)
                    if diarizer.is_available and self.hf_token:
                        segments = diarizer.diarize(
                            path, segments, num_speakers, on_progress
                        )

                self._update_listbox(i, f"✅ {name}")

                # Show results
                self.win.after(0, self._show_results, segments, name)

            except Exception as e:
                self._update_listbox(i, f"❌ {name}: {e}")

        self._update_progress(100, "Обработка завершена")
        self.win.after(0, self._processing_done)

    def _processing_done(self):
        self._processing = False
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_cancel.configure(state=tk.DISABLED)

    def _update_progress(self, pct, msg):
        self.win.after(0, self.progress_var.set, pct)
        self.win.after(0, self.lbl_status.configure, {"text": msg})

    def _update_status(self, msg):
        self.win.after(0, self.lbl_status.configure, {"text": msg})

    def _update_listbox(self, idx, text):
        def update():
            self.listbox.delete(idx)
            self.listbox.insert(idx, text)
        self.win.after(0, update)

    def _show_results(self, segments, source_file):
        from gui.transcript_window import TranscriptWindow
        TranscriptWindow(self.win, segments, source_file)
