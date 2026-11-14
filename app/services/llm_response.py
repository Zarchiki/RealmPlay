"""OpenAI-compatible response parsing helpers."""

import json


def completion_content(data: bytes) -> tuple[str, str, str]:
    response = json.loads(data.decode("utf-8"))
    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})
    return str(message.get("content") or ""), str(message.get("reasoning_content") or ""), str(choice.get("finish_reason") or "")


def stream_delta(line: bytes) -> tuple[str, str, bool]:
    text = line.decode("utf-8", errors="replace").strip()
    if not text.startswith("data:"):
        return "", "", False
    event = text[5:].strip()
    if event == "[DONE]":
        return "", "", True
    try:
        delta = json.loads(event).get("choices", [{}])[0].get("delta", {})
    except (ValueError, TypeError, IndexError):
        return "", "", False
    return str(delta.get("content") or ""), str(delta.get("reasoning_content") or ""), False
