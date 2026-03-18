"""Check for updates from GitHub and apply them."""

import os
import json
import shutil
import zipfile
import tempfile
import threading

try:
    import urllib.request
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

REPO = "valah7-hub/speech-to-text"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
VERSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION")


def get_current_version() -> str:
    try:
        with open(VERSION_FILE) as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"


def check_update() -> dict | None:
    """Check GitHub for a newer version.

    Returns {"version": "1.10.0", "url": "...", "notes": "..."} or None.
    """
    if not HAS_URLLIB:
        return None
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": "STT"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        remote_tag = data.get("tag_name", "").lstrip("v")
        current = get_current_version()
        if remote_tag and remote_tag != current:
            zip_url = data.get("zipball_url", "")
            notes = data.get("body", "")[:200]
            return {"version": remote_tag, "url": zip_url, "notes": notes}
    except Exception:
        pass
    return None


def download_and_apply(zip_url: str, on_progress=None) -> bool:
    """Download update zip from GitHub and replace files."""
    if not zip_url:
        return False

    app_dir = os.path.dirname(os.path.dirname(__file__))
    tmp_dir = tempfile.mkdtemp(prefix="stt_update_")

    try:
        # Download
        if on_progress:
            on_progress("Скачивание обновления...")
        zip_path = os.path.join(tmp_dir, "update.zip")
        urllib.request.urlretrieve(zip_url, zip_path)

        # Extract
        if on_progress:
            on_progress("Распаковка...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_dir)

        # Find the extracted folder (GitHub adds a prefix)
        extracted = None
        for name in os.listdir(tmp_dir):
            path = os.path.join(tmp_dir, name)
            if os.path.isdir(path) and name != "__pycache__":
                extracted = path
                break

        if not extracted:
            return False

        # Copy new files over old ones (skip settings, history, etc.)
        skip = {"settings.json", "history.json", "replacements.json",
                "vocabulary.txt", ".lock", ".first_run_done",
                "__pycache__", "dist", "build", ".git"}

        if on_progress:
            on_progress("Обновление файлов...")

        for item in os.listdir(extracted):
            if item in skip:
                continue
            src = os.path.join(extracted, item)
            dst = os.path.join(app_dir, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        if on_progress:
            on_progress("Готово! Перезапустите приложение.")
        return True

    except Exception as e:
        if on_progress:
            on_progress(f"Ошибка: {e}")
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
