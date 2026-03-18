"""Build script for PyInstaller — creates portable exe."""

import PyInstaller.__main__
import os
import sys

# Get paths
app_dir = os.path.dirname(os.path.abspath(__file__))

args = [
    os.path.join(app_dir, "app.py"),
    "--name=Speech-to-Text",
    "--onedir",               # Folder with exe (smaller than onefile)
    "--noconsole",            # No console window (like pythonw)
    "--noconfirm",            # Overwrite without asking

    # Include all our modules
    "--add-data=core;core",
    "--add-data=gui;gui",
    "--add-data=VERSION;.",
    "--add-data=README.md;.",

    # Hidden imports that PyInstaller may miss
    "--hidden-import=sounddevice",
    "--hidden-import=numpy",
    "--hidden-import=pyperclip",
    "--hidden-import=keyboard",
    "--hidden-import=mouse",
    "--hidden-import=pystray",
    "--hidden-import=PIL",
    "--hidden-import=PIL._tkinter_finder",
    "--hidden-import=faster_whisper",
    "--hidden-import=ctranslate2",
    "--hidden-import=huggingface_hub",
    "--hidden-import=tokenizers",

    # Exclude heavy CUDA libs (user downloads if needed)
    "--exclude-module=torch.cuda",
    "--exclude-module=triton",
    "--exclude-module=caffe2",

    # Icon (would need an .ico file)
    # "--icon=icon.ico",
]

print("Building Speech-to-Text.exe...")
print(f"Source: {app_dir}")
print()

PyInstaller.__main__.run(args)

print()
print("Done! Check dist/Speech-to-Text/")
