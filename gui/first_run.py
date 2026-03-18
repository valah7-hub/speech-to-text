"""First run wizard — guides user through initial setup."""

import tkinter as tk
from tkinter import ttk
import threading
import os
import sys

from core.gpu_detector import detect_device, get_recommended_model, get_installed_engines
from core.settings_manager import SettingsManager
from core.audio_recorder import AudioRecorder
from core.i18n import t, set_language


# Quality presets: key -> (model, size_mb)
PRESETS = [
    ("tiny", 75),
    ("base", 150),
    ("small", 500),
    ("medium", 1500),
    ("large-v3", 3000),
]


def _get_models_dir():
    """Models stored next to exe / app.py, not in ~/.cache."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "models")


class FirstRunWizard:
    """Step-by-step first-run wizard."""

    def __init__(self, parent: tk.Tk, settings: SettingsManager,
                 on_complete=None):
        self.settings = settings
        self.on_complete = on_complete
        self._lang = settings.get("ui_language") or "ru"

        self.win = tk.Toplevel(parent)
        self.win.title("Speech-to-Text")
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.geometry("520x620")
        self.win.protocol("WM_DELETE_WINDOW", self._skip)

        self.bg = "#2B2B2B"
        self.fg = "#E0E0E0"
        self.win.configure(bg=self.bg)

        self.container = tk.Frame(self.win, bg=self.bg, padx=20, pady=16)
        self.container.pack(fill=tk.BOTH, expand=True)

        self._show_step_1()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ---- Step 1: Language + Engine + Model ----

    def _show_step_1(self):
        self._clear()

        # Title
        tk.Label(
            self.container,
            text="Welcome! / Добро пожаловать!",
            font=("Segoe UI", 15, "bold"), fg=self.fg, bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 8))

        # Language selector
        lang_frame = tk.Frame(self.container, bg=self.bg)
        lang_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(lang_frame, text="Language / Язык:",
                 font=("Segoe UI", 10), fg="#AAAAAA", bg=self.bg
                 ).pack(side=tk.LEFT)

        self.ui_lang_var = tk.StringVar(value=self._lang)
        for code, name in [("ru", "Русский"), ("en", "English")]:
            tk.Radiobutton(
                lang_frame, text=name, variable=self.ui_lang_var, value=code,
                font=("Segoe UI", 10), fg=self.fg, bg=self.bg,
                selectcolor="#3C3C3C", activebackground=self.bg,
                activeforeground=self.fg,
                command=self._on_lang_change,
            ).pack(side=tk.LEFT, padx=(8, 0))

        # Separator
        tk.Frame(self.container, height=1, bg="#555555").pack(fill=tk.X, pady=4)

        # Engine — only installed ones
        self._lbl_engine = tk.Label(
            self.container, text=self._t_engine_title(),
            font=("Segoe UI", 10, "bold"), fg=self.fg, bg=self.bg,
        )
        self._lbl_engine.pack(anchor=tk.W, pady=(4, 4))

        # Show engines — both always available
        ENGINE_LIST = [
            ("faster-whisper",
             "Faster-Whisper — " + ("fast, recommended" if self._lang == "en" else "быстрый, рекомендуется")),
            ("whisper",
             "Whisper — " + ("original by OpenAI" if self._lang == "en" else "оригинальный от OpenAI")),
        ]
        self.engine_var = tk.StringVar(value="faster-whisper")
        for key, label in ENGINE_LIST:
            tk.Radiobutton(
                self.container, text=label,
                variable=self.engine_var, value=key,
                font=("Segoe UI", 9), fg=self.fg, bg=self.bg,
                selectcolor="#3C3C3C", activebackground=self.bg,
                activeforeground=self.fg,
            ).pack(anchor=tk.W, pady=1)

        # Separator
        tk.Frame(self.container, height=1, bg="#555555").pack(fill=tk.X, pady=6)

        # Model selection
        device = detect_device()
        recommended = get_recommended_model(device)

        self._lbl_quality = tk.Label(
            self.container, text=self._t_quality_title(),
            font=("Segoe UI", 10, "bold"), fg=self.fg, bg=self.bg,
        )
        self._lbl_quality.pack(anchor=tk.W, pady=(0, 4))

        # Device info
        dev_text = f"{'Device' if self._lang == 'en' else 'Устройство'}: {device.upper()}"
        if device == "cuda":
            dev_text += f" | {'Recommended' if self._lang == 'en' else 'Рекомендация'}: {recommended}"
        tk.Label(
            self.container, text=dev_text,
            font=("Segoe UI", 8), fg="#888888", bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 6))

        # Hint about model quality
        hint = ("Larger model = better quality, but slower and more disk space"
                if self._lang == "en"
                else "Чем больше модель — тем лучше качество, но медленнее и больше места на диске")
        tk.Label(
            self.container, text=hint,
            font=("Segoe UI", 8), fg="#999999", bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 4))

        self.quality_var = tk.StringVar(value=recommended)
        for model, size_mb in PRESETS:
            star = " ★" if model == recommended else ""
            label = f"{model}  (~{size_mb} MB){star}"
            tk.Radiobutton(
                self.container, text=label,
                variable=self.quality_var, value=model,
                font=("Segoe UI", 9), fg=self.fg, bg=self.bg,
                selectcolor="#3C3C3C", activebackground=self.bg,
                activeforeground=self.fg,
            ).pack(anchor=tk.W, pady=1)

        # Next button — full width, clearly visible
        self._btn_next = tk.Button(
            self.container,
            text="Next →" if self._lang == "en" else "Далее →",
            font=("Segoe UI", 13, "bold"),
            bg="#3C6E3C", fg="white", relief=tk.FLAT,
            activebackground="#4A8A4A", cursor="hand2",
            pady=8,
            command=self._on_step1_next,
        )
        self._btn_next.pack(fill=tk.X, pady=(14, 0))

    def _t_engine_title(self):
        return "Engine:" if self._lang == "en" else "Движок:"

    def _t_quality_title(self):
        return "Model quality (size):" if self._lang == "en" else "Качество (размер модели):"

    def _on_lang_change(self):
        """Rebuild step 1 with new language."""
        self._lang = self.ui_lang_var.get()
        set_language(self._lang)
        self.settings.set("ui_language", self._lang)
        self.settings.save()
        self._show_step_1()

    def _on_step1_next(self):
        model_name = self.quality_var.get()
        engine = self.engine_var.get()
        self.settings.set("model", model_name)
        self.settings.set("engine", engine)
        self.settings.set("ui_language", self._lang)
        self.settings.save()
        self._show_step_2(model_name)

    # ---- Step 2: Download model ----

    def _show_step_2(self, model_name: str):
        self._clear()

        title = f"Downloading model «{model_name}»..." if self._lang == "en" \
            else f"Загрузка модели «{model_name}»..."
        tk.Label(
            self.container, text=title,
            font=("Segoe UI", 14, "bold"), fg=self.fg, bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 8))

        from core.gpu_detector import MODEL_SIZES
        from gui.download_window import MODEL_BYTES, _get_cache_size

        size = MODEL_SIZES.get(model_name, "?")
        info = f"{'Size' if self._lang == 'en' else 'Размер'}: {size}"
        tk.Label(
            self.container, text=info,
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

        self._dl_model = model_name
        self._dl_expected = MODEL_BYTES.get(model_name, 100 * 1024 * 1024)
        self._dl_polling = True
        self._dl_tick = 0
        self._poll_download()
        self._load_model_bg(model_name)

    def _poll_download(self):
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
        dl_word = "Downloading" if self._lang == "en" else "Скачивание"
        self.lbl_dl_status.configure(
            text=f"{dl_word}{dots}  {mb:.0f} / {mb_total:.0f} MB  ({pct:.0f}%)")

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
        done = "Model loaded!" if self._lang == "en" else "Модель загружена!"
        self.lbl_dl_status.configure(text=done, fg="#44FF44")

        # Show "Next" button — full width
        next_text = "Далее →" if self._lang != "en" else "Next →"
        tk.Button(
            self.container, text=next_text, font=("Segoe UI", 13, "bold"),
            bg="#3C6E3C", fg="white", relief=tk.FLAT,
            activebackground="#4A8A4A", cursor="hand2",
            pady=8,
            command=self._show_step_3,
        ).pack(fill=tk.X, pady=(14, 0))

    def _on_model_error(self, error: str):
        self._dl_polling = False
        err_text = f"Error: {error}" if self._lang == "en" else f"Ошибка: {error}"
        self.lbl_dl_status.configure(text=err_text, fg="#FF6666")

        skip_text = "Skip →" if self._lang == "en" else "Пропустить →"
        tk.Button(
            self.container, text=skip_text, font=("Segoe UI", 10),
            bg="#5C3030", fg=self.fg, relief=tk.FLAT,
            command=self._show_step_3,
        ).pack(anchor=tk.E, pady=(10, 0))

    # ---- Step 3: Mic test ----

    def _show_step_3(self):
        self._clear()

        title = "Microphone test" if self._lang == "en" else "Тест микрофона"
        tk.Label(
            self.container, text=title,
            font=("Segoe UI", 14, "bold"), fg=self.fg, bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 8))

        hint = "Press and hold the button, say something:" if self._lang == "en" \
            else "Нажмите кнопку и скажите что-нибудь:"
        tk.Label(
            self.container, text=hint,
            font=("Segoe UI", 10), fg="#AAAAAA", bg=self.bg,
        ).pack(anchor=tk.W, pady=(0, 12))

        btn_text = "Hold to test" if self._lang == "en" else "Удерживайте для теста"
        self.btn_test = tk.Button(
            self.container, text=btn_text,
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
        self._testing = False
        self._model_cache = None

        # Buttons
        btn_frame = tk.Frame(self.container, bg=self.bg)
        btn_frame.pack(fill=tk.X)

        done_text = "Done!" if self._lang == "en" else "Готово!"
        tk.Button(
            btn_frame, text=done_text, font=("Segoe UI", 11),
            bg="#3C6E3C", fg=self.fg, relief=tk.FLAT,
            activebackground="#4A8A4A", cursor="hand2",
            command=self._finish,
        ).pack(side=tk.RIGHT)

        skip_text = "Skip" if self._lang == "en" else "Пропустить"
        tk.Button(
            btn_frame, text=skip_text, font=("Segoe UI", 10),
            bg="#3C3C3C", fg="#888888", relief=tk.FLAT,
            command=self._finish,
        ).pack(side=tk.RIGHT, padx=(0, 8))

    def _test_start(self, event):
        if self._testing:
            return  # Already recording/transcribing
        self._testing = True
        rec_text = "Recording..." if self._lang == "en" else "Запись..."
        self.btn_test.configure(text=rec_text, bg="#5C2020")
        try:
            self._recorder = AudioRecorder()  # Fresh recorder each time
            self._recorder.start()
        except Exception as e:
            self._testing = False
            self.lbl_test_result.configure(
                text=f"Mic error: {e}", fg="#FF6666")
            self.btn_test.configure(
                text="Hold to test" if self._lang == "en" else "Удерживайте для теста",
                bg="#3C3C3C")

    def _test_stop(self, event):
        if not self._testing:
            return
        btn_text = "Hold to test" if self._lang == "en" else "Удерживайте для теста"
        self.btn_test.configure(text=btn_text, bg="#3C3C3C")

        try:
            audio = self._recorder.stop()
        except Exception:
            self._testing = False
            return

        duration = len(audio) / 16000
        if duration < 0.5:
            msg = "Too short. Try again." if self._lang == "en" \
                else "Слишком короткая запись. Попробуйте ещё раз."
            self.lbl_test_result.configure(text=msg, fg="#FF6666")
            self._testing = False
            return

        proc_text = "Recognizing..." if self._lang == "en" else "Распознаю..."
        self.lbl_test_result.configure(text=proc_text, fg="#888888")

        def transcribe():
            try:
                engine = self.settings.get("engine")
                model_name = self.settings.get("model")
                device = detect_device()
                from core.recognizer import load_model, create_recognizer
                from core.gpu_detector import get_compute_type
                compute_type = get_compute_type(device)

                # Cache model to avoid reloading each test
                if self._model_cache is None:
                    self._model_cache = (
                        load_model(engine, model_name, device, compute_type),
                        engine
                    )
                model_obj, eng = self._model_cache
                rec = create_recognizer(eng, model_obj, device)
                text = rec.transcribe(audio, language="ru")
                if text:
                    self.win.after(0, self.lbl_test_result.configure,
                                   {"text": text, "fg": self.fg})
                else:
                    msg = "No speech detected" if self._lang == "en" \
                        else "Речь не распознана"
                    self.win.after(0, self.lbl_test_result.configure,
                                   {"text": msg, "fg": "#FF6666"})
            except Exception as e:
                err = str(e)
                # Friendly message for missing torch
                if "torch" in err.lower() or "No module named" in err:
                    err = ("Engine requires PyTorch. Use faster-whisper instead."
                           if self._lang == "en"
                           else "Движок требует PyTorch. Используйте faster-whisper.")
                self.win.after(0, self.lbl_test_result.configure,
                               {"text": err, "fg": "#FF6666"})
            finally:
                self._testing = False

        threading.Thread(target=transcribe, daemon=True).start()

    def _finish(self):
        self.win.destroy()
        if self.on_complete:
            self.on_complete()

    def _skip(self):
        self.win.destroy()
        if self.on_complete:
            self.on_complete()
