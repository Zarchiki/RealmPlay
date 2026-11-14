"""Per-user chat read receipt updates."""

import time


def mark_read(char_name: str, request, user: str, safe_name) -> dict:
    from chat_inbox import read_history, receipt, summary
    character = safe_name(char_name)
    history, _ = read_history(user, character)
    latest = max((float(message.get("timestamp", 0)) for message in history), default=0)
    receipt(user, character, max(float(request.through or 0), latest, time.time()))
    return summary(user, character)
