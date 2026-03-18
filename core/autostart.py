"""Windows autostart — add/remove from Startup folder."""

import os
import sys


def _get_shortcut_path() -> str:
    startup = os.path.join(os.environ.get("APPDATA", ""),
                           r"Microsoft\Windows\Start Menu\Programs\Startup")
    return os.path.join(startup, "Speech-to-Text.bat")


def is_autostart_enabled() -> bool:
    return os.path.exists(_get_shortcut_path())


def enable_autostart():
    """Create a .bat file in Startup folder."""
    bat_path = _get_shortcut_path()
    python = sys.executable
    app_py = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "app.py"))
    app_dir = os.path.dirname(app_py)

    content = f'@echo off\ncd /d "{app_dir}"\nstart "" "{python}" "{app_py}"\n'
    os.makedirs(os.path.dirname(bat_path), exist_ok=True)
    with open(bat_path, "w") as f:
        f.write(content)


def disable_autostart():
    """Remove from Startup."""
    bat_path = _get_shortcut_path()
    if os.path.exists(bat_path):
        os.remove(bat_path)
