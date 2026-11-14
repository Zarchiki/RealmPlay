"""Per-character proactive interval configuration."""

import json
import random
import time

from fastapi import HTTPException


def load_config(path: str = "config.json") -> dict:
    defaults = {"enabled": True, "min_interval_seconds": 180, "max_interval_seconds": 360,
                "max_consecutive": 2, "presence_ttl_seconds": 75, "character_intervals": {}}
    try:
        values = json.loads(open(path, encoding="utf-8").read()).get("proactive", {})
    except (OSError, ValueError):
        values = {}
    config = {**defaults, **(values if isinstance(values, dict) else {})}
    config["min_interval_seconds"] = max(30, int(config.get("min_interval_seconds", 180)))
    config["max_interval_seconds"] = max(config["min_interval_seconds"], int(config.get("max_interval_seconds", 360)))
    config["max_consecutive"] = min(2, max(1, int(config.get("max_consecutive", 2))))
    config["presence_ttl_seconds"] = max(30, int(config.get("presence_ttl_seconds", 75)))
    if not isinstance(config.get("character_intervals"), dict):
        config["character_intervals"] = {}
    return config


def set_interval(req, user: str, safe_name, session_key, sessions, schedule_next, config_for) -> dict:
    character = safe_name(req.character_name)
    if not character:
        raise HTTPException(status_code=400, detail="Invalid character name")
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
    except Exception:
        config = {}
    proactive = config.get("proactive")
    if not isinstance(proactive, dict):
        proactive = {}
        config["proactive"] = proactive
    intervals = proactive.get("character_intervals")
    if not isinstance(intervals, dict):
        intervals = {}
        proactive["character_intervals"] = intervals
    if req.min_seconds is not None and req.max_seconds is not None and req.min_seconds > 0 and req.max_seconds > 0:
        minimum = max(30, int(req.min_seconds))
        intervals[character] = {"min_seconds": minimum, "max_seconds": max(minimum, int(req.max_seconds))}
    else:
        intervals.pop(character, None)
    with open("config.json", "w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, ensure_ascii=False)
    session = sessions.get(session_key(user, character))
    if session:
        schedule_next(session, config_for(), character, is_initial=False)
    return {"ok": True, "character": character, "override": intervals.get(character)}


def has_user_reply(history: list[dict]) -> bool:
    return any(
        item.get("role") == "user" and str(item.get("content") or "").strip()
        for item in (history or []) if isinstance(item, dict)
    )


def replies_since_user(history: list[dict]) -> int:
    count = 0
    for item in reversed(history or []):
        if item.get("role") == "user":
            break
        if item.get("role") == "assistant" and item.get("proactive") is True:
            count += 1
    return count


def session_key(user: str, character: str, safe_name) -> tuple[str, str]:
    return user, safe_name(character)


def character_params(config: dict, character: str, load_card) -> tuple[int, int, float]:
    minimum = int(config.get("min_interval_seconds", 180))
    maximum = int(config.get("max_interval_seconds", 360))
    override = config.get("character_intervals", {}).get(character, {})
    override = override if isinstance(override, dict) else {}
    minimum = max(30, int(override.get("min_seconds", minimum)))
    maximum = max(minimum, int(override.get("max_seconds", maximum)))
    talkativeness = override.get("talkativeness")
    if talkativeness is None and character:
        try:
            data = load_card(character)
            talkativeness = data.get("talkativeness") if isinstance(data, dict) else None
        except Exception:
            talkativeness = None
    try:
        talkativeness = float(talkativeness) if talkativeness is not None else 0.5
    except (ValueError, TypeError):
        talkativeness = 0.5
    return minimum, maximum, max(0.1, min(1.0, talkativeness))


def schedule_next(session: dict, config: dict, character: str, safe_name, params) -> None:
    name = safe_name(character) if character else session.get("character_name", "")
    if name:
        session["character_name"] = name
    minimum, maximum, talkativeness = params(config, name)
    override = session.get("request_interval")
    if isinstance(override, tuple) and len(override) == 2:
        minimum = max(30, int(override[0]))
        maximum = max(minimum, int(override[1]))
    session["talkativeness"] = talkativeness
    session["timing_profile"] = (minimum, maximum, talkativeness)
    base = random.randint(minimum, maximum)
    multiplier = 1.28 - talkativeness * 0.56
    interval = min(maximum, max(minimum, int(base * multiplier * random.uniform(0.85, 1.15))))
    session["next_at"] = time.monotonic() + interval


def touch(user: str, character: str, sessions: dict, config_for, safe_name, session_key, load_state, count_replies, schedule, params, replied=False, activity=False, state=None, interval_override=None) -> dict:
    config = config_for()
    name = safe_name(character)
    key = session_key(user, name)
    now = time.monotonic()
    session = sessions.get(key)
    if session is None:
        current = state if state is not None else load_state(user, name)
        count = count_replies(current.get("history", []))
        session = {"character_name": name, "last_seen": now, "last_action": now, "unanswered": count,
                   "sleeping": count >= config["max_consecutive"], "inflight": False}
        schedule(session, config, name, is_initial=True)
        sessions[key] = session
    else:
        session["last_seen"] = now
        session["character_name"] = name
        if tuple(session.get("timing_profile") or ()) != params(config, name):
            schedule(session, config, name, is_initial=False)
    if interval_override is not None:
        session["request_interval"] = interval_override
        schedule(session, config, name, is_initial=False)
    if activity:
        session["last_action"] = now
        schedule(session, config, name, is_initial=False)
    if replied:
        session["unanswered"] = 0
        session["sleeping"] = False
        schedule(session, config, name, is_initial=False)
    else:
        current = state if state is not None else load_state(user, name)
        count = count_replies(current.get("history", []))
        session["unanswered"] = count
        session["sleeping"] = count >= config["max_consecutive"]
    return session


def status(user: str, character: str, activity: bool, safe_name, load_state, touch_session, config_for) -> dict:
    name = safe_name(character)
    state = None
    summary = None
    try:
        state = load_state(user, name)
        summary = {key: state.get(key) for key in ("status", "scenario", "memory", "emotion")}
        summary["history_len"] = len(state.get("history", []))
    except Exception:
        pass
    session = touch_session(user, name, replied=False, activity=activity, char_state=state)
    now, asleep_until = time.monotonic(), float(((state or {}).get("needs_state") or {}).get("asleep_until", 0) or 0)
    resting, quiet = asleep_until > time.time(), bool(session.get("sleeping"))
    presence = "sleep" if resting else "quiet" if quiet else "online"
    return {"ok": True, "character": name, "status": presence, "label": "Sleep" if resting else "Away" if quiet else "Online",
            "unanswered": int(session.get("unanswered", 0)), "max_consecutive": config_for()["max_consecutive"],
            "next_in_seconds": None if presence != "online" else max(0, round(session.get("next_at", now) - now)),
            "sleep_until": asleep_until if resting else None, "sleep_remaining_seconds": max(0, round(asleep_until - time.time())) if resting else None,
            "talkativeness": session.get("talkativeness", 0.5), "state": summary}
