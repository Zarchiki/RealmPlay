"""Message normalization shared by local LLM call paths."""

from typing import Any


def normalize(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [
        dict(message) for message in messages
        if message.get("role") in {"system", "user", "assistant"} and message.get("content") not in (None, "")
    ]
    if not any(message.get("role") == "user" for message in normalized):
        normalized.append({"role": "user", "content": "Follow the preceding system instruction and provide the requested result."})
    elif normalized[-1].get("role") != "user":
        normalized.append({"role": "user", "content": "Continue from the context above and return only the requested result."})
    return normalized
