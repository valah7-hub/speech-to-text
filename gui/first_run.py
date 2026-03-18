"""First run wizard — guides user through initial setup."""

import tkinter as tk
from tkinter import ttk
import threading

from core.gpu_detector import detect_device, get_recommended_model
from core.settings_manager import SettingsManager
from core.audio_recorder import AudioRecorder


# Quality presets: label -> (model, description)
PRESETS = {
    "fast": ("tiny", "Быстрое — менее точное (~75 MB)"),
    "standard": ("base", "Стандартное — хороший баланс (~150 MB)"),
    "good": ("small", "Хорошее — точнее, медленнее (~500 MB)"),
    "high": ("medium", "Высокое — точное, нужен GPU (~1.5 GB)"),
    "max": ("large-v3", "Максимальное — лучшее качество (~3 GB)"),
}


class FirstRunWizard:
    """Step-by-step first-run wizard."""

    def __init__(self, parent: tk.Tk, settings: SettingsManager,
                 on_complete=None):
        self.settings = settings
        self.on_complete = on_complete
        self._step = 0

        self.win = tk.Toplevel(parent)
        self.win.title("Speech-to-Text — Первый запуск")
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.geometry("500x560")
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._skip)

        self.bg = "#2B2B2B"
        self.fg = "#E0E0E0"
        self.win.configure(bg=self.bg)

        # Main container
        self.container = tk.Frame(self.win, bg=self.bg, padx=20, pady=16)
        self.container.pack(fill=tk.BOTH, expand=True)

        self._show_step_1()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # --- Step 1: Quality ---

    def _show_step_1(self):
        self._clear()

        tk.Label(
            self.container,
            text="Welcome! / Добро пожаловать!",
            font=("Segoe UI", 16, "bold"), fg=self.fg, bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 4))

        # UI Language choice
        lang_frame = tk.Frame(self.container, bg=self.bg)
        lang_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(lang_frame, text="Language / Язык:",
                 font=("Segoe UI", 10), fg="#AAAAAA", bg=self.bg
                 ).pack(side=tk.LEFT)
        self.ui_lang_var = tk.StringVar(value="Русский")
        for code, name in [("ru", "Русский"), ("en", "English")]:
            tk.Radiobutton(
                lang_frame, text=name, variable=self.ui_lang_var, value=name,
                font=("Segoe UI", 10), fg=self.fg, bg=self.bg,
                selectcolor="#3C3C3C", activebackground=self.bg,
                activeforeground=self.fg,
            ).pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(
            self.container,
            text="Выберите качество распознавания:",
            font=("Segoe UI", 10), fg="#AAAAAA", bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 8))

        # Device info
        device = detect_device()
        recommended = get_recommended_model(device)
        dev_text = f"Устройство: {device.upper()}"
        if device == "cuda":
            dev_text += f" | Рекомендация: {recommended}"
        tk.Label(
            self.container, text=dev_text,
            font=("Segoe UI", 8), fg="#888888", bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 10))

        # Engine selection
        tk.Label(
            self.container, text="Движок:",
            font=("Segoe UI", 10, "bold"), fg=self.fg, bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 4))

        ENGINES = {
            "faster-whisper": "Faster-Whisper — быстрый, рекомендуется",
            "whisper": "Whisper — оригинальный от OpenAI",
            "whisperx": "WhisperX — точные таймкоды + alignment",
        }
        self.engine_var = tk.StringVar(value="faster-whisper")
        for key, desc in ENGINES.items():
            rb = tk.Radiobutton(
                self.container, text=desc,
                variable=self.engine_var, value=key,
                font=("Segoe UI", 9), fg=self.fg, bg=self.bg,
                selectcolor="#3C3C3C", activebackground=self.bg,
                activeforeground=self.fg,
            )
            rb.pack(anchor=tk.W, pady=1)

        # Separator
        tk.Frame(self.container, height=1, bg="#555555").pack(
            fill=tk.X, pady=8
        )

        # Model selection
        tk.Label(
            self.container, text="Качество (размер модели):",
            font=("Segoe UI", 10, "bold"), fg=self.fg, bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 4))

        self.quality_var = tk.StringVar(value="standard")

        for key, (model, desc) in PRESETS.items():
            suffix = " ★" if model == recommended else ""
            rb = tk.Radiobutton(
                self.container,
                text=f"{desc}{suffix}",
                variable=self.quality_var, value=key,
                font=("Segoe UI", 9), fg=self.fg, bg=self.bg,
                selectcolor="#3C3C3C", activebackground=self.bg,
                activeforeground=self.fg,
            )
            rb.pack(anchor=tk.W, pady=1)

        # Next button
        tk.Button(
            self.container, text="Далее →", font=("Segoe UI", 11),
            bg="#3C6E3C", fg=self.fg, relief=tk.FLAT,
            activebackground="#4A8A4A", cursor="hand2",
            command=self._on_step1_next,
        ).pack(anchor=tk.E, pady=(12, 0))

    def _on_step1_next(self):
        quality = self.quality_var.get()
        model_name = PRESETS[quality][0]
        engine = self.engine_var.get()
        # Save UI language
        lang_name = self.ui_lang_var.get()
        ui_lang = "en" if lang_name == "English" else "ru"
        self.settings.set("ui_language", ui_lang)
        self.settings.set("model", model_name)
        self.settings.set("engine", engine)
        self.settings.save()
        from core.i18n import set_language
        set_language(ui_lang)
        self._show_step_2(model_name)

    # --- Step 2: Download model ---

    def _show_step_2(self, model_name: str):
        self._clear()

        tk.Label(
            self.container,
            text=f"Загрузка модели «{model_name}»...",
            font=("Segoe UI", 14, "bold"), fg=self.fg, bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 8))

        from core.gpu_detector import MODEL_SIZES
        from gui.download_window import MODEL_BYTES, _get_cache_size

        size = MODEL_SIZES.get(model_name, "?")
        tk.Label(
            self.container,
            text=f"Размер: {size}. Скачивание с Hugging Face...",
            font=("Segoe UI", 9), fg="#AAAAAA", bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 12))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            self.container, variable=self.progress_var, maximum=100,
        )
        self.progress.pack(fill=tk.X, pady=(0, 8))

        self.lbl_dl_status = tk.Label(
            self.container, text="0 MB",
            font=("Segoe UI", 9), fg="#888888", bg=self.bg,
        )
        self.lbl_dl_status.pack(anchor=tk.W)

        # Poll download progress
        self._dl_model = model_name
        self._dl_expected = MODEL_BYTES.get(model_name, 100 * 1024 * 1024)
        self._dl_polling = True
        self._dl_tick = 0
        self._poll_download()

        # Load model in background
        self._load_model_bg(model_name)

    def _poll_download(self):
        """Poll cache folder size every 300ms + animate."""
        if not self._dl_polling:
            return
        self._dl_tick += 1
        dots = "." * ((self._dl_tick % 4) + 1)

        from gui.download_window import _get_cache_size
        current = _get_cache_size(self._dl_model)
        mb = current / (1024 * 1024)
        mb_total = self._dl_expected / (1024 * 1024)
        pct = min(95, current / self._dl_expected * 100) if self._dl_expected else 0

        self.progress_var.set(pct)
        self.lbl_dl_status.configure(
            text=f"Скачивание{dots}  {mb:.0f} / {mb_total:.0f} MB  ({pct:.0f}%)")

        self.win.after(300, self._poll_download)

    def _load_model_bg(self, model_name):
        def load():
            try:
                engine = self.settings.get("engine")
                device = detect_device()
                from core.recognizer import load_model
                from core.gpu_detector import get_compute_type
                compute_type = get_compute_type(device)
                load_model(engine, model_name, device, compute_type)
                self.win.after(0, self._on_model_loaded)
            except Exception as e:
                self.win.after(0, self._on_model_error, str(e))

        threading.Thread(target=load, daemon=True).start()

    def _on_model_loaded(self):
        self._dl_polling = False
        self.progress_var.set(100)
        self.lbl_dl_status.configure(text="Модель загружена!", fg="#44FF44")
        self.win.after(500, self._show_step_3)

    def _on_model_error(self, error: str):
        self._dl_polling = False
        self.lbl_dl_status.configure(
            text=f"Ошибка: {error}", fg="#FF6666"
        )
        tk.Button(
            self.container, text="Пропустить →", font=("Segoe UI", 10),
            bg="#5C3030", fg=self.fg, relief=tk.FLAT,
            command=self._show_step_3,
        ).pack(anchor=tk.E, pady=(10, 0))

    # --- Step 3: Mic test ---

    def _show_step_3(self):
        self._clear()

        tk.Label(
            self.container,
            text="Тест микрофона",
            font=("Segoe UI", 14, "bold"), fg=self.fg, bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 8))

        tk.Label(
            self.container,
            text="Нажмите кнопку и скажите что-нибудь:",
            font=("Segoe UI", 10), fg="#AAAAAA", bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 12))

        self.btn_test = tk.Button(
            self.container, text="Удерживайте для теста",
            font=("Segoe UI", 11), bg="#3C3C3C", fg=self.fg,
            relief=tk.FLAT, cursor="hand2",
        )
        self.btn_test.pack(fill=tk.X, pady=(0, 8))
        self.btn_test.bind("<ButtonPress-1>", self._test_start)
        self.btn_test.bind("<ButtonRelease-1>", self._test_stop)

        self.lbl_test_result = tk.Label(
            self.container, text="",
            font=("Segoe UI", 10), fg=self.fg, bg="#1E1E1E",
            wraplength=380, justify=tk.LEFT, padx=6, pady=4,
        )
        self.lbl_test_result.pack(fill=tk.X, pady=(0, 12))

        self._recorder = AudioRecorder()

        # Skip / Done
        btn_frame = tk.Frame(self.container, bg=self.bg)
        btn_frame.pack(fill=tk.X)

        tk.Button(
            btn_frame, text="Готово!", font=("Segoe UI", 11),
            bg="#3C6E3C", fg=self.fg, relief=tk.FLAT,
            activebackground="#4A8A4A", cursor="hand2",
            command=self._finish,
        ).pack(side=tk.RIGHT)

        tk.Button(
            btn_frame, text="Пропустить", font=("Segoe UI", 10),
            bg="#3C3C3C", fg="#888888", relief=tk.FLAT,
            command=self._finish,
        ).pack(side=tk.RIGHT, padx=(0, 8))

    def _test_start(self, event):
        self.btn_test.configure(text="Запись...", bg="#5C2020")
        self._recorder.start()

    def _test_stop(self, event):
        self.btn_test.configure(text="Удерживайте для теста", bg="#3C3C3C")
        audio = self._recorder.stop()
        duration = len(audio) / 16000

        if duration < 0.5:
            self.lbl_test_result.configure(
                text="Слишком короткая запись. Попробуйте ещё раз.",
                fg="#FF6666",
            )
            return

        self.lbl_test_result.configure(text="Распознаю...", fg="#888888")

        def transcribe():
            try:
                engine = self.settings.get("engine")
                model_name = self.settings.get("model")
                device = detect_device()
                from core.recognizer import load_model, create_recognizer
                from core.gpu_detector import get_compute_type
                compute_type = get_compute_type(device)
                model = load_model(engine, model_name, device, compute_type)
                rec = create_recognizer(engine, model)
                text = rec.transcribe(audio, language="ru")
                if text:
                    self.win.after(0, self.lbl_test_result.configure,
                                   {"text": text, "fg": self.fg})
                else:
                    self.win.after(0, self.lbl_test_result.configure,
                                   {"text": "Речь не распознана", "fg": "#FF6666"})
            except Exception as e:
                self.win.after(0, self.lbl_test_result.configure,
                               {"text": f"Ошибка: {e}", "fg": "#FF6666"})

        threading.Thread(target=transcribe, daemon=True).start()

    def _finish(self):
        hotkey = self.settings.get("hotkey")
        self.win.destroy()
        if self.on_complete:
            self.on_complete()

    def _skip(self):
        self.win.destroy()
        if self.on_complete:
            self.on_complete()
