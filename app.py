"""Speech-to-Text — GUI application.

Запуск: python app.py          (GUI режим)
        python app.py --console (консольный режим)
"""

import sys
import time
import os
import threading
import ctypes
import tkinter as tk

# Fix blurry text on HiDPI monitors
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Suppress HuggingFace warnings on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_XET_WARNING"] = "1"

# Suppress "unauthenticated requests" warning
import warnings
warnings.filterwarnings("ignore", message=".*unauthenticated.*")
warnings.filterwarnings("ignore", message=".*hf_xet.*")

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from core.gpu_detector import detect_device, get_compute_type
from core.settings_manager import SettingsManager
from core.audio_recorder import AudioRecorder
from core.model_manager import ModelManager
from core.window_tracker import WindowTracker
from core.text_inserter import TextInserter
from core.hotkey_manager import HotkeyManager
from core.text_processor import TextProcessor
from core.history_manager import HistoryManager
from core.stream_recognizer import StreamRecognizer
from core.voice_commands import VoiceCommandProcessor
from core.tray_icon import TrayIcon
from core.vad_listener import VADListener


def load_vocabulary(path: str = None) -> str | None:
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "vocabulary.txt")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        terms = [line.strip() for line in f if line.strip()]
    if not terms:
        return None
    return "В тексте используются: " + ", ".join(terms)


