#!/bin/bash
# Auto-commit: bump version, describe changes, commit, push
cd "$(dirname "$0")/.." || exit 0

# Check if there are changes
if git diff --quiet HEAD 2>/dev/null && \
   git diff --cached --quiet 2>/dev/null && \
   [ -z "$(git ls-files --others --exclude-standard)" ]; then
    exit 0
fi

# Read current version
VERSION=$(cat VERSION 2>/dev/null | tr -d '[:space:]')
[ -z "$VERSION" ] && VERSION="1.9.0"
MAJOR=$(echo "$VERSION" | cut -d. -f1)
MINOR=$(echo "$VERSION" | cut -d. -f2)
PATCH=$(echo "$VERSION" | cut -d. -f3)
NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"

# Collect changed files
CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null; git ls-files --others --exclude-standard)

# Build detailed description from diffs
DETAILS=""
for f in $CHANGED_FILES; do
    [ ! -f "$f" ] && continue
    case "$f" in
        core/text_inserter.py)
            # Check what changed
            if git diff HEAD -- "$f" 2>/dev/null | grep -q "backspace\|append_diff\|NEVER"; then
                DETAILS="$DETAILS\n- text_inserter: больше не стирает существующий текст"
            elif git diff HEAD -- "$f" 2>/dev/null | grep -q "clipboard\|restore"; then
                DETAILS="$DETAILS\n- text_inserter: исправлено сохранение буфера обмена"
            else
                DETAILS="$DETAILS\n- text_inserter: обновлена вставка текста"
            fi
            ;;
        core/recognizer.py)
            DETAILS="$DETAILS\n- recognizer: обновлены движки распознавания"
            ;;
        core/stream_recognizer.py)
            if git diff HEAD -- "$f" 2>/dev/null | grep -q "audio_level\|rms"; then
                DETAILS="$DETAILS\n- стриминг: улучшена чувствительность к голосу"
            else
                DETAILS="$DETAILS\n- стриминг: обновлено распознавание в реальном времени"
            fi
            ;;
        core/settings_manager.py)
            DETAILS="$DETAILS\n- настройки: обновлены параметры"
            ;;
        core/gpu_detector.py)
            DETAILS="$DETAILS\n- GPU: обновлена детекция устройств"
            ;;
        core/hotkey_manager.py)
            DETAILS="$DETAILS\n- хоткей: обновлено управление горячими клавишами"
            ;;
        core/vad_listener.py)
            DETAILS="$DETAILS\n- VAD: обновлено автопрослушивание"
            ;;
        core/voice_commands.py)
            DETAILS="$DETAILS\n- голосовые команды: обновлены"
            ;;
        core/text_processor.py)
            DETAILS="$DETAILS\n- обработка текста: обновлена"
            ;;
        core/updater.py)
            DETAILS="$DETAILS\n- обновление: добавлено/исправлено автообновление"
            ;;
        core/autostart.py)
            DETAILS="$DETAILS\n- автозапуск: обновлён"
            ;;
        gui/indicator.py)
            if git diff HEAD -- "$f" 2>/dev/null | grep -q "spectro\|BAR\|_bar"; then
                DETAILS="$DETAILS\n- индикатор: обновлён спектрограф"
            else
                DETAILS="$DETAILS\n- индикатор: обновлён дизайн"
            fi
            ;;
        gui/settings_window.py)
            if git diff HEAD -- "$f" 2>/dev/null | grep -q "pady\|spacing\|section"; then
                DETAILS="$DETAILS\n- настройки: улучшены отступы и разметка"
            elif git diff HEAD -- "$f" 2>/dev/null | grep -q "update\|version"; then
                DETAILS="$DETAILS\n- настройки: добавлена проверка обновлений"
            else
                DETAILS="$DETAILS\n- настройки: обновлён интерфейс"
            fi
            ;;
        gui/download_window.py)
            DETAILS="$DETAILS\n- загрузка: обновлён прогресс скачивания"
            ;;
        gui/first_run.py)
            DETAILS="$DETAILS\n- мастер настройки: обновлён"
            ;;
        app.py)
            if git diff HEAD -- "$f" 2>/dev/null | grep -q "DPI\|dpi"; then
                DETAILS="$DETAILS\n- app: исправлена чёткость на HiDPI"
            elif git diff HEAD -- "$f" 2>/dev/null | grep -q "single_instance\|lock"; then
                DETAILS="$DETAILS\n- app: защита от двойного запуска"
            else
                DETAILS="$DETAILS\n- app: обновлена логика приложения"
            fi
            ;;
        README.md|CHANGELOG.md|VERSION)
            ;; # Skip docs — they're auto-updated
        scripts/*)
            ;; # Skip scripts
        *.py)
            name=$(basename "$f" .py)
            DETAILS="$DETAILS\n- $name: обновлён"
            ;;
    esac
done

# Fallback if no details
if [ -z "$DETAILS" ]; then
    STAT=$(git diff --stat HEAD 2>/dev/null | tail -1 | sed 's/^ *//')
    DETAILS="\n- $STAT"
fi

# First line of commit message
TITLE="v${NEW_VERSION}"

# Update VERSION
echo "$NEW_VERSION" > VERSION

# Update README version
sed -i "s/Speech-to-Text v[0-9]*\.[0-9]*\.[0-9]*/Speech-to-Text v${NEW_VERSION}/" README.md 2>/dev/null

# Add entry to CHANGELOG
DATE=$(date +%Y-%m-%d)
sed -i "s/^# Changelog/# Changelog\n\n## [${NEW_VERSION}] — ${DATE}$(echo -e "$DETAILS")/" CHANGELOG.md 2>/dev/null

# Commit and push
git add -A
git commit -m "${TITLE}
$(echo -e "$DETAILS")

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"

git push 2>/dev/null || true
