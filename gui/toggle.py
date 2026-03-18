"""Modern toggle switch widget."""

import tkinter as tk


class Toggle(tk.Canvas):
    """iOS-style toggle switch."""

    def __init__(self, parent, variable: tk.BooleanVar = None,
                 command=None, width=40, height=22, **kw):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, cursor="hand2",
                         **kw)
        self.w = width
        self.h = height
        self.var = variable or tk.BooleanVar(value=False)
        self.command = command
        self._on = self.var.get()

        # Colors
        self.c_on = "#4CAF50"
        self.c_off = "#555555"
        self.c_knob = "#FFFFFF"
        self.c_knob_shadow = "#CCCCCC"

        self.bind("<Button-1>", self._click)
        self._draw()
        self.var.trace_add("write", lambda *a: self._draw())

    def _draw(self):
        self.delete("all")
        on = self.var.get()
        r = self.h // 2

        # Track
        color = self.c_on if on else self.c_off
        self.create_oval(0, 0, self.h, self.h, fill=color, outline="")
        self.create_oval(self.w - self.h, 0, self.w, self.h,
                         fill=color, outline="")
        self.create_rectangle(r, 0, self.w - r, self.h,
                              fill=color, outline="")

        # Knob
        pad = 2
        knob_r = r - pad
        if on:
            cx = self.w - r
        else:
            cx = r
        self.create_oval(cx - knob_r, pad, cx + knob_r, self.h - pad,
                         fill=self.c_knob, outline=self.c_knob_shadow)

    def _click(self, e=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()
