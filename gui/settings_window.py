"""Settings — two columns, localized."""

import os
import shutil
import tkinter as tk

from core.settings_manager import SettingsManager, VALID_VALUES
from core.gpu_detector import (
    detect_device, get_recommended_model,
    get_downloaded_models, format_model_label, MODEL_SIZES,
    get_installed_engines, format_engine_label,
)
from core.i18n import t, set_language, get_language
from gui.tooltip import Tooltip

BG = "#1E1E1E"
FG = "#E0E0E0"
FG2 = "#888888"
FIELD = "#2E2E2E"
ACCENT = "#5599DD"
GREEN = "#55BB55"
ROW = "#252525"

UI_LANGS = {"ru": "Русский", "en": "English"}


class SettingsWindow:
    def __init__(self, parent, settings: SettingsManager,
                 on_save=None, history_manager=None):
        self.settings = settings
        self.on_save = on_save
        self.history_manager = history_manager
        set_language(self.settings.get("ui_language", "ru"))

        self.win = tk.Toplevel(parent)
        self.win.title(t("settings_title"))
        self.win.attributes("-topmost", True)
        self.win.resizable(True, True)
        self.win.configure(bg=BG)

        device = detect_device()
        recommended = get_recommended_model(device)
        downloaded = get_downloaded_models()
        installed = get_installed_engines()

        root = tk.Frame(self.win, bg=BG, padx=12, pady=8)
        root.pack(fill=tk.BOTH, expand=True)

        # Header
        hdr = tk.Frame(root, bg=BG)
        hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(hdr, text=t("settings_title"), font=("Segoe UI Semibold", 14),
                 fg=FG, bg=BG).pack(side=tk.LEFT)
        gpu_txt = "GPU ✓" if device == "cuda" else "CPU"
        tk.Label(hdr, text=gpu_txt, font=("Segoe UI", 9),
                 fg=GREEN if device == "cuda" else "#AA8833", bg=BG
                 ).pack(side=tk.RIGHT)

        # Two columns
        cols = tk.Frame(root, bg=BG)
        cols.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(cols, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        right = tk.Frame(cols, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # ========= LEFT COLUMN =========

        # --- Recognition ---
        self._section(left, t("section_recognition"))

        self._engine_values = [e for e in VALID_VALUES["engine"] if installed.get(e)]
        self._engine_labels = [format_engine_label(e, installed)
                               for e in self._engine_values]
        cur_eng = self.settings.get("engine")
        if cur_eng not in self._engine_values and self._engine_values:
            cur_eng = self._engine_values[0]
        self.engine_var = self._select(
            left, t("engine"), self._engine_labels,
            format_engine_label(cur_eng, installed), "tip_engine")

        cuda_ok = device == "cuda"
        self.gpu_var = tk.BooleanVar(
            value=cuda_ok and self.settings.get("device") != "cpu")
        self._check(left, t("use_gpu"), self.gpu_var, "tip_device",
                    enabled=cuda_ok,
                    note="" if cuda_ok else t("gpu_unavailable"))

        self._model_values = list(VALID_VALUES["model"])
        self._model_labels = [format_model_label(n, downloaded, recommended)
                              for n in self._model_values]
        cur_mod = self.settings.get("model")
        self.model_var = self._select(
            left, t("model"), self._model_labels,
            format_model_label(cur_mod, downloaded, recommended), "tip_model")

        # Models list — each on its own line with size
        self._mf = tk.Frame(left, bg=BG)
        self._mf.pack(fill=tk.X, pady=(2, 4))
        self._build_models(downloaded)

        self.language_var = self._select(
            left, t("language"), list(VALID_VALUES["language"]),
            self.settings.get("language"), "tip_language")

        # --- Processing ---
        self._section(left, t("section_processing"))

        self.streaming_var = tk.BooleanVar(
            value=self.settings.get("streaming_insert", True))
        self._check(left, t("streaming_insert"), self.streaming_var, "tip_streaming")

        self.filler_var = tk.BooleanVar(
            value=self.settings.get("remove_filler_words"))
        self._check(left, t("filler_words"), self.filler_var, "tip_filler")

        self.vc_var = tk.BooleanVar(value=self.settings.get("voice_commands"))
        self._check(left, t("voice_commands"), self.vc_var, "tip_voice_cmd")

        # ========= RIGHT COLUMN =========

        # --- Controls ---
        self._section(right, t("section_control"))

        # Hotkey
        hk = tk.Frame(right, bg=ROW, padx=8, pady=8)
        hk.pack(fill=tk.X, pady=4)
        tk.Label(hk, text=t("hotkey"), font=("Segoe UI", 10),
                 fg=FG, bg=ROW).pack(anchor=tk.W)
        hk2 = tk.Frame(hk, bg=ROW)
        hk2.pack(fill=tk.X, pady=(4, 0))
        self.hotkey_var = tk.StringVar(value=self.settings.get("hotkey"))
        tk.Label(hk2, textvariable=self.hotkey_var,
                 font=("Segoe UI", 11, "bold"), fg=ACCENT,
                 bg=FIELD, padx=10, pady=3).pack(side=tk.LEFT)
        self.btn_hk = tk.Button(
            hk2, text=t("hotkey_change"), font=("Segoe UI", 10),
            bg="#3A5A6A", fg=FG, relief=tk.FLAT, padx=10, pady=2,
            cursor="hand2", command=self._capture_hk)
        self.btn_hk.pack(side=tk.LEFT, padx=(8, 0))
        self._tip_btn(hk2, "tip_hotkey")

        from core.audio_recorder import AudioRecorder
        devs = AudioRecorder.list_devices()
        mics = [t("mic_default")] + [d["name"][:25] for d in devs]
        self.mic_var = self._select(right, t("microphone"), mics,
                                     t("mic_default"), "tip_mic")

        # --- Other ---
        self._section(right, "")

        self.vad_var = tk.BooleanVar(value=self.settings.get("vad_enabled", False))
        self._check(right, t("auto_listen"), self.vad_var, "tip_vad")

        from core.autostart import is_autostart_enabled
        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        self._check(right, t("autostart"), self.autostart_var, "tip_autostart")

        self.ui_lang_var = self._select(
            right, t("ui_language"), list(UI_LANGS.values()),
            UI_LANGS.get(self.settings.get("ui_language", "ru"), "Русский"),
            "tip_ui_lang")

        # Update
        upd = tk.Frame(right, bg=ROW, padx=8, pady=6)
        upd.pack(fill=tk.X, pady=4)
        from core.updater import get_current_version
        tk.Label(upd, text=f"v{get_current_version()}",
                 font=("Segoe UI", 9), fg=FG2, bg=ROW).pack(side=tk.LEFT)
        self._upd_btn = tk.Button(
            upd, text=t("check_updates"), font=("Segoe UI", 9),
            bg="#2A4A5A", fg=FG, relief=tk.FLAT, padx=6,
            cursor="hand2", command=self._check_update)
        self._upd_btn.pack(side=tk.RIGHT)
        self._upd_lbl = tk.Label(upd, text="", font=("Segoe UI", 8),
                                  fg=FG2, bg=ROW)
        self._upd_lbl.pack(side=tk.RIGHT, padx=(0, 6))

        # ========= FOOTER =========
        tk.Frame(root, height=1, bg="#333").pack(fill=tk.X, pady=(8, 6))

        bf = tk.Frame(root, bg=BG)
        bf.pack(fill=tk.X)
        tk.Button(bf, text=t("save"), font=("Segoe UI", 11, "bold"),
                  bg="#2D6A2D", fg="white", relief=tk.FLAT, padx=20, pady=4,
                  cursor="hand2", command=self._save).pack(side=tk.RIGHT)
        tk.Button(bf, text=t("cancel"), font=("Segoe UI", 10),
                  bg=FIELD, fg=FG, relief=tk.FLAT, padx=14, pady=4,
                  cursor="hand2", command=self.win.destroy
                  ).pack(side=tk.RIGHT, padx=(0, 8))
        if self.history_manager:
            tk.Button(bf, text=t("history"), font=("Segoe UI", 10),
                      bg="#2A4050", fg=FG, relief=tk.FLAT, padx=14, pady=4,
                      cursor="hand2", command=self._history
                      ).pack(side=tk.LEFT)

        self.win.update_idletasks()
        w = max(root.winfo_reqwidth() + 24, 600)
        h = min(root.winfo_reqheight() + 20,
                self.win.winfo_screenheight() - 50)
        self.win.geometry(f"{w}x{h}")

    # --- Widgets ---

    def _section(self, parent, text):
        if text:
            tk.Label(parent, text=text, font=("Segoe UI", 10, "bold"),
                     fg=ACCENT, bg=BG).pack(anchor=tk.W, pady=(8, 6))

    def _tip_btn(self, parent, key):
        lbl = tk.Label(parent, text=" ? ", font=("Segoe UI", 8, "bold"),
                       fg=ACCENT, bg=ROW, cursor="hand2")
        lbl.pack(side=tk.RIGHT, padx=(4, 0))
        Tooltip(lbl, t(key))

    def _select(self, parent, label, values, current, tip_key):
        r = tk.Frame(parent, bg=ROW, padx=8, pady=6)
        r.pack(fill=tk.X, pady=3)
        tk.Label(r, text=label, font=("Segoe UI", 10),
                 fg=FG, bg=ROW).pack(side=tk.LEFT)
        self._tip_btn(r, tip_key)
        var = tk.StringVar(value=current)
        om = tk.OptionMenu(r, var, *values)
        om.configure(font=("Segoe UI", 9), bg=FIELD, fg=FG,
                     activebackground="#444", highlightthickness=0,
                     relief=tk.FLAT)
        om["menu"].configure(bg=FIELD, fg=FG, activebackground="#444",
                             font=("Segoe UI", 9))
        om.pack(side=tk.RIGHT)
        return var

    def _check(self, parent, label, var, tip_key,
               enabled=True, note=""):
        r = tk.Frame(parent, bg=ROW, padx=8, pady=6)
        r.pack(fill=tk.X, pady=3)
        tk.Label(r, text=label, font=("Segoe UI", 10),
                 fg=FG, bg=ROW).pack(side=tk.LEFT)
        self._tip_btn(r, tip_key)
        cb = tk.Checkbutton(r, variable=var, bg=ROW,
                            selectcolor=FIELD, activebackground=ROW,
                            fg=FG, activeforeground=FG)
        cb.pack(side=tk.RIGHT)
        if not enabled:
            cb.configure(state=tk.DISABLED); var.set(False)
        if note:
            tk.Label(r, text=note, font=("Segoe UI", 8),
                     fg="#AA6666", bg=ROW).pack(side=tk.RIGHT, padx=(0, 4))

    # --- Actions ---

    def _build_models(self, downloaded):
        for w in self._mf.winfo_children():
            w.destroy()
        for name, expected in MODEL_SIZES.items():
            mb = downloaded.get(name, 0)
            row = tk.Frame(self._mf, bg=ROW, padx=8, pady=2)
            row.pack(fill=tk.X, pady=1)
            if mb > 0:
                tk.Label(row, text=f"✓ {name}", font=("Segoe UI", 8),
                         fg=GREEN, bg=ROW, width=10, anchor=tk.W
                         ).pack(side=tk.LEFT)
                tk.Label(row, text=f"{mb} MB", font=("Segoe UI", 8),
                         fg=FG2, bg=ROW).pack(side=tk.LEFT)
                tk.Button(row, text="✕", font=("Segoe UI", 7),
                          bg="#4A2020", fg="#CC8888", relief=tk.FLAT,
                          cursor="hand2",
                          command=lambda n=name: self._del_model(n)
                          ).pack(side=tk.RIGHT)
            else:
                tk.Label(row, text=f"  {name}", font=("Segoe UI", 8),
                         fg=FG2, bg=ROW, width=10, anchor=tk.W
                         ).pack(side=tk.LEFT)
                tk.Label(row, text=expected, font=("Segoe UI", 8),
                         fg="#666", bg=ROW).pack(side=tk.LEFT)

        total = sum(v for v in downloaded.values())
        dl_names = [n for n, mb in downloaded.items() if mb > 0]

        if total > 0:
            tk.Label(self._mf, text=f"  {t('on_disk')}: {total} MB",
                     font=("Segoe UI", 8), fg=FG2, bg=BG).pack(anchor=tk.W)

        # Warn if multiple models downloaded
        if len(dl_names) > 1:
            warn = tk.Frame(self._mf, bg="#3A2A1A", padx=8, pady=4)
            warn.pack(fill=tk.X, pady=(2, 0))
            tk.Label(warn,
                     text="Модели заменяют друг друга — достаточно одной",
                     font=("Segoe UI", 8), fg="#DDAA44", bg="#3A2A1A"
                     ).pack(side=tk.LEFT)
            tk.Button(warn, text="Удалить лишние", font=("Segoe UI", 8),
                      bg="#5A3A1A", fg="#DDAA44", relief=tk.FLAT,
                      cursor="hand2",
                      command=lambda: self._del_except_best(downloaded)
                      ).pack(side=tk.RIGHT)

    def _del_except_best(self, downloaded):
        """Keep only the largest (best) downloaded model, delete the rest."""
        dl = [(n, mb) for n, mb in downloaded.items() if mb > 0]
        if len(dl) <= 1:
            return
        # Model quality order
        order = ["large-v3", "medium", "small", "base", "tiny"]
        best = None
        for name in order:
            if downloaded.get(name, 0) > 0:
                best = name
                break
        if not best:
            return
        deleted = []
        for name, mb in dl:
            if name != best:
                self._remove_model_files(name)
                deleted.append(name)
        if deleted:
            print(f"Deleted models: {', '.join(deleted)}, kept: {best}")
        self._build_models(get_downloaded_models())

    def _remove_model_files(self, name):
        """Delete model from local models/ and HF cache."""
        from core.gpu_detector import get_models_dir
        # Local
        local = os.path.join(get_models_dir(), f"faster-whisper-{name}")
        if os.path.exists(local):
            shutil.rmtree(local, ignore_errors=True)
        # HF cache
        hf = os.path.join(os.path.expanduser("~/.cache/huggingface/hub"),
                          f"models--Systran--faster-whisper-{name}")
        if os.path.exists(hf):
            shutil.rmtree(hf, ignore_errors=True)

    def _del_model(self, name):
        from tkinter import messagebox
        if not messagebox.askyesno(t("delete_model"),
                                    t("delete_model_confirm", name=name),
                                    parent=self.win):
            return
        self._remove_model_files(name)
        self._build_models(get_downloaded_models())

    def _history(self):
        if self.history_manager:
            from gui.history_window import HistoryWindow
            HistoryWindow(self.win, self.history_manager)

    def _capture_hk(self):
        from core.hotkey_manager import HotkeyManager
        self.hotkey_var.set(t("hotkey_press"))
        self.btn_hk.configure(state=tk.DISABLED)
        def done(combo):
            def up():
                self.hotkey_var.set(combo or self.settings.get("hotkey"))
                self.btn_hk.configure(state=tk.NORMAL)
            self.win.after(0, up)
        HotkeyManager.capture_next_combo(done, timeout=5.0)

    def _check_update(self):
        self._upd_btn.configure(state=tk.DISABLED, text="...")
        def check():
            from core.updater import check_update
            r = check_update()
            self.win.after(0, self._on_upd, r)
        import threading
        threading.Thread(target=check, daemon=True).start()

    def _on_upd(self, r):
        if r:
            self._upd_lbl.configure(text=t("update_available", ver=r["version"]), fg=GREEN)
            self._upd_btn.configure(state=tk.NORMAL, text=t("update_now"),
                                     bg="#2D6A2D",
                                     command=lambda: self._do_upd(r["url"]))
        else:
            self._upd_lbl.configure(text=t("no_updates"), fg=FG2)
            self._upd_btn.configure(state=tk.NORMAL, text=t("check_updates"))

    def _do_upd(self, url):
        self._upd_btn.configure(state=tk.DISABLED, text=t("updating"))
        def go():
            from core.updater import download_and_apply
            ok = download_and_apply(url,
                lambda msg: self.win.after(0, self._upd_lbl.configure, {"text": msg}))
            if ok:
                self.win.after(0, self._upd_btn.configure,
                               {"text": t("restart_needed"), "state": tk.DISABLED})
        import threading
        threading.Thread(target=go, daemon=True).start()

    def _get_engine(self):
        l = self.engine_var.get()
        for i, el in enumerate(self._engine_labels):
            if el == l: return self._engine_values[i]
        return l.split()[0]

    def _get_model(self):
        l = self.model_var.get()
        for i, ml in enumerate(self._model_labels):
            if ml == l: return self._model_values[i]
        return l.split()[0]

    def _save(self):
        try:
            self.settings.set("engine", self._get_engine())
            self.settings.set("model", self._get_model())
            self.settings.set("language", self.language_var.get())
            self.settings.set("device", "cuda" if self.gpu_var.get() else "cpu")
            self.settings.set("hotkey", self.hotkey_var.get())
            self.settings.set("streaming_insert", self.streaming_var.get())
            self.settings.set("remove_filler_words", self.filler_var.get())
            self.settings.set("voice_commands", self.vc_var.get())
            self.settings.set("vad_enabled", self.vad_var.get())
            lang_name = self.ui_lang_var.get()
            ui_lang = next((c for c, n in UI_LANGS.items() if n == lang_name), "ru")
            self.settings.set("ui_language", ui_lang)
            set_language(ui_lang)
            self.settings.save()
            from core.autostart import enable_autostart, disable_autostart
            (enable_autostart if self.autostart_var.get() else disable_autostart)()
        except Exception as e:
            print(f"Save: {e}")
        parent = self.win.master
        cb = self.on_save
        self.win.destroy()
        if cb and parent:
            parent.after(300, cb)
