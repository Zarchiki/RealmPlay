"""Data-driven visible-reply cleanup rules."""
import json
import re
from functools import lru_cache
from pathlib import Path


RULE_FILE = Path(__file__).parent / "rules" / "response_quality" / "Thai.json"


@lru_cache(maxsize=1)
def thai_banned_confirmation_patterns() -> tuple[str, ...]:
    """Load Thai phrase rules once; an invalid rule file fails safely closed."""
    try:
        data = json.loads(RULE_FILE.read_text(encoding="utf-8"))
        patterns = data.get("banned_confirmation_patterns", [])
    except (OSError, ValueError):
        return ()
    if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
        return ()
    return tuple(patterns)


def thai_banned_confirmation_prompt_instruction() -> str:
    """Return the model-facing instruction from the same rule source."""
    try:
        data = json.loads(RULE_FILE.read_text(encoding="utf-8"))
        instruction = data.get("prompt_instruction", "")
    except (OSError, ValueError):
        return ""
    return instruction.strip() if isinstance(instruction, str) else ""


def clean_banned_confirmation_phrases(text: str) -> str:
    """Remove configured canned Thai confirmation reactions from visible prose."""
    if not text:
        return text
    patterns = thai_banned_confirmation_patterns()
    if not patterns:
        return text
    marker = "(?:" + "|".join(patterns) + ")"
    text = re.sub(r'\s*["“][^"”\n]*?' + marker + r'[^"”\n]*?["”]\s*', " ", text, flags=re.IGNORECASE)
    text = re.sub(r'\s*' + marker + r'[^\n\.\!\?？]*[\.\!\?？]?', " ", text, flags=re.IGNORECASE)
    return re.sub(r"[ \t]{2,}", " ", text).strip()
