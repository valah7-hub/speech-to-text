"""Settings — compact, single panel, no scroll, native widgets."""

import os
import shutil
import tkinter as tk
from tkinter import ttk

from core.settings_manager import SettingsManager, VALID_VALUES
from core.gpu_detector import (
    detect_device, get_recommended_model,
    get_downloaded_models, format_model_label, MODEL_SIZES,
    get_installed_engines, format_engine_label,
)
from gui.tooltip import Tooltip

BG = "#1E1E1E"
FG = "#E0E0E0"
FG2 = "#888888"
FIELD = "#2E2E2E"
ACCENT = "#5599DD"
GREEN = "#55BB55"
ROW_BG = "#252525"

TIPS = {
    "engine": "Движок распознавания речи.\nfaster-whisper — самый быстрый.",
    "model": "Больше модель = точнее, но медленнее.\n★ — рекомендуется.",
    "language": "ru — русский + англ. термины латиницей.\nauto — автоопределение.",
    "device": "GPU ускоряет распознавание в 5-10 раз.\nТребуется NVIDIA + CUDA.",
    "hotkey": "Зажмите — запись. Отпустите — распознавание.\nМожно назначить кнопку мыши.",
    "mic": "Микрофон для записи голоса.",
    "filler": "Убирает «ну», «вот», «типа», «как бы».",
    "voice_cmd": "«Точка», «запятая» → знаки препинания.",
    "vad": "Автоматически слушает и записывает\nкогда вы начинаете говорить.",
    "autostart": "Запускать приложение автоматически\nпри включении Windows.",
}


