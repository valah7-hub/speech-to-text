"""Main overlay window — always-on-top, hold-to-record button."""

import tkinter as tk
import threading
from enum import Enum


class AppState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    INSERTING = "inserting"


STATUS_TEXT = {
    AppState.IDLE: "Готов",
    AppState.RECORDING: "Запись...",
    AppState.PROCESSING: "Обработка...",
    AppState.INSERTING: "Вставка...",
}

STATUS_COLOR = {
    AppState.IDLE: "#888888",
    AppState.RECORDING: "#FF4444",
    AppState.PROCESSING: "#FFD700",
    AppState.INSERTING: "#44FF44",
}


class OverlayWindow:
    """Compact always-on-top overlay with hold-to-record button."""

    def __init__(self, on_record_start=None, on_record_stop=None,
                 on_settings=None):
        """
        Args:
            on_record_start: callback() when button is pressed
            on_record_stop: callback() when button is released,
                            should return in a thread
            on_settings: callback() when settings button is clicked
        """
        self.on_record_start = on_record_start
        self.on_record_stop = on_record_stop
        self.on_settings = on_settings

        self.state = AppState.IDLE
        self.root = tk.Tk()
        self._setup_window()
        self._create_widgets()

    def _setup_window(self):
        self.root.title("Speech-to-Text")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.resizable(True, True)
        self.root.minsize(200, 80)
        self.root.geometry("280x100+50+50")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Dark theme colors
        self.bg = "#2B2B2B"
        self.fg = "#E0E0E0"
        self.root.configure(bg=self.bg)

    def _create_widgets(self):
        # Main frame
        frame = tk.Frame(self.root, bg=self.bg)
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Record button
        self.btn_record = tk.Button(
            frame,
            text="Удерживайте для записи",
            font=("Segoe UI", 11),
            bg="#3C3C3C",
            fg=self.fg,
            activebackground="#555555",
            activeforeground=self.fg,
            relief=tk.FLAT,
            cursor="hand2",
        )
        self.btn_record.pack(fill=tk.X, pady=(2, 4))
        self.btn_record.bind("<ButtonPress-1>", self._on_press)
        self.btn_record.bind("<ButtonRelease-1>", self._on_release)

        # Streaming text preview (hidden by default)
        self.lbl_stream = tk.Label(
            frame, text="", font=("Segoe UI", 9),
            fg="#777777", bg="#1E1E1E", anchor=tk.W,
            wraplength=260, justify=tk.LEFT, padx=4, pady=2,
        )
        # Not packed until streaming starts

        # Bottom row: status + settings
        bottom = tk.Frame(frame, bg=self.bg)
        bottom.pack(fill=tk.X)

        # Status indicator (colored dot + text)
        self.status_dot = tk.Canvas(bottom, width=10, height=10,
                                     bg=self.bg, highlightthickness=0)
        self.status_dot.pack(side=tk.LEFT, padx=(0, 4))
        self._dot = self.status_dot.create_oval(1, 1, 9, 9,
                                                 fill="#888888", outline="")

        self.lbl_status = tk.Label(
            bottom, text="Готов", font=("Segoe UI", 9),
            fg="#888888", bg=self.bg, anchor=tk.W,
        )
        self.lbl_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Privacy indicator
        self.lbl_privacy = tk.Label(
            bottom, text="Локально", font=("Segoe UI", 7),
            fg="#666666", bg=self.bg,
        )
        self.lbl_privacy.pack(side=tk.RIGHT, padx=(4, 0))

        # Settings button — larger, more visible
        self.btn_settings = tk.Button(
            bottom, text="⚙ Настройки", font=("Segoe UI", 9),
            bg="#3C3C3C", fg="#CCCCCC", relief=tk.FLAT,
            activebackground="#555555", activeforeground="#FFFFFF",
            cursor="hand2", padx=6,
            command=self._on_settings_click,
        )
        self.btn_settings.pack(side=tk.RIGHT, padx=(4, 0))

    def _on_press(self, event):
        if self.state != AppState.IDLE:
            return
        self.set_state(AppState.RECORDING)
        if self.on_record_start:
            self.on_record_start()

    def _on_release(self, event):
        if self.state != AppState.RECORDING:
            return
        self.set_state(AppState.PROCESSING)
        if self.on_record_stop:
            # Run transcription in background thread
            thread = threading.Thread(target=self.on_record_stop, daemon=True)
            thread.start()

    def _on_settings_click(self):
        if self.on_settings:
            self.on_settings()

    def _on_close(self):
        self.root.destroy()

    def set_state(self, state: AppState):
        """Update UI state."""
        self.state = state
        color = STATUS_COLOR[state]
        text = STATUS_TEXT[state]

        self.lbl_status.configure(text=text, fg=color)
        self.status_dot.itemconfig(self._dot, fill=color)

        if state == AppState.RECORDING:
            self.btn_record.configure(text="Запись...", bg="#5C2020")
            self._pulse_recording()
        elif state == AppState.PROCESSING:
            self.btn_record.configure(text="Обработка...", bg="#4A4A20")
        elif state == AppState.IDLE:
            self.btn_record.configure(
                text="Удерживайте для записи", bg="#3C3C3C"
            )
        elif state == AppState.INSERTING:
            self.btn_record.configure(text="Вставка...", bg="#204A20")

    def _pulse_recording(self):
        """Blink the status dot while recording."""
        if self.state != AppState.RECORDING:
            return
        current = self.status_dot.itemcget(self._dot, "fill")
        new_color = "#FF4444" if current == "#2B2B2B" else "#2B2B2B"
        self.status_dot.itemconfig(self._dot, fill=new_color)
        self.root.after(500, self._pulse_recording)

    def show_stream_text(self, text: str):
        """Update the streaming preview with partial text."""
        if text:
            self.lbl_stream.configure(text=text, fg="#777777")
            self.lbl_stream.pack(fill=tk.X, pady=(0, 4))
            # Auto-resize overlay if needed
            self.root.update_idletasks()
        else:
            self.lbl_stream.pack_forget()

    def show_stream_final(self, text: str):
        """Show final streaming text briefly (in white)."""
        if text:
            self.lbl_stream.configure(text=text, fg=self.fg)
        self.root.after(2000, self._hide_stream)

    def _hide_stream(self):
        self.lbl_stream.configure(text="")
        self.lbl_stream.pack_forget()

    def set_result(self, text: str, elapsed: float = 0):
        """Show result briefly, then return to idle."""
        self._hide_stream()
        if elapsed > 0:
            status = f"Готово ({elapsed:.1f} сек)"
        else:
            status = "Готово!"
        self.lbl_status.configure(text=status, fg="#44FF44")
        self.status_dot.itemconfig(self._dot, fill="#44FF44")
        self.btn_record.configure(text="Удерживайте для записи", bg="#3C3C3C")
        # Return to idle after 2 sec
        self.root.after(2000, lambda: self.set_state(AppState.IDLE))

    def set_error(self, message: str):
        """Show error message briefly."""
        self._hide_stream()
        self.lbl_status.configure(text=message, fg="#FF6666")
        self.status_dot.itemconfig(self._dot, fill="#FF6666")
        self.btn_record.configure(text="Удерживайте для записи", bg="#3C3C3C")
        self.root.after(3000, lambda: self.set_state(AppState.IDLE))

    def schedule(self, callback, *args):
        """Schedule a callback on the main tkinter thread."""
        self.root.after(0, callback, *args)

    def get_hwnd(self) -> int:
        """Get the HWND of the overlay window."""
        self.root.update_idletasks()
        return int(self.root.wm_frame(), 16)

    def run(self):
        """Start the tkinter main loop."""
        self.root.mainloop()
