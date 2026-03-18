"""System tray icon using pystray."""

import threading

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


def _create_icon_image(color: str = "#4488CC", size: int = 64) -> "Image":
    """Create a simple microphone-like icon."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Circle background
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    # Mic shape (simple rectangle + rounded top)
    cx, cy = size // 2, size // 2
    w, h = size // 5, size // 3
    draw.rounded_rectangle(
        [cx - w, cy - h, cx + w, cy + h // 2],
        radius=w, fill="white",
    )
    # Stand line
    draw.line([cx, cy + h // 2, cx, cy + h], fill="white", width=2)
    draw.line([cx - w, cy + h, cx + w, cy + h], fill="white", width=2)
    return img


class TrayIcon:
    """System tray icon with context menu."""

    def __init__(self, on_settings=None, on_history=None,
                 on_files=None, on_show=None, on_exit=None):
        if not TRAY_AVAILABLE:
            self._icon = None
            return

        self.on_settings = on_settings
        self.on_history = on_history
        self.on_files = on_files
        self.on_show = on_show
        self.on_exit = on_exit

        menu = pystray.Menu(
            pystray.MenuItem("Показать", self._on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Настройки", self._on_settings),
            pystray.MenuItem("История", self._on_history),
            pystray.MenuItem("Файлы", self._on_files),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self._on_exit),
        )

        self._icon = pystray.Icon(
            "speech-to-text",
            icon=_create_icon_image(),
            title="Speech-to-Text",
            menu=menu,
        )

    def start(self):
        """Start tray icon in a background thread."""
        if self._icon is None:
            return
        thread = threading.Thread(target=self._icon.run, daemon=True)
        thread.start()

    def stop(self):
        """Stop and remove tray icon."""
        if self._icon:
            self._icon.stop()

    def set_recording(self, recording: bool):
        """Update icon color to show recording state."""
        if not self._icon:
            return
        color = "#FF4444" if recording else "#4488CC"
        self._icon.icon = _create_icon_image(color)

    def _on_show(self, icon=None, item=None):
        if self.on_show:
            self.on_show()

    def _on_settings(self, icon=None, item=None):
        if self.on_settings:
            self.on_settings()

    def _on_history(self, icon=None, item=None):
        if self.on_history:
            self.on_history()

    def _on_files(self, icon=None, item=None):
        if self.on_files:
            self.on_files()

    def _on_exit(self, icon=None, item=None):
        if self.on_exit:
            self.on_exit()
