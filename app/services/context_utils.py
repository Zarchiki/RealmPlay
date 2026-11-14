"""Pure context-window operations used by prompt construction."""

import re
from typing import Any, Dict, List, Optional


BOS_CONTEXT_TURNS = 3


def prune_memory_facts(memory_text: str, max_facts: int = 5) -> str:
    """Keep only the newest non-empty memory lines for a compact prompt."""
    if not memory_text:
        return "No prior memories"
    lines = [line.strip() for line in memory_text.split("\n") if line.strip()]
    if not lines:
        return "No prior memories"
    return " | ".join(lines[-max_facts:])


def clip_context(value: Any, limit: int) -> str:
    """Normalize whitespace and cap a text value without splitting the marker."""
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    return value if len(value) <= limit else value[:max(0, limit - 1)].rstrip() + "…"


def estimate_context_tokens(value: Any) -> int:
    """Conservative local token estimate for mixed Thai/English content."""
    return len(re.findall(r"[\u0E00-\u0E7F]|[A-Za-z0-9_]+|[^\s]", str(value or "")))


def bos_context_active(history: List[Dict[str, Any]]) -> bool:
    """Keep beginning-of-story context for the first three character turns."""
    completed_turns = sum(
        1 for item in (history or [])
        if item.get("role") == "assistant" and not item.get("is_first_message")
    )
    return completed_turns < BOS_CONTEXT_TURNS


def history_without_first_message_context(
    history: List[Dict[str, Any]], baseline: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Drop the greeting marker after the initial story turns."""
    items = list(history or [])
    if bos_context_active(items):
        return items
    return [item for item in items if not item.get("is_first_message")]


def history_context_window(
    history: List[Dict[str, Any]], max_messages: int = 12,
) -> List[Dict[str, Any]]:
    """Return only recent dialogue that can contribute to a prompt."""
    usable = [
        item for item in (history or [])
        if isinstance(item, dict) and (item.get("content", "").strip() or item.get("user_image"))
    ]
    return usable[-max(1, int(max_messages or 1)):]


def build_bounded_history(
    history: List[Dict[str, Any]], max_messages: int = 14,
    chars_per_message: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Copy recent messages, optionally truncating each message body."""
    result = []
    for item in history[-max_messages:]:
        if not item.get("content", "").strip() and not item.get("user_image"):
            continue
        compact = dict(item)
        if chars_per_message is not None:
            compact["content"] = clip_context(item.get("content", ""), chars_per_message)
        result.append(compact)
    return result


def enforce_context_budget(
    system_instruction: str, history: List[Dict[str, Any]], budget: int = 3600,
) -> List[Dict[str, Any]]:
    """Reserve ``budget`` tokens for recent dialogue after the system prompt.

    System instructions can be larger than the old total budget by themselves.
    Treating that value as a whole-prompt cap silently collapsed the conversation
    to one turn (or none).  The system prompt is authoritative and already
    fixed, so the bounded window is applied to history only.
    """
    kept = list(history)
    history_budget = max(1, int(budget or 1))
    while (
        len(kept) > 1
        and sum(estimate_context_tokens(item.get("content", "")) for item in kept) > history_budget
    ):
        kept.pop(0)
    return kept
