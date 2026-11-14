"""Persistent, personality-based Energy lifecycle."""
from __future__ import annotations
import time
from datetime import datetime


PROFILES = {
    # sleep_hours, hourly drain, usual sleep start, usual wake hour
    "energetic": (6, 5.0, 22, 4), "balanced": (8, 6.25, 23, 7), "sensitive": (9, 7.15, 22, 7),
    "night_owl": (8, 6.25, 2, 10), "hyperactive": (7, 8.0, 0, 7),
}


def profile(personality: str) -> str:
    text = (personality or "").casefold()
    if any(x in text for x in ("night owl", "nocturnal", "นอนดึก", "กลางคืน")): return "night_owl"
    if any(x in text for x in ("hyperactive", "นักสู้", "ทำงานหนัก", "restless")): return "hyperactive"
    if any(x in text for x in ("sensitive", "introvert", "ขี้เหนื่อย", "อ่อนไหว")): return "sensitive"
    if any(x in text for x in ("energetic", "disciplined", "กระฉับกระเฉง", "มีวินัย", "อดทน")): return "energetic"
    return "balanced"


def refresh(state: dict | None, personality: str, now: float | None = None) -> dict:
    now = time.time() if now is None else float(now)
    state = dict(state or {})
    kind = profile(personality); sleep_hours, drain, sleep_start, wake_hour = PROFILES[kind]
    last = float(state.get("updated_at", now) if state.get("updated_at") is not None else now)
    asleep_until = float(state.get("asleep_until", 0) or 0)
    sleep_started_at = float(state.get("sleep_started_at", 0) or 0)
    sleep_start_energy = float(state.get("sleep_start_energy", 0.0) or 0.0)

    if asleep_until and now >= asleep_until:
        value, asleep_until = 100.0, 0.0
        sleep_started_at = 0.0
        sleep_start_energy = 0.0
    elif asleep_until:
        cycle_seconds = float(state.get("sleep_hours", sleep_hours)) * 3600.0
        if not sleep_started_at:
            sleep_started_at = max(0.0, asleep_until - cycle_seconds)
        elapsed_sleep = max(0.0, now - sleep_started_at)
        total_sleep = max(1.0, asleep_until - sleep_started_at)
        progress = min(1.0, elapsed_sleep / total_sleep)
        value = min(100.0, sleep_start_energy + (100.0 - sleep_start_energy) * progress)
    else:
        elapsed = max(0.0, (now-last)/3600)
        value = max(0.0, float(state.get("energy", 100) or 0)-elapsed*drain)
        sleep_started_at = 0.0
        sleep_start_energy = 0.0

    res = {
        "energy": round(value, 1),
        "profile": kind,
        "sleep_hours": sleep_hours,
        "drain_per_hour": drain,
        "usual_sleep_start": sleep_start,
        "usual_wake_hour": wake_hour,
        "updated_at": now,
        "asleep_until": asleep_until,
    }
    if sleep_started_at:
        res["sleep_started_at"] = sleep_started_at
    if sleep_start_energy:
        res["sleep_start_energy"] = sleep_start_energy
    return res


def sleep_remaining(state: dict | None, now: float | None = None) -> int:
    """Return remaining enforced sleep seconds, or zero once the character wakes."""
    now = time.time() if now is None else float(now)
    return max(0, int(float((state or {}).get("asleep_until", 0) or 0) - now))


def is_asleep(state: dict | None, now: float | None = None) -> bool:
    return sleep_remaining(state, now) > 0


def in_sleep_window(state: dict, now: float | None = None) -> bool:
    now = time.time() if now is None else float(now)
    hour = datetime.fromtimestamp(now).astimezone().hour
    start, wake = int(state.get("usual_sleep_start", 23)), int(state.get("usual_wake_hour", 7))
    return hour >= start or hour < wake if start > wake else start <= hour < wake


def require_sleep(state: dict, now: float | None = None, force: bool = False) -> dict:
    now = time.time() if now is None else float(now)
    current = dict(state or {})
    if (float(current.get("energy", 100)) > 20 or float(current.get("asleep_until", 0)) > now
            or (not force and not in_sleep_window(current, now))):
        return current
    sleep_hours = float(current.get("sleep_hours", 8))
    start_energy = float(current.get("energy", 0.0) or 0.0)
    current["sleep_started_at"] = now
    current["sleep_start_energy"] = start_energy
    current["energy"] = start_energy
    current["asleep_until"] = now + sleep_hours * 3600.0
    current["updated_at"] = now
    return current
