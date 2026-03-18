"""Voice commands — convert spoken punctuation/commands into actions."""

import re


# Mapping: spoken word -> replacement
COMMANDS = {
    # Punctuation
    "точка": ".",
    "запятая": ",",
    "вопросительный знак": "?",
    "знак вопроса": "?",
    "восклицательный знак": "!",
    "двоеточие": ":",
    "точка с запятой": ";",
    "тире": " — ",
    "дефис": "-",
    "многоточие": "...",
    "кавычки": '"',
    "открой скобку": "(",
    "закрой скобку": ")",

    # Formatting
    "новая строка": "\n",
    "новый абзац": "\n\n",
    "пробел": " ",
    "табуляция": "\t",
}

# Words that trigger deletion of the last word
DELETE_COMMANDS = {"удали последнее слово", "удали слово", "назад"}


class VoiceCommandProcessor:
    """Processes voice commands in transcribed text.

    Replaces spoken punctuation with actual characters.
    Only active in streaming mode.
    """

    def __init__(self, enabled: bool = False, custom_commands: dict = None):
        self.enabled = enabled
        self._commands = dict(COMMANDS)
        if custom_commands:
            self._commands.update(custom_commands)

        # Build regex pattern for all commands (longest first to match greedy)
        sorted_cmds = sorted(self._commands.keys(), key=len, reverse=True)
        escaped = [re.escape(c) for c in sorted_cmds]
        self._pattern = re.compile(
            r"\b(" + "|".join(escaped) + r")\b",
            re.IGNORECASE,
        )

        # Delete commands pattern
        sorted_del = sorted(DELETE_COMMANDS, key=len, reverse=True)
        escaped_del = [re.escape(c) for c in sorted_del]
        self._delete_pattern = re.compile(
            r"\b(" + "|".join(escaped_del) + r")\b",
            re.IGNORECASE,
        )

    def process(self, text: str) -> str:
        """Apply voice commands to text."""
        if not self.enabled or not text:
            return text

        # Handle delete commands first
        text = self._handle_deletes(text)

        # Replace spoken punctuation with actual characters
        text = self._pattern.sub(self._replace_match, text)

        # Clean up spacing around punctuation
        text = self._clean_punctuation_spacing(text)

        return text

    def _replace_match(self, match):
        """Replace a matched command with its character."""
        spoken = match.group(0).lower()
        return self._commands.get(spoken, match.group(0))

    def _handle_deletes(self, text: str) -> str:
        """Handle 'delete last word' commands."""
        while True:
            m = self._delete_pattern.search(text)
            if not m:
                break
            # Remove the delete command
            before = text[: m.start()].rstrip()
            after = text[m.end():]
            # Remove the last word before the command
            words = before.rsplit(None, 1)
            if len(words) > 1:
                before = words[0]
            else:
                before = ""
            text = (before + " " + after).strip()
        return text

    @staticmethod
    def _clean_punctuation_spacing(text: str) -> str:
        """Remove extra spaces before punctuation marks."""
        # Remove space before .,!?;:
        text = re.sub(r"\s+([.,!?;:])", r"\1", text)
        # Ensure space after punctuation (except at end)
        text = re.sub(r"([.,!?;:])([^\s\n\"])", r"\1 \2", text)
        # Remove double spaces
        text = re.sub(r"  +", " ", text)
        return text.strip()
