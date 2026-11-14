"""Persistent per-user read receipts and lightweight conversation summaries."""
import json
import re
import time
from pathlib import Path

import state_index


def stamp_history(history, previous):
    now = time.time()
    for i, message in enumerate(history):
        if not message.get("timestamp"):
            old = previous[i] if i < len(previous) else {}
            same = old.get("role") == message.get("role") and old.get("content") == message.get("content")
            old_ts = old.get("timestamp")
            if same:
                message["timestamp"] = float(old_ts) if old_ts is not None else 0.0
            elif message.get("is_first_message"):
                message["timestamp"] = float(old_ts) if old_ts is not None else max(1.0, now - 86400)
            else:
                message["timestamp"] = now


def read_history(user, name):
    path = Path("users") / user / name / "history.json"
    try:
        raw_history = json.loads(path.read_text(encoding="utf-8"))
        mtime = path.stat().st_mtime
        changed = False
        if isinstance(raw_history, list):
            for idx, msg in enumerate(raw_history):
                if isinstance(msg, dict) and not msg.get("timestamp"):
                    synth = max(1.0, mtime - (len(raw_history) - idx) * 10)
                    msg["timestamp"] = synth
                    changed = True
        if changed:
            try:
                path.write_text(json.dumps(raw_history, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                pass
        return raw_history, mtime
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return [], 0


def receipt(user, name, through=None):
    return state_index.profile_receipt(Path("users") / user / name, through)


def summary(user, name):
    history, modified = read_history(user, name)
    # History order is normally chronological, but regenerate/edit can update
    # an older bubble after newer entries already exist.  The inbox must sort
    # by the newest actual message timestamp, never merely by list position.
    latest = max(
        enumerate(history),
        key=lambda item: (float(item[1].get("timestamp", 0) or 0), item[0]),
        default=(-1, {}),
    )[1]
    latest_ts = float(latest.get("timestamp", 0) or 0)
    if not latest_ts and history:
        latest_ts = float(modified)

    read_at = receipt(user, name)
    if read_at is None:
        read_at = 0.0

    preview = re.sub(r"```[\s\S]*?(?:```|$)", "", latest.get("content", "")).strip()
    preview_clean = re.sub(r"\s+", " ", preview).strip()

    unread = sum(
        1 for m in history
        if m.get("role") == "assistant"
        and not m.get("is_first_message")
        and float(m.get("timestamp", 0) or 0) > float(read_at)
    )
    return {
        "last_message": preview_clean[:120],
        "last_message_at": latest_ts if history else 0,
        "unread_count": unread,
    }

