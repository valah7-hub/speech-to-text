"""Floating indicator — pill with spectograph bars reacting to voice."""

import tkinter as tk
import math
import random


class FloatingIndicator:
    """Pill with 5 spectograph bars instead of dots.

    Bars react to audio level like a mini equalizer.
    """

    BG = {
        "idle": "#3A3A3A",
        "recording": "#5A2020",
        "processing": "#5A4A10",
        "done": "#204A20",
    }
    WIDTH = 76
    HEIGHT = 28
    NUM_BARS = 7
    BAR_W = 3
    BAR_GAP = 2
    BAR_MIN_H = 2
    BAR_MAX_H = 20

    def __init__(self, parent: tk.Tk, x: int = 100, y: int = 100,
                 on_right_click=None, on_left_click=None):
        self.parent = parent
        self.on_right_click = on_right_click
        self.on_left_click = on_left_click
        self._state = "idle"
        self._anim_active = False
        self._audio_level = 0.0
        self._smooth_level = 0.0
        self._phase = 0.0
        self._bar_heights = [0.0] * self.NUM_BARS

        # Window
        self.win = tk.Toplevel(parent)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)

        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()
        x = max(0, min(x, screen_w - self.WIDTH))
        y = max(0, min(y, screen_h - self.HEIGHT - 50))

        self.win.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

        # Transparent window background — only rounded shape visible
        self._tr = "#01FF01"  # Unique green, not used anywhere
        self.win.configure(bg=self._tr)
        self.win.wm_attributes("-transparentcolor", self._tr)

        # Canvas with transparent bg
        self.canvas = tk.Canvas(
            self.win, width=self.WIDTH, height=self.HEIGHT,
            bg=self._tr, highlightthickness=0, cursor="hand2",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Rounded pill shape — this is the only visible part
        self._bg = self._rounded_rect(
            0, 0, self.WIDTH, self.HEIGHT,
            radius=self.HEIGHT // 2,
            fill=self.BG["idle"], outline="#555555",
        )

        # Spectograph bars
        self._bars = []
        total_w = self.NUM_BARS * self.BAR_W + (self.NUM_BARS - 1) * self.BAR_GAP
        start_x = (self.WIDTH - total_w) / 2
        cy = self.HEIGHT / 2

        for i in range(self.NUM_BARS):
            bx = start_x + i * (self.BAR_W + self.BAR_GAP)
            h = self.BAR_MIN_H
            bar = self.canvas.create_rectangle(
                bx, cy - h / 2, bx + self.BAR_W, cy + h / 2,
                fill="#666666", outline="",
            )
            self._bars.append(bar)

        # Drag
        self._dsx = 0
        self._dsy = 0
        self._dragged = False
        self.canvas.bind("<ButtonPress-1>", self._p1)
        self.canvas.bind("<B1-Motion>", self._m1)
        self.canvas.bind("<ButtonRelease-1>", self._r1)
        self.canvas.bind("<ButtonPress-3>", self._p3)

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kw):
        r = min(radius, (y2 - y1) // 2)
        pts = []
        for a in range(90, 181, 10):
            pts += [x1 + r + r * math.cos(math.radians(a)),
                    y1 + r - r * math.sin(math.radians(a))]
        for a in range(180, 271, 10):
            pts += [x1 + r + r * math.cos(math.radians(a)),
                    y2 - r - r * math.sin(math.radians(a))]
        for a in range(270, 361, 10):
            pts += [x2 - r + r * math.cos(math.radians(a)),
                    y2 - r - r * math.sin(math.radians(a))]
        for a in range(0, 91, 10):
            pts += [x2 - r + r * math.cos(math.radians(a)),
                    y1 + r - r * math.sin(math.radians(a))]
        return self.canvas.create_polygon(pts, smooth=False, **kw)

    # Drag
    def _p1(self, e):
        self._dsx, self._dsy, self._dragged = e.x_root, e.y_root, False

    def _m1(self, e):
        if abs(e.x_root - self._dsx) > 3 or abs(e.y_root - self._dsy) > 3:
            self._dragged = True
        if self._dragged:
            self.win.geometry(f"+{self.win.winfo_x() + e.x_root - self._dsx}"
                              f"+{self.win.winfo_y() + e.y_root - self._dsy}")
            self._dsx, self._dsy = e.x_root, e.y_root

    def _r1(self, e):
        if not self._dragged and self.on_left_click:
            self.on_left_click(e)

    def _p3(self, e):
        if self.on_right_click:
            self.on_right_click(e)

    # --- State ---

    def set_state(self, state: str):
        self._state = state
        bg = self.BG.get(state, self.BG["idle"])
        self.canvas.itemconfig(self._bg, fill=bg)
        # Don't change win/canvas bg — they stay transparent

        if state in ("recording", "processing"):
            if not self._anim_active:
                self._anim_active = True
                self._phase = 0.0
                self._smooth_level = 0.0
                self._bar_heights = [0.0] * self.NUM_BARS
                self._animate()
        else:
            self._anim_active = False
            self._draw_idle()

        if state == "done":
            self.win.after(1500, lambda: self.set_state("idle"))

    def set_audio_level(self, level: float):
        self._audio_level = max(0.0, min(1.0, level))

    def _draw_idle(self):
        total_w = self.NUM_BARS * self.BAR_W + (self.NUM_BARS - 1) * self.BAR_GAP
        sx = (self.WIDTH - total_w) / 2
        cy = self.HEIGHT / 2
        h = self.BAR_MIN_H
        color = "#88DD88" if self._state == "done" else "#555555"
        for i, bar in enumerate(self._bars):
            bx = sx + i * (self.BAR_W + self.BAR_GAP)
            self.canvas.coords(bar, bx, cy - h / 2, bx + self.BAR_W, cy + h / 2)
            self.canvas.itemconfig(bar, fill=color)

    def _animate(self):
        if not self._anim_active:
            return

        self._phase += 0.2
        self._smooth_level += (self._audio_level - self._smooth_level) * 0.4
        lv = self._smooth_level

        total_w = self.NUM_BARS * self.BAR_W + (self.NUM_BARS - 1) * self.BAR_GAP
        sx = (self.WIDTH - total_w) / 2
        cy = self.HEIGHT / 2
        rec = self._state == "recording"

        # Per-bar frequency weights (middle bars react more)
        weights = [0.5, 0.7, 1.0, 1.0, 1.0, 0.7, 0.5]
        if self.NUM_BARS != 7:
            weights = [1.0] * self.NUM_BARS

        for i, bar in enumerate(self._bars):
            bx = sx + i * (self.BAR_W + self.BAR_GAP)
            w = weights[i] if i < len(weights) else 1.0

            if rec:
                # Each bar has different phase = different "frequency"
                freq = 1.2 + i * 0.4
                wave = math.sin(self._phase * freq + i * 0.9)
                jitter = math.sin(self._phase * 3.1 + i * 2.3) * 0.15

                # Height proportional to audio level
                target_h = self.BAR_MIN_H + (self.BAR_MAX_H - self.BAR_MIN_H) * lv * w * (0.4 + 0.6 * abs(wave) + jitter)
                target_h = max(self.BAR_MIN_H, min(self.BAR_MAX_H, target_h))

                if lv < 0.03:
                    target_h = self.BAR_MIN_H + abs(wave) * 1.5
            else:
                wave = math.sin(self._phase * 0.6 + i * 0.5)
                target_h = 5 + wave * 3

            # Smooth — faster response when loud
            speed = 0.5 if lv > 0.1 else 0.3
            self._bar_heights[i] += (target_h - self._bar_heights[i]) * speed
            h = self._bar_heights[i]

            self.canvas.coords(bar, bx, cy - h / 2, bx + self.BAR_W, cy + h / 2)

            # Color
            if rec:
                ratio = h / self.BAR_MAX_H
                # White when loud, dim when quiet
                v = int(140 + ratio * 115)
                v = min(255, v)
                self.canvas.itemconfig(bar, fill=f"#{v:02x}{v:02x}{v:02x}")
            else:
                v = int(170 + (h / 10) * 60)
                self.canvas.itemconfig(bar, fill=f"#{min(255,v):02x}{min(255,v):02x}40")

        self.win.after(30, self._animate)

    def get_position(self) -> tuple[int, int]:
        return self.win.winfo_x(), self.win.winfo_y()

    def destroy(self):
        self._anim_active = False
        self.win.destroy()