class App:
    """Main application — indicator-only UI, no overlay window."""

    # States
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"

    def __init__(self):
        self.state = self.IDLE
        self._state_lock = threading.Lock()

        # Hidden root window (required for tkinter)
        self.root = tk.Tk()
        self.root.withdraw()

        # Settings & language
        self.settings = SettingsManager()
        from core.i18n import set_language
        set_language(self.settings.get("ui_language", "ru"))
        device_setting = self.settings.get("device")
        if device_setting == "auto":
            self.device = detect_device()
        else:
            self.device = device_setting

        self.vocabulary = load_vocabulary()

        # Model
        self.model_manager = ModelManager()
        self._load_current_model()

        # Text processing & history
        self.text_processor = TextProcessor(self.settings)
        self.voice_commands = VoiceCommandProcessor(
            enabled=self.settings.get("voice_commands")
        )
        self.history = HistoryManager(max_items=20)

        # Streaming
        self.streamer: StreamRecognizer | None = None

        # Window tracking
        self.tracker = WindowTracker()
        # Use root's HWND so tracker ignores our dialogs
        self.root.update_idletasks()
        try:
            own_hwnd = int(self.root.wm_frame(), 16)
        except Exception:
            own_hwnd = 0
        self.tracker.set_own_hwnd(own_hwnd)
        self.inserter = TextInserter(self.tracker)

        # Indicator — main UI
        from gui.indicator import FloatingIndicator
        ind_x = self.settings.get("indicator_x")
        ind_y = self.settings.get("indicator_y")
        self.indicator = FloatingIndicator(
            self.root, x=ind_x, y=ind_y,
            on_right_click=self._on_menu,
            on_left_click=lambda e: self._on_settings(),
        )

        # Global hotkey (registered after first-run wizard completes)
        self.hotkey = HotkeyManager(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )
        self._hotkey_registered = False

        # System tray
        self.tray = TrayIcon(
            on_settings=self._on_settings,
            on_history=self._on_history,
            on_files=self._on_file_transcribe,
            on_show=lambda: None,
            on_exit=self._on_exit,
        )
        self.tray.start()

        # VAD (auto-listen)
        self.vad = VADListener()
        self.vad.on_speech_end = self._on_vad_speech_end
        self.vad.on_audio_level = self._on_audio_level
        if self.settings.get("vad_enabled"):
            self.vad.start()
            print("VAD auto-listen: ON")

        # Poll tracker
        self._poll_tracker()

    def _load_current_model(self):
        engine = self.settings.get("engine")
        model_name = self.settings.get("model")
        print(f"Loading: {engine} / {model_name} ({self.device})...")
        self.recognizer = self.model_manager.get_recognizer(
            engine, model_name, self.device
        )
        print("Model ready.")

    def _poll_tracker(self):
        self.tracker.poll()
        self.root.after(200, self._poll_tracker)

    def _schedule(self, callback, *args):
        """Schedule callback on main tkinter thread."""
        self.root.after(0, callback, *args)

    # === State management ===

    def _set_state(self, new_state: str) -> bool:
        """Thread-safe state transition. Returns True if successful."""
        with self._state_lock:
            # Allow any transition except recording->recording
            if new_state == self.RECORDING and self.state == self.RECORDING:
                return False
            self.state = new_state
            return True

    # === Hotkey ===

    def _on_hotkey_press(self):
        if not self._set_state(self.RECORDING):
            self._on_hotkey_release()
            time.sleep(0.1)
            if not self._set_state(self.RECORDING):
                return

        self._schedule(self.indicator.set_state, "recording")
        self.tracker.poll()
        self.tracker.snapshot()
        self._partial_text = ""
        self.inserter.save_clipboard()  # Save before any paste

        # Start streaming
        self.streamer = StreamRecognizer(
            recognizer=self.recognizer,
            language=self.settings.get("language"),
            initial_prompt=self.vocabulary,
        )
        self.streamer.on_partial = self._on_stream_partial
        self.streamer.on_final = self._on_stream_final
        self.streamer.on_error = self._on_stream_error
        self.streamer.on_audio_level = self._on_audio_level
        self.streamer.start()

    def _on_hotkey_release(self):
        if self.state != self.RECORDING:
            return
        self._set_state(self.PROCESSING)
        self._schedule(self.indicator.set_state, "processing")

        if self.streamer:
            self.streamer.stop()
            self.streamer = None

    # === Audio level ===

    def _on_audio_level(self, level: float):
        # Direct call — set_audio_level just stores a float, thread-safe
        self.indicator.set_audio_level(level)

    # === Streaming callbacks ===

    def _on_stream_partial(self, text: str):
        """Append new words directly into target field (if streaming enabled)."""
        if not self.settings.get("streaming_insert", True):
            return
        text = self.voice_commands.process(text)
        # Filter garbage partials
        if not text or len(text.strip().rstrip(".")) < 2:
            return
        from core.stream_recognizer import StreamRecognizer
        if StreamRecognizer._is_hallucination(text):
            return
        self._partial_text = self.inserter.append_diff(
            self._partial_text, text
        )

    def _on_stream_final(self, text: str, duration: float):
        text = self.voice_commands.process(text)
        text = self.text_processor.process(text)

        if not text:
            self._schedule(self.indicator.set_state, "idle")
            self._set_state(self.IDLE)
            return

        # Save to history
        self.history.add(
            text=text,
            engine=self.settings.get("engine"),
            duration=duration,
            elapsed=0,
        )

        # Append remaining diff or insert full text
        if self._partial_text:
            self.inserter.append_diff(self._partial_text, text)
            self._partial_text = ""
        else:
            self.inserter.save_clipboard()
            self.inserter._paste(text)

        # Restore original clipboard
        self.inserter.restore_clipboard()
        print(f"Done [{text[:50]}]")

        self._schedule(self.indicator.set_state, "done")
        self._set_state(self.IDLE)

    def _on_stream_error(self, message: str):
        if message:
            print(f"Error: {message}")
        self._schedule(self.indicator.set_state, "idle")
        self._set_state(self.IDLE)

    # === VAD (auto-listen) ===

    def _on_vad_speech_end(self, audio):
        """Called by VAD when speech segment is detected and ended."""
        if self.state != self.IDLE:
            return

        import numpy as np

        # Check audio quality before transcribing
        duration = len(audio) / 16000
        if duration < 0.8:
            return

        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < 0.012:
            return  # Silence — skip

        self._set_state(self.PROCESSING)
        self._schedule(self.indicator.set_state, "processing")
        self.tracker.snapshot()

        def transcribe():
            language = self.settings.get("language")
            try:
                text = self.recognizer.transcribe(
                    audio, language=language,
                    initial_prompt=self.vocabulary,
                )
            except Exception as e:
                print(f"VAD error: {e}")
                self._schedule(self.indicator.set_state, "idle")
                self._set_state(self.IDLE)
                return

            # Filter hallucinations
            from core.stream_recognizer import StreamRecognizer
            if text and StreamRecognizer._is_hallucination(text):
                self._schedule(self.indicator.set_state, "idle")
                self._set_state(self.IDLE)
                return

            text = self.voice_commands.process(text)
            text = self.text_processor.process(text)

            if not text:
                self._schedule(self.indicator.set_state, "idle")
                self._set_state(self.IDLE)
                return

            duration = len(audio) / 16000
            self.history.add(text=text, engine=self.settings.get("engine"),
                             duration=duration)

            pasted = self.inserter.insert(text)
            if pasted:
                print(f"VAD inserted: {text[:50]}")
                self._schedule(self.indicator.set_state, "done")
            else:
                self.inserter.copy_only(text)
                print(f"VAD clipboard: {text[:50]}")
                self._schedule(self.indicator.set_state, "done")

            self._set_state(self.IDLE)

        threading.Thread(target=transcribe, daemon=True).start()

    # === Menu ===

    def _on_menu(self, event):
        from core.i18n import t
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"⚙  {t('menu_settings')}", command=self._on_settings)
        menu.add_command(label=f"📋  {t('menu_history')}", command=self._on_history)
        menu.add_command(label=f"📁  {t('menu_files')}", command=self._on_file_transcribe)
        menu.add_separator()
        menu.add_command(label=f"✕  {t('menu_exit')}", command=self._on_exit)
        menu.post(event.x_root, event.y_root)

    def _on_settings(self):
        # Don't open if already open
        if hasattr(self, '_settings_win') and self._settings_win:
            try:
                self._settings_win.win.lift()
                return
            except Exception:
                self._settings_win = None

        try:
            from gui.settings_window import SettingsWindow
            self._settings_win = SettingsWindow(
                self.root, self.settings,
                on_save=self._on_settings_saved,
                history_manager=self.history,
            )
            self._settings_win.win.bind("<Destroy>",
                lambda e: setattr(self, '_settings_win', None))
        except Exception as e:
            print(f"Settings error: {e}")
            self._settings_win = None

    def _on_models(self):
        if hasattr(self, '_models_win') and self._models_win:
            try:
                self._models_win.win.lift()
                return
            except Exception:
                self._models_win = None
        from gui.models_window import ModelsWindow
        self._models_win = ModelsWindow(self.root)
        self._models_win.win.bind("<Destroy>",
            lambda e: setattr(self, '_models_win', None))

    def _on_history(self):
        if hasattr(self, '_history_win') and self._history_win:
            try:
                self._history_win.win.lift()
                return
            except Exception:
                self._history_win = None
        from gui.history_window import HistoryWindow
        self._history_win = HistoryWindow(
            self.root, self.history,
            on_insert=lambda text: self.inserter.insert(text),
        )
        self._history_win.win.bind("<Destroy>",
            lambda e: setattr(self, '_history_win', None))

    def _on_file_transcribe(self):
        if hasattr(self, '_file_win') and self._file_win:
            try:
                self._file_win.win.lift()
                return
            except Exception:
                self._file_win = None
        from gui.file_window import FileWindow
        self._file_win = FileWindow(
            self.root,
            recognizer=self.recognizer,
            text_processor=self.text_processor,
            language=self.settings.get("language"),
            initial_prompt=self.vocabulary,
            hf_token=self.settings.get("hf_token"),
        )
        self._file_win.win.bind("<Destroy>",
            lambda e: setattr(self, '_file_win', None))

    def _on_exit(self):
        x, y = self.indicator.get_position()
        self.settings.set("indicator_x", x)
        self.settings.set("indicator_y", y)
        self.settings.save()
        self.hotkey.unregister()
        self.vad.stop()
        self.tray.stop()
        self.indicator.destroy()
        self.root.destroy()

    # === Settings reload ===

    def _on_settings_saved(self):
        try:
            self._apply_settings()
        except Exception as e:
            print(f"Settings apply error: {e}")
            import traceback
            traceback.print_exc()

    def _apply_settings(self):
        # Update device
        device_setting = self.settings.get("device")
        if device_setting == "auto":
            self.device = detect_device()
        else:
            self.device = device_setting

        self.voice_commands.enabled = self.settings.get("voice_commands")

        # Update VAD
        if self.settings.get("vad_enabled"):
            if not self.vad.is_listening:
                self.vad.start()
                print("VAD: ON")
        else:
            if self.vad.is_listening:
                self.vad.stop()
                print("VAD: OFF")

        # Check what changed
        new_engine = self.settings.get("engine")
        new_model = self.settings.get("model")
        new_hotkey = self.settings.get("hotkey")

        # Reload hotkey if changed
        if new_hotkey and new_hotkey != self.hotkey.current_combo:
            self._reregister_hotkey(new_hotkey)

        # Reload text processor
        self.text_processor.reload()
        self.vocabulary = load_vocabulary()

        # Check if model/engine actually changed
        current = self.model_manager.loaded_models
        need_reload = True
        for key in current:
            if key[0] == new_engine and key[1] == new_model:
                need_reload = False
                break

        if not need_reload:
            print(f"Model unchanged: {new_engine} / {new_model}")
            self.indicator.set_state("done")
            return

        # Model changed — show download window and reload
        self.indicator.set_state("processing")

        from gui.download_window import DownloadWindow
        dl_win = DownloadWindow(self.root, new_model)

        def reload():
            try:
                self.recognizer = self.model_manager.reload(
                    new_engine, new_model, self.device
                )
                dl_win.set_progress(100, "Готово!")
                dl_win.close()
                self._schedule(self.indicator.set_state, "done")
                print(f"Reloaded: {new_engine} / {new_model}")
            except Exception as e:
                print(f"Reload error: {e}")
                dl_win.set_error(f"Ошибка: {e}")
                self._schedule(self.indicator.set_state, "idle")

        threading.Thread(target=reload, daemon=True).start()

    def _reregister_hotkey(self, combo: str):
        self.hotkey.unregister()
        self.hotkey.register(combo)

    # === First run ===

    def _register_hotkey(self):
        """Register global hotkey if not already registered."""
        if self._hotkey_registered:
            return
        combo = self.settings.get("hotkey")
        if combo:
            self.hotkey.register(combo)
            self._hotkey_registered = True
            print(f"Hotkey: {combo}")

    def _check_first_run(self):
        marker = os.path.join(os.path.dirname(self.settings.path),
                              ".first_run_done")
        if not os.path.exists(marker):
            from gui.first_run import FirstRunWizard

            def on_complete():
                with open(marker, "w") as f:
                    f.write("done")
                self.settings.load()
                self._load_current_model()
                self._register_hotkey()  # Register AFTER wizard

            FirstRunWizard(self.root, self.settings, on_complete=on_complete)
        else:
            # No wizard needed — register hotkey immediately
            self._register_hotkey()

    def run(self):
        print(f"Ready: {self.settings.get('engine')} / "
              f"{self.settings.get('model')} / "
              f"{self.settings.get('language')}")
        self.root.after(100, self._check_first_run)
        self.root.mainloop()


