"""Tooltip widget — shows hint text on hover."""

import tkinter as tk


class Tooltip:
    """Shows a tooltip when hovering over a widget."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip_window: tk.Toplevel | None = None
        self._after_id = None

        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event):
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, event):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        if self._tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#FFFFDD", foreground="#333333",
            relief=tk.SOLID, borderwidth=1,
            font=("Segoe UI", 9), wraplength=300,
            padx=6, pady=4,
        )
        label.pack()

    def _hide(self):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None
