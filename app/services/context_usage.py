"""Transparent local context-budget reporting."""

import json
import re
from pathlib import Path


def breakdown(state: dict, profile: dict) -> dict:
    history = state.get("history", [])
    categories = {
        "Character profile": str(state.get("character_profile") or state["baseline"].get("char_summary", "")),
        "User profile": "\n".join(str(profile.get(key, "")) for key in ("display_name", "persona")),
        "Permanent memory": state.get("memory", ""),
        "Current situation": "\n".join(str(state.get(key, "")) for key in ("scenario", "status", "emotion")),
        "Recent messages": "\n".join(str(message.get("content", "")) for message in history[-8:]),
        "Older history": "\n".join(str(message.get("content", "")) for message in history[:-8]),
    }
    estimate = lambda value: len(re.findall(r"[\u0E00-\u0E7F]|[A-Za-z0-9_]+|[^\s]", value or ""))
    parts = [{"name": name, "tokens": estimate(value)} for name, value in categories.items()]
    total = sum(part["tokens"] for part in parts)
    for part in parts:
        part["percent"] = round(part["tokens"] * 100 / total, 1) if total else 0
    try:
        context_limit = int(json.loads(Path("config.json").read_text(encoding="utf-8")).get("llm", {}).get("context_length", 4096))
    except Exception:
        context_limit = 4096
    return {"total": total, "context_limit": context_limit,
            "context_percent": round(total * 100 / context_limit, 1) if context_limit else 0,
            "estimated": True, "parts": parts}