class SettingsWindow:
    def __init__(self, parent, settings: SettingsManager,
                 on_save=None, history_manager=None):
        self.settings = settings
        self.on_save = on_save
        self.history_manager = history_manager

        self.win = tk.Toplevel(parent)
        self.win.title("Настройки")
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.configure(bg=BG)

        m = tk.Frame(self.win, bg=BG, padx=14, pady=10)
        m.pack(fill=tk.BOTH, expand=True)

        device = detect_device()
        recommended = get_recommended_model(device)
        downloaded = get_downloaded_models()
        installed = get_installed_engines()

        # Header + GPU
        hdr = tk.Frame(m, bg=BG)
        hdr.pack(fill=tk.X, pady=(0, 8))
        tk.Label(hdr, text="Настройки", font=("Segoe UI Semibold", 13),
                 fg=FG, bg=BG).pack(side=tk.LEFT)
        gpu_text = "GPU ✓" if device == "cuda" else "CPU"
        gpu_color = GREEN if device == "cuda" else "#AA8833"
        tk.Label(hdr, text=gpu_text, font=("Segoe UI", 9),
                 fg=gpu_color, bg=BG).pack(side=tk.RIGHT)

        # --- Rows ---

        # Engine
        self._engine_values = [e for e in VALID_VALUES["engine"] if installed.get(e)]
        self._engine_labels = [format_engine_label(e, installed) for e in self._engine_values]
        cur_eng = self.settings.get("engine")
        if cur_eng not in self._engine_values and self._engine_values:
            cur_eng = self._engine_values[0]
        self.engine_var = self._row_select(
            m, "Движок", self._engine_labels,
            format_engine_label(cur_eng, installed), "engine")

        # GPU toggle
        cuda_ok = device == "cuda"
        self.gpu_var = tk.BooleanVar(
            value=cuda_ok and self.settings.get("device") != "cpu")
        self._row_check(m, "Использовать GPU", self.gpu_var,
                        "device", enabled=cuda_ok,
                        note="" if cuda_ok else "(CUDA недоступна)")

        # Model
        self._model_values = list(VALID_VALUES["model"])
        self._model_labels = [format_model_label(n, downloaded, recommended)
                              for n in self._model_values]
        cur_mod = self.settings.get("model")
        self.model_var = self._row_select(
            m, "Модель", self._model_labels,
            format_model_label(cur_mod, downloaded, recommended), "model")

        # Downloaded models
        self._mf = tk.Frame(m, bg=BG)
        self._mf.pack(fill=tk.X, pady=(0, 2))
        self._build_dl(downloaded)

        # Language
        self.language_var = self._row_select(
            m, "Язык", list(VALID_VALUES["language"]),
            self.settings.get("language"), "language")

        # Hotkey
        hk = tk.Frame(m, bg=ROW_BG, padx=8, pady=5)
        hk.pack(fill=tk.X, pady=2)
        tk.Label(hk, text="Хоткей", font=("Segoe UI", 10),
                 fg=FG, bg=ROW_BG).pack(side=tk.LEFT)
        self._tip(hk, "hotkey")
        self.hotkey_var = tk.StringVar(value=self.settings.get("hotkey"))
        self.lbl_hk = tk.Label(hk, textvariable=self.hotkey_var,
                                font=("Segoe UI", 10, "bold"), fg=ACCENT,
                                bg=FIELD, padx=6, pady=1)
        self.lbl_hk.pack(side=tk.RIGHT)
        self.btn_hk = tk.Button(hk, text="Изменить", font=("Segoe UI", 8),
                                 bg=FIELD, fg=FG, relief=tk.FLAT,
                                 cursor="hand2", command=self._capture_hk)
        self.btn_hk.pack(side=tk.RIGHT, padx=(0, 4))

        # Microphone
        from core.audio_recorder import AudioRecorder
        devs = AudioRecorder.list_devices()
        mics = ["По умолчанию"] + [d["name"][:30] for d in devs]
        self.mic_var = self._row_select(m, "Микрофон", mics,
                                         "По умолчанию", "mic")

        # Toggles
        sep = tk.Frame(m, height=1, bg="#333333")
        sep.pack(fill=tk.X, pady=6)

        self.filler_var = tk.BooleanVar(value=self.settings.get("remove_filler_words"))
        self._row_check(m, "Удалять слова-паразиты", self.filler_var, "filler")

        self.vc_var = tk.BooleanVar(value=self.settings.get("voice_commands"))
        self._row_check(m, "Голосовые команды", self.vc_var, "voice_cmd")

        self.vad_var = tk.BooleanVar(value=self.settings.get("vad_enabled", False))
        self._row_check(m, "Автопрослушивание", self.vad_var, "vad")

        # Autostart
        from core.autostart import is_autostart_enabled
        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        self._row_check(m, "Запускать с Windows", self.autostart_var, "autostart")

        # Update section
        sep2 = tk.Frame(m, height=1, bg="#333333")
        sep2.pack(fill=tk.X, pady=6)

        upd_row = tk.Frame(m, bg=ROW_BG, padx=8, pady=5)
        upd_row.pack(fill=tk.X, pady=2)

        from core.updater import get_current_version
        tk.Label(upd_row, text=f"Версия: {get_current_version()}",
                 font=("Segoe UI", 9), fg=FG2, bg=ROW_BG
                 ).pack(side=tk.LEFT)

        self._upd_btn = tk.Button(
            upd_row, text="Проверить обновления", font=("Segoe UI", 9),
            bg="#2A4A5A", fg=FG, relief=tk.FLAT, padx=8,
            cursor="hand2", command=self._check_update)
        self._upd_btn.pack(side=tk.RIGHT)

        self._upd_label = tk.Label(upd_row, text="", font=("Segoe UI", 8),
                                    fg=FG2, bg=ROW_BG)
        self._upd_label.pack(side=tk.RIGHT, padx=(0, 6))

        # Footer
        tk.Label(m, text="🔒 Локально • История: 20", font=("Segoe UI", 8),
                 fg=FG2, bg=BG).pack(anchor=tk.W, pady=(6, 4))

        bf = tk.Frame(m, bg=BG)
        bf.pack(fill=tk.X, pady=(2, 0))
        tk.Button(bf, text="Сохранить", font=("Segoe UI", 10, "bold"),
                  bg="#2D6A2D", fg="white", relief=tk.FLAT, padx=16, pady=3,
                  cursor="hand2", command=self._save).pack(side=tk.RIGHT)
        tk.Button(bf, text="Отмена", font=("Segoe UI", 10),
                  bg=FIELD, fg=FG, relief=tk.FLAT, padx=12, pady=3,
                  cursor="hand2", command=self.win.destroy
                  ).pack(side=tk.RIGHT, padx=(0, 6))
        if self.history_manager:
            tk.Button(bf, text="История", font=("Segoe UI", 10),
                      bg="#2A4050", fg=FG, relief=tk.FLAT, padx=12, pady=3,
                      cursor="hand2", command=self._history
                      ).pack(side=tk.LEFT)

        # Fit window to content
        self.win.update_idletasks()
        w = 420
        h = m.winfo_reqheight() + 20
        self.win.geometry(f"{w}x{h}")

    def _tip(self, parent, key):
        lbl = tk.Label(parent, text=" ? ", font=("Segoe UI", 8, "bold"),
                       fg=ACCENT, bg=ROW_BG, cursor="hand2")
        lbl.pack(side=tk.RIGHT, padx=(4, 4))
        if key in TIPS:
            Tooltip(lbl, TIPS[key])

    def _row_select(self, parent, label, values, current, tip_key):
        row = tk.Frame(parent, bg=ROW_BG, padx=8, pady=4)
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label, font=("Segoe UI", 10),
                 fg=FG, bg=ROW_BG).pack(side=tk.LEFT)
        self._tip(row, tip_key)
        var = tk.StringVar(value=current)
        om = tk.OptionMenu(row, var, *values)
        om.configure(font=("Segoe UI", 9), bg=FIELD, fg=FG,
                     activebackground="#444", activeforeground=FG,
                     highlightthickness=0, relief=tk.FLAT)
        om["menu"].configure(bg=FIELD, fg=FG, activebackground="#444",
                             font=("Segoe UI", 9))
        om.pack(side=tk.RIGHT)
        return var

    def _row_check(self, parent, label, var, tip_key,
                   enabled=True, note=""):
        row = tk.Frame(parent, bg=ROW_BG, padx=8, pady=4)
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label, font=("Segoe UI", 10),
                 fg=FG, bg=ROW_BG).pack(side=tk.LEFT)
        self._tip(row, tip_key)
        cb = tk.Checkbutton(row, variable=var, bg=ROW_BG,
                            selectcolor=FIELD, activebackground=ROW_BG,
                            fg=FG, activeforeground=FG)
        cb.pack(side=tk.RIGHT)
        if not enabled:
            cb.configure(state=tk.DISABLED)
            var.set(False)
        if note:
            tk.Label(row, text=note, font=("Segoe UI", 8),
                     fg="#AA6666", bg=ROW_BG).pack(side=tk.RIGHT, padx=(0, 4))

    def _build_dl(self, downloaded):
        for w in self._mf.winfo_children():
            w.destroy()
        items = [(n, mb) for n, mb in downloaded.items() if mb > 0]
        if not items:
            return
        row = tk.Frame(self._mf, bg=BG)
        row.pack(fill=tk.X)
        total = sum(mb for _, mb in items)
        names = ", ".join(f"{n}({mb}MB)" for n, mb in items)
        tk.Label(row, text=f"Скачано: {names} — {total} MB",
                 font=("Segoe UI", 8), fg=FG2, bg=BG).pack(side=tk.LEFT)
        tk.Button(row, text="Очистить", font=("Segoe UI", 7),
                  bg="#3A2020", fg="#CC8888", relief=tk.FLAT,
                  cursor="hand2", command=self._del_all
                  ).pack(side=tk.RIGHT)

    def _del_all(self):
        from tkinter import messagebox
        if not messagebox.askyesno("Удалить", "Удалить все модели?",
                                    parent=self.win):
            return
        cache = os.path.expanduser("~/.cache/huggingface/hub")
        for name in MODEL_SIZES:
            p = os.path.join(cache, f"models--Systran--faster-whisper-{name}")
            if os.path.exists(p):
                shutil.rmtree(p, ignore_errors=True)
        self._build_dl(get_downloaded_models())

    def _history(self):
        if self.history_manager:
            from gui.history_window import HistoryWindow
            HistoryWindow(self.win, self.history_manager)

    def _check_update(self):
        self._upd_btn.configure(state=tk.DISABLED, text="Проверка...")
        self._upd_label.configure(text="", fg=FG2)

        def check():
            from core.updater import check_update
            result = check_update()
            self.win.after(0, self._on_update_check, result)

        import threading
        threading.Thread(target=check, daemon=True).start()

    def _on_update_check(self, result):
        if result:
            ver = result["version"]
            self._upd_label.configure(
                text=f"Доступна v{ver}", fg="#55BB55")
            self._upd_btn.configure(
                state=tk.NORMAL, text="Обновить",
                bg="#2D6A2D",
                command=lambda: self._do_update(result["url"]))
        else:
            self._upd_label.configure(
                text="Обновлений нет", fg=FG2)
            self._upd_btn.configure(
                state=tk.NORMAL, text="Проверить обновления",
                bg="#2A4A5A")

    def _do_update(self, url):
        self._upd_btn.configure(state=tk.DISABLED, text="Обновление...")
        self._upd_label.configure(text="Скачивание...", fg="#CCAA44")

        def update():
            from core.updater import download_and_apply
            def progress(msg):
                self.win.after(0, self._upd_label.configure,
                               {"text": msg})
            ok = download_and_apply(url, on_progress=progress)
            if ok:
                self.win.after(0, self._upd_btn.configure,
                               {"text": "Перезапустите", "state": tk.DISABLED})
            else:
                self.win.after(0, self._upd_btn.configure,
                               {"text": "Ошибка", "state": tk.NORMAL})

        import threading
        threading.Thread(target=update, daemon=True).start()

    def _capture_hk(self):
        from core.hotkey_manager import HotkeyManager
        self.lbl_hk.configure(fg="#FFAA00")
        self.hotkey_var.set("...")
        self.btn_hk.configure(state=tk.DISABLED)

        def done(combo):
            def up():
                self.hotkey_var.set(combo or self.settings.get("hotkey"))
                self.lbl_hk.configure(fg=ACCENT)
                self.btn_hk.configure(state=tk.NORMAL)
            self.win.after(0, up)
        HotkeyManager.capture_next_combo(done, timeout=5.0)

    def _get_engine(self):
        label = self.engine_var.get()
        for i, el in enumerate(self._engine_labels):
            if el == label:
                return self._engine_values[i]
        return label.split()[0]

    def _get_model(self):
        label = self.model_var.get()
        for i, ml in enumerate(self._model_labels):
            if ml == label:
                return self._model_values[i]
        return label.split()[0]

    def _save(self):
        try:
            self.settings.set("engine", self._get_engine())
            self.settings.set("model", self._get_model())
            self.settings.set("language", self.language_var.get())
            self.settings.set("device", "cuda" if self.gpu_var.get() else "cpu")
            self.settings.set("hotkey", self.hotkey_var.get())
            self.settings.set("remove_filler_words", self.filler_var.get())
            self.settings.set("voice_commands", self.vc_var.get())
            self.settings.set("vad_enabled", self.vad_var.get())
            self.settings.save()
            # Autostart
            from core.autostart import enable_autostart, disable_autostart
            if self.autostart_var.get():
                enable_autostart()
            else:
                disable_autostart()
        except Exception as e:
            print(f"Save: {e}")
        parent = self.win.master
        cb = self.on_save
        self.win.destroy()
        if cb and parent:
            parent.after(300, cb)
