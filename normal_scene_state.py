"""Durable pacing state for ordinary, non-H-mode roleplay."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path("rules") / "normal"
DEFAULT = {"stage": "resting", "updated_at": 0, "reason": "initial"}


def _config() -> Dict[str, Any]:
    try:
        return json.loads((ROOT / "transitions.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"stages": ["resting"], "transitions": {"resting": ["resting"]}, "signals": {}}


def normalize(value: Any) -> Dict[str, Any]:
    state = dict(DEFAULT)
    if isinstance(value, dict):
        state.update({key: value[key] for key in DEFAULT if key in value})
    if state["stage"] not in _config()["stages"]:
        state["stage"] = "resting"
    return state


def advance(previous: Any, text: str) -> Dict[str, Any]:
    state, config = normalize(previous), _config()
    folded = (text or "").casefold()
    wanted = ""
    for stage in ("resting", "reflection", "transition", "activity", "conversation"):
        if any(cue.casefold() in folded for cue in config.get("signals", {}).get(stage, [])):
            wanted = stage
            break
    if not wanted:
        return state
    allowed = config["transitions"].get(state["stage"], [state["stage"]])
    if wanted not in allowed:
        wanted = "conversation" if "conversation" in allowed else state["stage"]
    return {"stage": wanted, "updated_at": time.time(), "reason": "matched normal-scene signal"}


def rebuild(history: Any) -> Dict[str, Any]:
    """Recover normal pacing from user turns after a history edit or regeneration."""
    state: Dict[str, Any] = dict(DEFAULT)
    for message in history or []:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        state = advance(state, str(message.get("content") or ""))
    return state


def stage_rule(language: str, value: Any) -> str:
    stage = normalize(value)["stage"]
    file = "Thai.md" if language == "thai" else "English.md"
    try:
        raw = (ROOT / "stages" / file).read_text(encoding="utf-8")
    except OSError:
        return ""
    part = raw.split(f"## {stage}", 1)
    return part[1].split("\n## ", 1)[0].strip() if len(part) == 2 else ""
