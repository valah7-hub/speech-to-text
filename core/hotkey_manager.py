"""Global hotkey manager — keyboard combos + mouse buttons."""

import threading
import keyboard

try:
    import mouse as mouse_lib
    MOUSE_AVAILABLE = True
except ImportError:
    MOUSE_AVAILABLE = False

# Mouse button names that can be used as hotkeys
MOUSE_BUTTONS = {"mouse_middle", "mouse_side1", "mouse_side2",
                 "mouse_x1", "mouse_x2", "mouse_right"}


class HotkeyManager:
    """Register global hotkeys (keyboard or mouse) for hold-to-record."""

    def __init__(self, on_press=None, on_release=None):
        self.on_press = on_press
        self.on_release = on_release
        self._current_combo: str = ""
        self._hook = None
        self._mouse_hook = None
        self._pressed = False
        self._is_mouse = False

    def register(self, combo: str):
        """Register a hotkey.

        Supports keyboard combos: 'ctrl+space', 'f9', 'ctrl+shift+r'
        Supports mouse buttons: 'mouse_middle', 'mouse_side1', 'mouse_side2'
        """
        self.unregister()
        self._current_combo = combo.lower().strip()
        self._pressed = False

        # Check if it's a mouse button
        if self._current_combo in MOUSE_BUTTONS:
            self._is_mouse = True
            self._register_mouse(self._current_combo)
        else:
            self._is_mouse = False
            self._register_keyboard(self._current_combo)

    def _register_keyboard(self, combo: str):
        """Register keyboard combo."""
        keys = [k.strip() for k in combo.split("+")]
        self._target_keys = set(keys)
        self._hook = keyboard.hook(self._on_key_event, suppress=False)

    def _register_mouse(self, button: str):
        """Register mouse button."""
        if not MOUSE_AVAILABLE:
            print(f"Warning: mouse library not installed, can't use {button}")
            return

        # Map our names to mouse library names
        btn_map = {
            "mouse_middle": "middle",
            "mouse_side1": "x",
            "mouse_side2": "x2",
            "mouse_x1": "x",
            "mouse_x2": "x2",
            "mouse_right": "right",
        }
        btn = btn_map.get(button, "middle")

        def on_mouse_event(event):
            if not isinstance(event, (mouse_lib.ButtonEvent,)):
                return
            if event.button != btn:
                return

            if event.event_type == "down" and not self._pressed:
                self._pressed = True
                if self.on_press:
                    threading.Thread(target=self.on_press, daemon=True).start()
            elif event.event_type == "up" and self._pressed:
                self._pressed = False
                if self.on_release:
                    threading.Thread(target=self.on_release, daemon=True).start()

        self._mouse_hook = mouse_lib.hook(on_mouse_event)

    def unregister(self):
        if self._hook is not None:
            keyboard.unhook(self._hook)
            self._hook = None
        if self._mouse_hook is not None and MOUSE_AVAILABLE:
            mouse_lib.unhook(self._mouse_hook)
            self._mouse_hook = None
        self._pressed = False
        self._current_combo = ""

    def _on_key_event(self, event: keyboard.KeyboardEvent):
        if not self._target_keys:
            return
        all_pressed = all(keyboard.is_pressed(k) for k in self._target_keys)

        if all_pressed and not self._pressed:
            self._pressed = True
            if self.on_press:
                threading.Thread(target=self.on_press, daemon=True).start()
        elif not all_pressed and self._pressed:
            self._pressed = False
            if self.on_release:
                threading.Thread(target=self.on_release, daemon=True).start()

    @property
    def current_combo(self) -> str:
        return self._current_combo

    @staticmethod
    def get_available_mouse_buttons() -> list[str]:
        """Get list of available mouse button names for UI."""
        if not MOUSE_AVAILABLE:
            return []
        return [
            "mouse_middle — Средняя кнопка (колёсико)",
            "mouse_side1 — Боковая кнопка 1 (назад)",
            "mouse_side2 — Боковая кнопка 2 (вперёд)",
        ]

    @staticmethod
    def capture_next_combo(callback, timeout: float = 5.0):
        """Capture next key/mouse combo. Calls callback(combo_string)."""
        captured = {"combo": None}

        def on_key(event: keyboard.KeyboardEvent):
            if event.event_type != "down":
                return
            modifiers = []
            if keyboard.is_pressed("ctrl"):
                modifiers.append("ctrl")
            if keyboard.is_pressed("alt"):
                modifiers.append("alt")
            if keyboard.is_pressed("shift"):
                modifiers.append("shift")
            key = event.name.lower()
            if key in ("ctrl", "alt", "shift", "left ctrl", "right ctrl",
                        "left alt", "right alt", "left shift", "right shift"):
                return
            parts = modifiers + [key]
            captured["combo"] = "+".join(parts)
            keyboard.unhook(kb_hook)
            if mouse_hook and MOUSE_AVAILABLE:
                mouse_lib.unhook(mouse_hook)
            timer.cancel()
            if callback:
                callback(captured["combo"])

        mouse_hook = None

        def on_mouse(event):
            if not isinstance(event, mouse_lib.ButtonEvent):
                return
            if event.event_type != "down":
                return
            btn_map = {"middle": "mouse_middle", "x": "mouse_side1",
                       "x2": "mouse_side2", "right": "mouse_right"}
            name = btn_map.get(event.button)
            if name:
                captured["combo"] = name
                keyboard.unhook(kb_hook)
                if MOUSE_AVAILABLE:
                    mouse_lib.unhook(on_mouse)
                timer.cancel()
                if callback:
                    callback(captured["combo"])

        kb_hook = keyboard.hook(on_key, suppress=False)
        if MOUSE_AVAILABLE:
            mouse_hook = mouse_lib.hook(on_mouse)

        def cancel():
            if captured["combo"] is None:
                try:
                    keyboard.unhook(kb_hook)
                except Exception:
                    pass
                if mouse_hook and MOUSE_AVAILABLE:
                    try:
                        mouse_lib.unhook(mouse_hook)
                    except Exception:
                        pass
                if callback:
                    callback(None)

        timer = threading.Timer(timeout, cancel)
        timer.daemon = True
        timer.start()