def run_console():
    from core.recognizer import load_model, create_recognizer

    settings = SettingsManager()
    engine = settings.get("engine")
    model_name = settings.get("model")
    language = settings.get("language")
    device = detect_device()
    compute_type = get_compute_type(device)

    print(f"Loading: {engine} / {model_name} ({device})...")
    model = load_model(engine, model_name, device, compute_type)
    recognizer = create_recognizer(engine, model)
    vocabulary = load_vocabulary()
    recorder = AudioRecorder()

    print(f"Ready: {language} | {engine} | {model_name}")

    while True:
        try:
            input("\n>>> Enter to record (Ctrl+C to quit)...")
        except KeyboardInterrupt:
            break
        recorder.start()
        print("Recording... (Enter to stop)")
        try:
            input()
        except KeyboardInterrupt:
            recorder.stop()
            break
        audio = recorder.stop()
        duration = len(audio) / 16000
        if duration < 0.5:
            print(f"Too short ({duration:.1f}s)")
            continue
        start = time.time()
        try:
            text = recognizer.transcribe(audio, language=language,
                                         initial_prompt=vocabulary)
        except Exception as e:
            print(f"Error: {e}")
            continue
        elapsed = time.time() - start
        print(f"Result ({elapsed:.1f}s): {text}" if text else "No speech")


def check_single_instance() -> bool:
    """Ensure only one instance runs. Uses a lock file with Windows file lock."""
    lock_path = os.path.join(os.path.dirname(__file__), ".lock")
    try:
        # Try to create/open lock file exclusively
        import msvcrt
        global _lock_file  # Keep reference alive
        _lock_file = open(lock_path, "w")
        msvcrt.locking(_lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
        return True
    except (OSError, IOError):
        print("Приложение уже запущено!")
        return False


if __name__ == "__main__":
    if "--console" in sys.argv:
        run_console()
    else:
        if not check_single_instance():
            sys.exit(1)
        app = App()
        app.run()
