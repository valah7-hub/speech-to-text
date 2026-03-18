"""Build standalone EXE for Speech-to-Text.

Usage:  python build.py
Output: dist/SpeechToText/SpeechToText.exe
"""

import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")
NAME = "SpeechToText"


def main():
    print("=== Building Speech-to-Text EXE ===\n")

    # Ensure PyInstaller is installed
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])

    # Clean previous build
    for d in [DIST, BUILD]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)

    # Collect hidden imports that PyInstaller misses
    hidden = [
        "faster_whisper",
        "ctranslate2",
        "huggingface_hub",
        "sounddevice",
        "numpy",
        "keyboard",
        "pyperclip",
        "pyautogui",
        "pystray",
        "PIL",
        "PIL._tkinter_finder",
        "win32api",
        "win32con",
        "win32gui",
        "win32process",
        "win32clipboard",
        "pywintypes",
    ]

    # Exclude heavy optional packages to keep EXE smaller
    excludes = [
        "whisper",        # openai-whisper (torch is huge)
        "torch",          # PyTorch — will be downloaded on demand if needed
        "torchaudio",
        "torchvision",
        "whisperx",
        "matplotlib",
        "scipy",
        "pandas",
        "pytest",
        "IPython",
        "notebook",
        "jupyter",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", NAME,
        "--onedir",            # folder mode (faster startup than --onefile)
        # "--windowed",          # no console window (disabled for debug)
        "--noconfirm",         # overwrite without asking
        "--clean",             # clean cache
        # Icon (if exists)
        # "--icon", os.path.join(ROOT, "icon.ico"),
    ]

    for h in hidden:
        cmd.extend(["--hidden-import", h])

    for e in excludes:
        cmd.extend(["--exclude-module", e])

    # Add data files
    cmd.extend(["--add-data", f"{os.path.join(ROOT, 'core')}:core"])
    cmd.extend(["--add-data", f"{os.path.join(ROOT, 'gui')}:gui"])
    cmd.extend(["--add-data", f"{os.path.join(ROOT, 'VERSION')}:."])
    cmd.extend(["--add-data", f"{os.path.join(ROOT, 'requirements.txt')}:."])

    # Add locale files
    locale_dir = os.path.join(ROOT, "locale")
    if os.path.exists(locale_dir):
        cmd.extend(["--add-data", f"{locale_dir}:locale"])

    # Entry point
    cmd.append(os.path.join(ROOT, "app.py"))

    print(f"Running: {' '.join(cmd[-5:])}")
    print("This may take 2-5 minutes...\n")

    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode != 0:
        print("\n*** Build FAILED ***")
        sys.exit(1)

    # Check output
    exe_path = os.path.join(DIST, NAME, f"{NAME}.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)

        # Calculate total folder size
        total = 0
        for dp, dn, fns in os.walk(os.path.join(DIST, NAME)):
            for f in fns:
                total += os.path.getsize(os.path.join(dp, f))
        total_mb = total / (1024 * 1024)

        print(f"\n=== Build SUCCESS ===")
        print(f"EXE:    {exe_path}")
        print(f"EXE:    {size_mb:.1f} MB")
        print(f"Folder: {total_mb:.1f} MB")
        print(f"\nTo run: {exe_path}")
        print(f"To distribute: zip the '{os.path.join(DIST, NAME)}' folder")
    else:
        print("\n*** EXE not found after build ***")
        sys.exit(1)


if __name__ == "__main__":
    main()
