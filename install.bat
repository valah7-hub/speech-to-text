@echo off
chcp 65001 >nul
title Speech-to-Text — Установка

echo.
echo ══════════════════════════════════════════════
echo   Speech-to-Text v1.9.0 — Установка
echo ══════════════════════════════════════════════
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo.
    echo Скачайте Python с https://python.org/downloads
    echo При установке отметьте "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [1/4] Python найден:
python --version
echo.

:: Install base dependencies
echo [2/4] Установка базовых зависимостей...
echo       sounddevice, numpy, pyperclip, keyboard, Pillow, pystray...
python -m pip install sounddevice numpy pyperclip pyautogui keyboard pywin32 Pillow pystray mouse --quiet
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости
    pause
    exit /b 1
)
echo       OK
echo.

:: Install speech engine
echo [3/4] Установка движка распознавания (faster-whisper)...
echo       Это может занять несколько минут...
python -m pip install faster-whisper --quiet
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить faster-whisper
    pause
    exit /b 1
)
echo       OK
echo.

:: Check GPU
echo [4/4] Проверка GPU...
python -c "import torch; print('  GPU: ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else '  CPU (без GPU)')" 2>nul
if errorlevel 1 (
    echo       GPU не обнаружен или PyTorch без CUDA.
    echo.
    echo       Хотите установить поддержку GPU? (NVIDIA, ~2.5 GB)
    choice /c YN /m "      Установить CUDA-версию PyTorch"
    if errorlevel 2 goto skip_gpu
    echo       Скачивание PyTorch + CUDA...
    python -m pip install torch --index-url https://download.pytorch.org/whl/cu126 --quiet
    if errorlevel 1 (
        echo       [!] Не удалось установить CUDA. Продолжаем без GPU.
    ) else (
        echo       GPU поддержка установлена!
    )
)
:skip_gpu

echo.
echo ══════════════════════════════════════════════
echo   Установка завершена!
echo.
echo   Запуск: дважды кликните start.vbs
echo   Или:    python app.py
echo.
echo   При первом запуске выберите модель
echo   (она скачается автоматически с Hugging Face)
echo ══════════════════════════════════════════════
echo.
pause
