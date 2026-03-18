"""First-run bootstrapper — downloads heavy dependencies on demand.

When running from EXE, torch and faster-whisper may not be bundled.
This module checks and installs them into a local _deps folder.
"""

import os
import sys
import subprocess
import importlib
import tkinter as tk
from tkinter import ttk


# Where to install runtime deps (next to exe or app.py)
def _get_deps_dir():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "_deps")


DEPS_DIR = _get_deps_dir()


def _ensure_deps_on_path():
    """Add _deps to sys.path if it exists."""
    if os.path.exists(DEPS_DIR) and DEPS_DIR not in sys.path:
        sys.path.insert(0, DEPS_DIR)
        # Also add site-packages inside _deps
        sp = os.path.join(DEPS_DIR, "Lib", "site-packages")
        if os.path.exists(sp) and sp not in sys.path:
            sys.path.insert(0, sp)


def _is_available(module_name):
    """Check if a module can be imported."""
    _ensure_deps_on_path()
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def check_dependencies():
    """Returns list of missing heavy dependencies."""
    missing = []
    if not _is_available("faster_whisper"):
        missing.append("faster-whisper")
    if not _is_available("torch"):
        # torch is needed for openai-whisper engine
        # faster-whisper uses ctranslate2 which doesn't need torch
        pass  # Optional, don't require
    return missing


def install_dependencies(missing, on_progress=None, on_status=None):
    """Install missing dependencies into _deps folder."""
    if not missing:
        return True

    os.makedirs(DEPS_DIR, exist_ok=True)

    python = sys.executable
    if getattr(sys, 'frozen', False):
        # In frozen exe, use embedded pip via ensurepip
        # First try to find pip
        try:
            subprocess.run(
                [python, "-m", "pip", "--version"],
                capture_output=True, timeout=10
            )
            has_pip = True
        except Exception:
            has_pip = False

        if not has_pip:
            if on_status:
                on_status("Установка pip...")
            try:
                subprocess.run(
                    [python, "-m", "ensurepip", "--default-pip"],
                    capture_output=True, timeout=60
                )
            except Exception:
                return False

    for pkg in missing:
        if on_status:
            on_status(f"Установка {pkg}...")

        cmd = [
            python, "-m", "pip", "install",
            pkg,
            "--target", DEPS_DIR,
            "--no-warn-script-location",
            "--quiet",
        ]

        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace"
            )
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if on_progress and line.strip():
                    on_progress(line.strip())

            if proc.returncode != 0:
                return False
        except Exception as e:
            print(f"Install error: {e}")
            return False

    _ensure_deps_on_path()
    return True


class SetupWindow:
    """GUI window for first-run dependency installation."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Speech-to-Text — Первая настройка")
        self.root.configure(bg="#1E1E2E")
        self.root.geometry("420x280")
        self.root.resizable(False, False)

        # Center on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 420) // 2
        y = (self.root.winfo_screenheight() - 280) // 2
        self.root.geometry(f"+{x}+{y}")

        self.success = False
        self._build_ui()

    def _build_ui(self):
        bg = "#1E1E2E"
        fg = "#E0E0E0"

        tk.Label(self.root, text="Speech-to-Text",
                 font=("Segoe UI", 16, "bold"), fg="#88AAFF", bg=bg
                 ).pack(pady=(20, 5))

        tk.Label(self.root, text="Первый запуск — скачивание компонентов",
                 font=("Segoe UI", 10), fg=fg, bg=bg
                 ).pack(pady=(0, 15))

        self.status_label = tk.Label(self.root, text="Проверка зависимостей...",
                                     font=("Segoe UI", 9), fg="#AAAAAA", bg=bg)
        self.status_label.pack(pady=5)

        # Progress bar
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Setup.Horizontal.TProgressbar",
                        troughcolor="#2A2A3E", background="#88AAFF",
                        thickness=16)

        self.progress = ttk.Progressbar(self.root, mode="indeterminate",
                                         style="Setup.Horizontal.TProgressbar",
                                         length=340)
        self.progress.pack(pady=10)

        self.detail_label = tk.Label(self.root, text="",
                                      font=("Segoe UI", 8), fg="#888888", bg=bg,
                                      wraplength=380)
        self.detail_label.pack(pady=5)

        self.btn = tk.Button(self.root, text="Установить",
                              font=("Segoe UI", 10, "bold"),
                              bg="#3A5A8C", fg="white", relief=tk.FLAT,
                              cursor="hand2", padx=20, pady=5,
                              command=self._start_install)
        self.btn.pack(pady=10)

    def _start_install(self):
        self.btn.configure(state=tk.DISABLED, text="Установка...")
        self.progress.start(15)

        import threading
        t = threading.Thread(target=self._install_thread, daemon=True)
        t.start()

    def _install_thread(self):
        missing = check_dependencies()
        if not missing:
            self._on_done(True)
            return

        ok = install_dependencies(
            missing,
            on_progress=lambda s: self.root.after(0, self._update_detail, s),
            on_status=lambda s: self.root.after(0, self._update_status, s),
        )
        self._on_done(ok)

    def _update_status(self, text):
        self.status_label.configure(text=text)

    def _update_detail(self, text):
        self.detail_label.configure(text=text[-60:] if len(text) > 60 else text)

    def _on_done(self, success):
        def _finish():
            self.progress.stop()
            self.success = success
            if success:
                self.status_label.configure(text="Готово!", fg="#88FF88")
                self.btn.configure(text="Запустить", state=tk.NORMAL,
                                    command=self.root.destroy)
            else:
                self.status_label.configure(text="Ошибка установки", fg="#FF8888")
                self.btn.configure(text="Повторить", state=tk.NORMAL,
                                    command=self._start_install)
        self.root.after(0, _finish)

    def run(self):
        self.root.mainloop()
        return self.success


def ensure_ready():
    """Check deps, show setup window if needed. Returns True if ready."""
    _ensure_deps_on_path()
    missing = check_dependencies()
    if not missing:
        return True

    # Show setup window
    win = SetupWindow()
    return win.run()
