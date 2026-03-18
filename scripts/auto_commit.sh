#!/bin/bash
# Auto-commit: bump version, update README/CHANGELOG, commit, push
cd "$(dirname "$0")/.." || exit 0

# Check if there are changes
if git diff --quiet HEAD 2>/dev/null && \
   git diff --cached --quiet 2>/dev/null && \
   [ -z "$(git ls-files --others --exclude-standard)" ]; then
    exit 0  # Nothing to commit
fi

# Read current version
VERSION=$(cat VERSION 2>/dev/null | tr -d '[:space:]')
if [ -z "$VERSION" ]; then
    VERSION="1.9.0"
fi

# Bump patch version (1.9.0 -> 1.9.1)
MAJOR=$(echo "$VERSION" | cut -d. -f1)
MINOR=$(echo "$VERSION" | cut -d. -f2)
PATCH=$(echo "$VERSION" | cut -d. -f3)
PATCH=$((PATCH + 1))
NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

# Get change summary
CHANGED=$(git diff --stat HEAD 2>/dev/null | tail -1 | sed 's/^ *//')
if [ -z "$CHANGED" ]; then
    CHANGED=$(git status --short | head -5 | tr '\n' ', ')
fi

# Get list of changed files for commit message
FILES=$(git diff --name-only HEAD 2>/dev/null; git ls-files --others --exclude-standard)
SUMMARY=""
for f in $FILES; do
    case "$f" in
        core/*) SUMMARY="$SUMMARY core" ;;
        gui/*) SUMMARY="$SUMMARY gui" ;;
        app.py) SUMMARY="$SUMMARY app" ;;
        *.md) SUMMARY="$SUMMARY docs" ;;
    esac
done
# Deduplicate
SUMMARY=$(echo "$SUMMARY" | tr ' ' '\n' | sort -u | tr '\n' ' ' | sed 's/^ *//;s/ *$//')
if [ -z "$SUMMARY" ]; then
    SUMMARY="update"
fi

# Update VERSION
echo "$NEW_VERSION" > VERSION

# Update README version
sed -i "s/Speech-to-Text v[0-9]*\.[0-9]*\.[0-9]*/Speech-to-Text v${NEW_VERSION}/" README.md 2>/dev/null

# Add entry to CHANGELOG
DATE=$(date +%Y-%m-%d)
ENTRY="\n## [${NEW_VERSION}] — ${DATE}\n- ${SUMMARY}: ${CHANGED}"
sed -i "s/^# Changelog/# Changelog\n${ENTRY}/" CHANGELOG.md 2>/dev/null

# Commit and push
git add -A
git commit -m "v${NEW_VERSION} — ${SUMMARY}

${CHANGED}

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"

git push 2>/dev/null || true
