"""Durable, bounded character-led intentions for every conversation."""

from __future__ import annotations

import re
import time
from typing import Any, Dict


_ASSERTIVE = ("assertive", "dominant", "bold", "confident", "leader", "proactive", "สายรุก", "มั่นใจ", "ผู้นำ")
_AFFECTIONATE = ("affectionate", "romantic", "loving", "caring", "clingy", "รัก", "โรแมนติก", "อ้อน", "ห่วงใย")


def normalize(value: Any) -> Dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    name = str(raw.get("name") or "").strip().lower()
    valid = {
        "seek_closeness", "lead_pacing", "tease", "recover", "pursue_need",
        "protect_boundary", "resolve_goal", "engage_present",
    }
    return {
        "name": name if name in valid else "",
        "goal": str(raw.get("goal") or "").strip()[:260],
        "urgency": str(raw.get("urgency") or "low").strip().lower() if str(raw.get("urgency") or "").strip().lower() in {"low", "medium", "high"} else "low",
        "allowed_stage": str(raw.get("allowed_stage") or "normal").strip().lower(),
        "status": "active" if raw.get("status") != "resolved" else "resolved",
        "created_at": float(raw.get("created_at") or 0),
        "updated_at": float(raw.get("updated_at") or 0),
    }


def _traits(baseline: Dict[str, Any]) -> str:
    return " ".join(str(baseline.get(key) or "") for key in ("personality", "persona", "char_summary")).casefold()


def _make(name: str, goal: str, urgency: str, stage: str) -> Dict[str, Any]:
    now = time.time()
    return {"name": name, "goal": goal, "urgency": urgency, "allowed_stage": stage, "status": "active", "created_at": now, "updated_at": now}


def _resolved(intent: Dict[str, Any], user_text: str, stage: str) -> bool:
    if not intent.get("name") or intent.get("allowed_stage") != stage:
        return True
    text = str(user_text or "").casefold()
    if not text:
        return False
    name = intent["name"]
    if name == "seek_closeness":
        return bool(re.search(r"กอด|จูบ|จับมือ|เข้าใกล้|\b(?:hug|kiss|hold|close)\b", text))
    if name == "pursue_need":
        return bool(re.search(r"อาหาร|กิน|พัก|นอน|\b(?:food|eat|rest|sleep)\b", text))
    if name in {"lead_pacing", "tease"}:
        return bool(re.search(r"ทำต่อ|ต่อเลย|เอาอีก|ได้สิ|\b(?:continue|again|yes|go ahead)\b", text))
    return False


def refresh(previous: Any, baseline: Dict[str, Any], state: Dict[str, Any], user_text: str = "") -> Dict[str, Any]:
    """Keep a current intent until resolved or invalidated by stage/needs."""
    scene = state.get("scene_state") or {}
    stage = str(scene.get("stage") or "normal").lower() if scene.get("active") else "normal"
    current = normalize(previous)
    if current.get("status") == "active" and not _resolved(current, user_text, stage):
        return current

    needs = state.get("needs_state") or {}
    energy = int(needs.get("energy", 100) or 100)
    hunger = str((state.get("time_state") or {}).get("biorhythm", {}).get("hunger") or "").casefold()
    traits = _traits(baseline)
    assertive = any(word in traits for word in _ASSERTIVE)
    affectionate = any(word in traits for word in _AFFECTIONATE)

    if stage == "aftercare":
        return _make("recover", "Seek comfort and recover at the character's own pace.", "high" if energy <= 25 else "medium", stage)
    if bool(scene.get("orgasm_exhausted")) or bool(scene.get("exhausted")) or int(scene.get("h_energy", 3) if "h_energy" in scene else 3) <= 0:
        return _make("engage_present", "Endure the overstimulated multi-orgasm exhaustion and react helplessly to the ongoing physical sensations.", "high", stage)
    if stage in {"foreplay", "explicit", "climax"}:
        if assertive and int(scene.get("h_energy", 0) or 0) > 0:
            return _make("lead_pacing", "Choose one stage-permitted beat and invite the user to meet it.", "medium", stage)
        return _make("seek_closeness", "Stay emotionally present and respond to the established scene with a personal, immediate reaction.", "medium", stage)
    if energy <= 25:
        return _make("recover", "Find a natural moment to rest or ask for quiet support.", "high", "normal")
    if hunger in {"starving", "hungry", "high"}:
        return _make("pursue_need", "Bring up finding food or satisfying a present physical need naturally.", "medium", "normal")
    if assertive:
        return _make("lead_pacing", "Choose one small, character-appropriate next step instead of waiting passively.", "low", "normal")
    if affectionate:
        return _make("seek_closeness", "Create one small opportunity for warmth, connection, or shared attention.", "low", "normal")
    return _make("engage_present", "Pursue one concrete observation, preference, or immediate goal that fits the present conversation.", "low", "normal")


def prompt_rule(value: Any, stage: str) -> str:
    intent = normalize(value)
    if (
        not intent.get("name")
        or intent.get("status") != "active"
        or intent.get("allowed_stage") != stage
    ):
        return ""
    return (
        "[Character-owned intention — active]\n"
        f"Current intention: {intent['name']}. Goal: {intent['goal']} Urgency: {intent['urgency']}.\n"
        "This is CHAR's own small goal, not a command for USER. Pursue it naturally through one voluntary, "
        "observable choice, invitation, or reaction when the current scene permits. Never narrate USER's choice, "
        "consent, thought, or action. The canonical stage, consent, boundaries, H-energy, terminal-expression rule, "
        f"and current `{stage}` stage ceiling override this intention whenever they conflict."
    )
