"""Unified Single-File Data Block Table & Per-Turn State Snapshot Manager.

Maintains a single unified table file (`turn_metadata.json`) per character in
`users/{username}/{character_name}/turn_metadata.json` that explicitly separates:
1. `current_datablock` ("Currently Value Data Block"):
   The live, authoritative values of the character at the present moment.
2. `turn_records` ("Turn Record Data Block"):
   Ordered per-turn rows (`turn_index`, `turn_id`, `role`, `timestamp`,
   `datablock`, `snapshot`, `media`) for every message in `history`, so
   deleting or regenerating messages restores the exact per-turn state
   (`arousal_value`, `arousal_level`, `h_stage`, `h_stage_level`, `h_energy`,
   `exhausted`, `affection`, `relationship`, `hunger`, `energy`, `posture`,
   `location`, `emotion`, `active_wardrobe`, `outfits`, `inventory`,
   `inventory_wardrobe`, `status`, `scenario`, `memory`, `scene_state`).
"""
from __future__ import annotations

import base64
import copy
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


METADATA_FILE = "turn_metadata.json"
SNAPSHOT_KEYS = (
    "status", "scenario", "memory", "emotion", "emotion_detail", "outfits",
    "inventory", "inventory_wardrobe", "pending_user_request", "location_prompt", "scene_state", "normal_scene_state",
    "arousal_state", "needs_state", "time_state",
    "character_intent",
)

CLOTHING_SLOT_ORDER = (
    "head", "neck", "earrings", "eyeglasses",
    "top", "bra", "bottom", "panties",
    "gloves", "arm", "socks", "shoes",
)


def _metadata_path(root: Path) -> Path:
    return root / METADATA_FILE


def _empty_table() -> Dict[str, Any]:
    return {
        "version": 2,
        "updated_at": time.time(),
        "current_datablock": {},
        "turn_records": [],
        "turns": {},
    }


def _load(root: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(_metadata_path(root).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _empty_table()
        turns = raw.get("turns") if isinstance(raw.get("turns"), dict) else {}
        turn_records = raw.get("turn_records") if isinstance(raw.get("turn_records"), list) else []
        current_datablock = raw.get("current_datablock") if isinstance(raw.get("current_datablock"), dict) else {}
        return {
            "version": 2,
            "updated_at": float(raw.get("updated_at") or time.time()),
            "current_datablock": current_datablock,
            "turn_records": turn_records,
            "turns": turns,
        }
    except (OSError, ValueError):
        return _empty_table()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _parse_status_fields(status_text: str) -> Dict[str, Any]:
    """Parse structured fields out of the markdown status block."""
    raw = str(status_text or "")

    def _field(name: str, default: str = "") -> str:
        m = re.search(rf"(?im)^\s*-?\s*{re.escape(name)}\s*:\s*(.+)$", raw)
        return m.group(1).strip() if m else default

    posture = _field("Posture", "Standing and maintaining natural eye contact")
    location = _field("Location", "Starting scene")
    energy = _field("Energy", "Normal")
    hunger = _field("Hunger", "Normal")
    arousal_raw = _field("Arousal", "None (0/100)")
    relationship = _field("Relationship", "Acquaintance")
    affection_raw = _field("Affection", "10 / 100")
    body_language = _field("Body Language", "Calm and relaxed")

    # Parse numeric arousal (0..100) and level
    arousal_val = 0
    num_m = re.search(r"\b(\d{1,3})\s*/\s*100\b", arousal_raw)
    if num_m:
        arousal_val = max(0, min(100, int(num_m.group(1))))
    else:
        low_ar = arousal_raw.casefold()
        for lvl_name, lvl_num in (("overwhelmed", 100), ("high", 75), ("medium", 50), ("low", 25), ("none", 0)):
            if lvl_name in low_ar:
                arousal_val = lvl_num
                break

    if arousal_val <= 0:
        arousal_level = "None"
    elif arousal_val < 38:
        arousal_level = "Low"
    elif arousal_val < 63:
        arousal_level = "Medium"
    elif arousal_val < 88:
        arousal_level = "High"
    else:
        arousal_level = "Overwhelmed"

    # Parse numeric affection (-100..100)
    aff_m = re.search(r"(-?\d{1,3})", affection_raw)
    affection_val = max(-100, min(100, int(aff_m.group(1)))) if aff_m else 10

    return {
        "posture": posture,
        "location": location,
        "energy": energy,
        "hunger": hunger,
        "arousal_value": arousal_val,
        "arousal_level": arousal_level,
        "arousal_display": f"{arousal_level} ({arousal_val}/100)",
        "relationship": relationship,
        "affection": affection_val,
        "body_language": body_language,
    }


def _active_wardrobe_summary(outfits: Any) -> Tuple[str, List[str]]:
    """Return active wardrobe prompt string and list of active slot keys."""
    if not isinstance(outfits, dict):
        return "", []
    if isinstance(outfits.get("naked"), dict) and outfits["naked"].get("active"):
        return str(outfits["naked"].get("prompt") or "completely naked, nude"), ["naked"]
    prompts: List[str] = []
    active_slots: List[str] = []
    for slot in CLOTHING_SLOT_ORDER:
        item = outfits.get(slot)
        if isinstance(item, dict) and item.get("active") and str(item.get("prompt") or "").strip():
            prompts.append(str(item["prompt"]).strip())
            active_slots.append(slot)
    if not prompts:
        naked_prompt = str((outfits.get("naked") or {}).get("prompt") or "completely naked, nude").strip()
        return naked_prompt, ["naked"]
    return ", ".join(prompts), active_slots


def _sanitize_scene_state(scene: Any) -> Dict[str, Any]:
    """Normalize scene_state and ensure legacy orgasm_counter is replaced by h_energy & exhausted."""
    raw = copy.deepcopy(scene) if isinstance(scene, dict) else {}
    stage = str(raw.get("stage") or raw.get("scene_stage") or "normal").strip().lower()
    if stage not in {"normal", "intimacy", "foreplay", "explicit", "climax", "aftercare"}:
        stage = "normal"
    active = stage != "normal"
    try:
        stage_level = 0 if stage == "normal" else max(1, min(3, int(raw.get("stage_level", 1) or 1)))
    except (TypeError, ValueError):
        stage_level = 0 if stage == "normal" else 1
    if "h_energy" in raw:
        try:
            h_energy = max(0, min(3, int(raw["h_energy"])))
        except (TypeError, ValueError):
            h_energy = 3
    else:
        spent = raw.get("orgasm_counter", raw.get("climax_peaks", raw.get("climax_loops", 0)))
        try:
            h_energy = max(0, min(3, 3 - int(spent or 0)))
        except (TypeError, ValueError):
            h_energy = 3
    exhausted = (h_energy <= 0)
    for legacy_key in ("orgasm_counter", "climax_peaks", "climax_loops"):
        raw.pop(legacy_key, None)
    raw["stage"] = stage
    raw["scene_stage"] = stage
    raw["active"] = active
    raw["stage_level"] = stage_level
    raw["h_energy"] = h_energy
    raw["exhausted"] = exhausted
    raw["orgasm_exhausted"] = exhausted and active
    return raw


def build_datablock(state: Dict[str, Any], *, turn_index: int = -1, turn_id: str = "") -> Dict[str, Any]:
    """Construct a structured Data Block dictionary from a character state or snapshot."""
    src = state.get("snapshot") if isinstance(state.get("snapshot"), dict) else state
    status_str = str(src.get("status") or "")
    parsed_status = _parse_status_fields(status_str)
    scene = _sanitize_scene_state(src.get("scene_state"))
    h_energy = int(scene.get("h_energy", 3))
    exhausted = bool(scene.get("exhausted") or h_energy <= 0)
    if exhausted:
        parsed_status["energy"] = "Exhausted"
        if re.search(r"(?im)^\s*-?\s*Energy\s*:", status_str):
            status_str = re.sub(r"(?im)^(\s*-?\s*Energy\s*:\s*).+$", r"\1Exhausted", status_str)

    outfits = copy.deepcopy(src.get("outfits") or {})
    active_wardrobe, active_slots = _active_wardrobe_summary(outfits)
    inventory = copy.deepcopy(src.get("inventory") if isinstance(src.get("inventory"), list) else [])
    inventory_wardrobe = copy.deepcopy(src.get("inventory_wardrobe") if isinstance(src.get("inventory_wardrobe"), list) else [])
    emotion_detail = copy.deepcopy(src.get("emotion_detail") if isinstance(src.get("emotion_detail"), dict) else {})
    emotion = str(src.get("emotion") or emotion_detail.get("name") or "neutral").strip() or "neutral"
    arousal_meta = copy.deepcopy(src.get("arousal_state") if isinstance(src.get("arousal_state"), dict) else {})
    for legacy_key in ("orgasm_counter", "climax_peaks", "climax_loops"):
        arousal_meta.pop(legacy_key, None)
    arousal_meta["h_energy"] = h_energy
    arousal_meta["exhausted"] = exhausted
    arousal_meta.setdefault("final", parsed_status["arousal_value"])
    arousal_meta.setdefault("level", parsed_status["arousal_level"])

    return {
        "turn_index": turn_index,
        "turn_id": str(turn_id or ""),
        "updated_at": time.time(),
        "arousal_value": parsed_status["arousal_value"],
        "arousal_level": parsed_status["arousal_level"],
        "arousal_display": parsed_status["arousal_display"],
        "arousal_state": arousal_meta,
        "h_stage": scene["stage"],
        "h_stage_level": scene["stage_level"],
        "h_active": scene["active"],
        "h_energy": h_energy,
        "exhausted": exhausted,
        "scene_state": scene,
        "affection": parsed_status["affection"],
        "relationship": parsed_status["relationship"],
        "hunger": parsed_status["hunger"],
        "energy": parsed_status["energy"],
        "posture": parsed_status["posture"],
        "location": parsed_status["location"],
        "body_language": parsed_status["body_language"],
        "emotion": emotion,
        "emotion_detail": emotion_detail or {"name": emotion, "intensity": 0, "cause": ""},
        "active_wardrobe": active_wardrobe,
        "active_wardrobe_slots": active_slots,
        "outfits": outfits,
        "inventory": inventory,
        "inventory_wardrobe": inventory_wardrobe,
        "status": status_str,
        "scenario": str(src.get("scenario") or ""),
        "memory": str(src.get("memory") or ""),
    }


def _snapshot_from_datablock(datablock: Dict[str, Any], extra_snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    snap = copy.deepcopy(extra_snapshot) if isinstance(extra_snapshot, dict) else {}
    for key in (
        "status", "scenario", "memory", "emotion", "emotion_detail",
        "outfits", "inventory", "inventory_wardrobe", "scene_state", "arousal_state",
    ):
        if key in datablock:
            snap[key] = copy.deepcopy(datablock[key])
    if "scene_state" in snap:
        snap["scene_state"] = _sanitize_scene_state(snap["scene_state"])
    return snap


def _store_user_image(root: Path, turn_id: str, value: Any) -> str | None:
    raw = str(value or "")
    match = re.match(r"data:([^;,]+);base64,([\s\S]+)$", raw)
    encoded = match.group(2) if match else raw
    mime = match.group(1).casefold() if match else "image/jpeg"
    extension = {"image/png": "png", "image/webp": "webp", "image/gif": "gif"}.get(mime, "jpg")
    try:
        binary = base64.b64decode(encoded, validate=True)
    except Exception:
        return None
    if not binary:
        return None
    relative = f"media/{turn_id}.{extension}"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(binary)
    return relative


def user_media_path(root: Path, turn_id: str) -> Path | None:
    record = (_load(root).get("turns") or {}).get(str(turn_id)) or {}
    relative = str((record.get("media") or {}).get("user_file") or "")
    candidate = (root / relative).resolve()
    media_root = (root / "media").resolve()
    if relative and candidate.is_file() and candidate.is_relative_to(media_root):
        return candidate
    return None


def _legacy_snapshot(content: str) -> tuple[str, Dict[str, Any]]:
    """Move old hidden fenced state blocks out of a visible assistant reply."""
    snapshot: Dict[str, Any] = {}
    labels = {
        "status": "status", "current situation": "scenario", "scenario": "scenario",
        "permanent memories": "memory", "permanent memory": "memory", "emotion": "emotion_detail",
    }

    def replace(match: re.Match[str]) -> str:
        label = re.sub(r"\s+", " ", match.group(1).strip().casefold())
        value = match.group(2).strip()
        key = labels.get(label)
        if not key:
            return match.group(0)
        if key == "emotion_detail":
            try:
                detail = json.loads(value)
            except ValueError:
                detail = {"name": value or "neutral", "intensity": 0, "cause": ""}
            if isinstance(detail, dict):
                snapshot["emotion_detail"] = detail
                snapshot["emotion"] = str(detail.get("name") or "neutral")
        else:
            snapshot[key] = value
        return ""

    cleaned = re.sub(r"```\s*([^\n`]+)\s*\n([\s\S]*?)```", replace, content or "", flags=re.I)
    return cleaned.strip(), snapshot


def snapshot_from_state(state: Dict[str, Any], *, turn_index: int = -1, turn_id: str = "") -> Dict[str, Any]:
    """Create a complete per-turn metadata payload containing both `datablock` and `snapshot`."""
    clean_state = copy.deepcopy(state)
    if "scene_state" in clean_state:
        clean_state["scene_state"] = _sanitize_scene_state(clean_state["scene_state"])
    datablock = build_datablock(clean_state, turn_index=turn_index, turn_id=turn_id)
    snapshot = {key: copy.deepcopy(clean_state[key]) for key in SNAPSHOT_KEYS if key in clean_state}
    for key in ("status", "scenario", "memory", "emotion", "emotion_detail", "outfits", "inventory", "inventory_wardrobe", "scene_state", "arousal_state"):
        snapshot[key] = copy.deepcopy(datablock[key])
    return {
        "datablock": datablock,
        "snapshot": snapshot,
    }


def _build_initial_baseline_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Build initial turn-0 baseline state for greeting / empty history."""
    baseline = state.get("baseline") if isinstance(state.get("baseline"), dict) else {}
    default_status = (
        "[Posture & Activity]\n"
        "- Posture: Standing and maintaining natural eye contact\n"
        "- Location: Starting scene\n\n"
        "[Vital Needs & Biorhythm]\n"
        "- Energy: Normal\n"
        "- Hunger: Normal\n"
        "- Arousal: None (0/100)\n\n"
        "[Relational & Emotional State]\n"
        "- Relationship: Acquaintance\n"
        "- Affection: 10 / 100\n"
        "- Body Language: Calm and relaxed\n"
    )
    return {
        "status": default_status,
        "scenario": str(baseline.get("scenario") or state.get("scenario") or ""),
        "memory": "# Permanent Memory\n- Initial encounter.\n",
        "emotion": "neutral",
        "emotion_detail": {"name": "neutral", "intensity": 0, "cause": ""},
        "outfits": copy.deepcopy(state.get("outfits") or {}),
        "inventory": copy.deepcopy(state.get("inventory") if isinstance(state.get("inventory"), list) else []),
        "inventory_wardrobe": copy.deepcopy(state.get("inventory_wardrobe") if isinstance(state.get("inventory_wardrobe"), list) else []),
        "scene_state": _sanitize_scene_state({"stage": "normal", "stage_level": 0, "active": False, "h_energy": 3, "exhausted": False}),
        "arousal_state": {"final": 0, "level": "None", "h_energy": 3, "exhausted": False},
    }


def _is_uninitialized_default_status(status_text: str) -> bool:
    """Return True if `status_text` is still the stock turn-0 placeholder template."""
    s = str(status_text or "")
    if not s.strip():
        return True
    return (
        "Standing and maintaining natural eye contact" in s
        and "Location: Starting scene" in s
        and "Affection: 10 / 100" in s
        and "Arousal: None (0/100)" in s
    )


def sync_table(
    root: Path,
    state: Dict[str, Any],
    history: Iterable[Dict[str, Any]],
    *,
    update_latest_turn_from_current: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Synchronize the unified single-file Data Block table (`turn_metadata.json`).

    Ensures:
    - Every message in `history` has a stable `turn_id` and a corresponding entry in
      `turn_records` (Turn Record Data Block) and `turns`.
    - `current_datablock` (Currently Value Data Block) reflects the character's live state.
    - When `update_latest_turn_from_current=True` (e.g., manual wardrobe/inventory/status edits),
      the latest turn's record in `turn_records` is also updated to match `current_datablock`.
    - `history.json` stores clean dialogue entries (with `turn_id`), while `turn_metadata.json`
      stores the full unified table (`current_datablock`, `turn_records`, `turns`).
    """
    data = _load(root)
    turns_map: Dict[str, Any] = dict(data.get("turns") or {})
    existing_records_by_id: Dict[str, Dict[str, Any]] = {}
    for row in data.get("turn_records") or []:
        if isinstance(row, dict) and row.get("turn_id"):
            existing_records_by_id[str(row["turn_id"])] = row

    history_list = [dict(m) for m in (history or []) if isinstance(m, dict)]
    current_db = build_datablock(
        state,
        turn_index=len(history_list) - 1,
        turn_id=str(history_list[-1].get("turn_id") or "") if history_list else "",
    )

    stored_history: List[Dict[str, Any]] = []
    new_turn_records: List[Dict[str, Any]] = []
    active_ids = set()
    history_file_changed = False

    # Running fallback state for backfilling legacy turns that had no snapshot.
    # If the character already has live progressed state (beyond turn-0 defaults),
    # seed legacy unrecorded turns from current live state rather than wiping them
    # back to turn-0 "Starting scene" defaults.
    running_state = _build_initial_baseline_state(state)
    if len(history_list) >= 1 and not _is_uninitialized_default_status(str(state.get("status") or "")):
        running_state = copy.deepcopy(state)

    for idx, raw_msg in enumerate(history_list):
        message = copy.deepcopy(raw_msg)
        turn_id = str(message.get("turn_id") or uuid.uuid4().hex)
        if message.get("turn_id") != turn_id:
            message["turn_id"] = turn_id
            history_file_changed = True
        active_ids.add(turn_id)

        record = copy.deepcopy(turns_map.get(turn_id) or existing_records_by_id.get(turn_id) or {})

        # Migrate legacy fenced blocks if present in assistant reply
        if message.get("role") == "assistant":
            cleaned, legacy = _legacy_snapshot(str(message.get("content") or ""))
            if cleaned != message.get("content", ""):
                message["content"] = cleaned
                history_file_changed = True
            if legacy:
                snap = dict(record.get("snapshot") or {})
                snap.update(legacy)
                record["snapshot"] = snap

        # Extract supplied transient metadata on message
        supplied = message.pop("metadata", None)
        if supplied is not None:
            history_file_changed = True
            if isinstance(supplied, dict):
                if isinstance(supplied.get("snapshot"), dict):
                    snap = dict(record.get("snapshot") or {})
                    snap.update(copy.deepcopy(supplied["snapshot"]))
                    record["snapshot"] = snap
                if isinstance(supplied.get("datablock"), dict):
                    record["datablock"] = copy.deepcopy(supplied["datablock"])
                if isinstance(supplied.get("media"), dict):
                    med = dict(record.get("media") or {})
                    med.update(copy.deepcopy(supplied["media"]))
                    record["media"] = med

        # Extract transient media/emotion fields from message dict before saving to history.json
        media = dict(record.get("media") or {})
        if "user_image" in message:
            user_file = _store_user_image(root, turn_id, message.pop("user_image"))
            if user_file:
                media["user_file"] = user_file
            history_file_changed = True
        if "user_image_path" in message:
            media.setdefault("user_file", message.pop("user_image_path"))
            history_file_changed = True
        if "image_url" in message:
            img_val = message.pop("image_url")
            if img_val:
                media["path"] = img_val
            else:
                media.pop("path", None)
            history_file_changed = True
        if "image_prompt" in message:
            prompt_val = message.pop("image_prompt")
            if prompt_val:
                media["prompt"] = prompt_val
            else:
                media.pop("prompt", None)
            history_file_changed = True
        if media:
            record["media"] = media

        snap = dict(record.get("snapshot") or {})
        if "emotion" in message:
            snap["emotion"] = message.pop("emotion")
            history_file_changed = True

        # Determine the state source for this turn's datablock
        is_last_turn = (idx == len(history_list) - 1)
        if is_last_turn and (
            update_latest_turn_from_current
            or (not snap and not record.get("datablock"))
            or (snap and not record.get("datablock"))
        ):
            # When migrating legacy turns or when manual state edits happen, ensure the final turn matches live state
            merged_last = copy.deepcopy(running_state)
            if snap:
                merged_last.update(copy.deepcopy(snap))
            for k in (
                "status", "scenario", "memory", "emotion", "emotion_detail",
                "outfits", "inventory", "inventory_wardrobe", "scene_state", "arousal_state",
            ):
                if k in state and state[k] is not None:
                    merged_last[k] = copy.deepcopy(state[k])
            source_for_turn = merged_last
        elif snap:
            # Merge snap onto running_state so any missing keys (e.g. outfits/inventory) carry forward
            merged = copy.deepcopy(running_state)
            merged.update(copy.deepcopy(snap))
            source_for_turn = merged
        elif isinstance(record.get("datablock"), dict) and record["datablock"]:
            merged = copy.deepcopy(running_state)
            merged.update(copy.deepcopy(record["datablock"]))
            source_for_turn = merged
        else:
            # Backfill legacy turn: if it's the greeting (index 0, is_first_message), use initial baseline;
            # otherwise carry running_state (or current state on final turn)
            if idx == 0 and message.get("is_first_message"):
                source_for_turn = running_state
            else:
                source_for_turn = state if is_last_turn else running_state

        turn_db = build_datablock(source_for_turn, turn_index=idx, turn_id=turn_id)
        turn_snap = _snapshot_from_datablock(turn_db, snap)

        # Advance running_state for subsequent turns
        running_state = copy.deepcopy(turn_snap)

        row_entry = {
            "turn_index": idx,
            "turn_id": turn_id,
            "role": str(message.get("role") or "assistant"),
            "timestamp": float(message.get("timestamp") or turn_db.get("updated_at") or time.time()),
            "datablock": turn_db,
            "snapshot": turn_snap,
            "media": media,
        }
        turns_map[turn_id] = row_entry
        new_turn_records.append(row_entry)
        stored_history.append(message)

    # Clean up orphaned user media files for deleted turns
    removed_ids = [tid for tid in list(turns_map.keys()) if tid not in active_ids]
    for tid in removed_ids:
        old_rec = turns_map.pop(tid, None) or {}
        relative = str((old_rec.get("media") or {}).get("user_file") or "")
        candidate = (root / relative).resolve()
        media_root = (root / "media").resolve()
        if relative and candidate.is_file() and candidate.is_relative_to(media_root):
            try:
                candidate.unlink()
            except OSError:
                pass

    if new_turn_records and update_latest_turn_from_current:
        current_db = copy.deepcopy(new_turn_records[-1]["datablock"])
    elif new_turn_records:
        current_db["turn_index"] = len(new_turn_records) - 1
        current_db["turn_id"] = new_turn_records[-1]["turn_id"]

    table_payload = {
        "version": 2,
        "updated_at": time.time(),
        "current_datablock": current_db,
        "turn_records": new_turn_records,
        "turns": {row["turn_id"]: row for row in new_turn_records},
    }
    _write(_metadata_path(root), table_payload)
    if history_file_changed:
        _write(root / "history.json", stored_history)

    return hydrate(stored_history, table_payload), table_payload


def rollback_to_latest_turn(
    root: Path,
    remaining_history: List[Dict[str, Any]],
    current_state: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """Roll back `current_datablock` and character state to the latest remaining turn's Turn Record.

    Called when deleting messages (`/api/chat/delete_message`, `/api/chat/delete_messages`)
    or rolling back before regeneration (`/api/chat/regenerate`).

    Returns:
        `(hydrated_history, state_updates_to_save, restored_datablock)`
    """
    data = _load(root)
    turns_map = data.get("turns") or {}
    records_by_id = {
        str(r.get("turn_id")): r
        for r in (data.get("turn_records") or [])
        if isinstance(r, dict) and r.get("turn_id")
    }

    # Find the target turn record from the last remaining message in history
    restored_source: Optional[Dict[str, Any]] = None
    last_turn_id = ""
    last_idx = len(remaining_history) - 1

    if remaining_history and not (len(remaining_history) == 1 and remaining_history[0].get("is_first_message")):
        for idx in range(len(remaining_history) - 1, -1, -1):
            msg = remaining_history[idx]
            if not isinstance(msg, dict):
                continue
            tid = str(msg.get("turn_id") or "")
            rec = (
                turns_map.get(tid)
                or records_by_id.get(tid)
                or (msg.get("metadata") if isinstance(msg.get("metadata"), dict) else None)
            )
            if isinstance(rec, dict):
                db = rec.get("datablock") if isinstance(rec.get("datablock"), dict) else None
                snap = rec.get("snapshot") if isinstance(rec.get("snapshot"), dict) else None
                if db or snap:
                    merged = copy.deepcopy(current_state)
                    if snap:
                        merged.update(copy.deepcopy(snap))
                    if db:
                        for k in (
                            "status", "scenario", "memory", "emotion", "emotion_detail",
                            "outfits", "inventory", "inventory_wardrobe", "scene_state", "arousal_state",
                        ):
                            if k in db:
                                merged[k] = copy.deepcopy(db[k])
                    restored_source = merged
                    last_turn_id = tid
                    break

    # Guard against legacy backfilled snapshots that carry stock turn-0 defaults
    # ("Standing and maintaining natural eye contact" / "Location: Starting scene")
    # when rolling back mid-conversation (remaining_history has > 1 message).
    if (
        restored_source is not None
        and len(remaining_history) > 1
        and _is_uninitialized_default_status(str(restored_source.get("status") or ""))
        and not _is_uninitialized_default_status(str(current_state.get("status") or ""))
    ):
        for preserve_key in ("status", "scenario", "memory", "scene_state", "arousal_state", "outfits", "inventory", "inventory_wardrobe"):
            if preserve_key in current_state and current_state[preserve_key]:
                restored_source[preserve_key] = copy.deepcopy(current_state[preserve_key])

    if restored_source is None:
        # History is empty or back to initial greeting: restore initial baseline state
        restored_source = _build_initial_baseline_state(current_state)
        if remaining_history and isinstance(remaining_history[-1], dict):
            last_turn_id = str(remaining_history[-1].get("turn_id") or "")

    restored_db = build_datablock(restored_source, turn_index=last_idx, turn_id=last_turn_id)
    state_updates = {
        "status": restored_db["status"],
        "scenario": restored_db["scenario"],
        "memory": restored_db["memory"],
        "emotion": restored_db["emotion"],
        "emotion_detail": restored_db["emotion_detail"],
        "outfits": restored_db["outfits"],
        "inventory": restored_db["inventory"],
        "inventory_wardrobe": restored_db["inventory_wardrobe"],
        "scene_state": restored_db["scene_state"],
        "arousal_state": restored_db["arousal_state"],
    }

    updated_state = {**copy.deepcopy(current_state), **copy.deepcopy(state_updates)}
    hydrated_history, table_payload = sync_table(
        root,
        updated_state,
        remaining_history,
        update_latest_turn_from_current=False,
    )
    # Force current_datablock to exactly match restored_db
    table_payload["current_datablock"] = restored_db
    _write(_metadata_path(root), table_payload)
    state_updates["history"] = hydrated_history
    state_updates["datablock_table"] = {
        "current_datablock": restored_db,
        "turn_count": len(hydrated_history),
    }
    return hydrated_history, state_updates, restored_db


def get_turn_datablock(
    root: Path,
    history: List[Dict[str, Any]],
    message_index: int,
    fallback_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Return the exact Turn Record Data Block for `message_index`."""
    if 0 <= message_index < len(history):
        msg = history[message_index]
        if isinstance(msg, dict):
            tid = str(msg.get("turn_id") or "")
            meta = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else {}
            if isinstance(meta.get("datablock"), dict) and meta["datablock"]:
                return copy.deepcopy(meta["datablock"])
            if isinstance(meta.get("snapshot"), dict) and meta["snapshot"]:
                return build_datablock(meta["snapshot"], turn_index=message_index, turn_id=tid)
            data = _load(root)
            rec = (data.get("turns") or {}).get(tid) or {}
            if isinstance(rec.get("datablock"), dict) and rec["datablock"]:
                return copy.deepcopy(rec["datablock"])
            if isinstance(rec.get("snapshot"), dict) and rec["snapshot"]:
                return build_datablock(rec["snapshot"], turn_index=message_index, turn_id=tid)
    return build_datablock(fallback_state, turn_index=message_index)


def load_for_display(root: Path, history: Iterable[Dict[str, Any]], state: Optional[Dict[str, Any]] = None) -> tuple[List[Dict[str, Any]], bool]:
    """Migrate legacy embedded blocks and hydrate transient UI metadata."""
    data = _load(root)
    turns = data["turns"]
    stored: List[Dict[str, Any]] = []
    changed = False
    for raw in history or []:
        if not isinstance(raw, dict):
            continue
        message = dict(raw)
        turn_id = str(message.get("turn_id") or uuid.uuid4().hex)
        if message.get("turn_id") != turn_id:
            message["turn_id"] = turn_id
            changed = True
        record = dict(turns.get(turn_id) or {})
        if message.get("role") == "assistant":
            cleaned, legacy = _legacy_snapshot(str(message.get("content") or ""))
            if cleaned != message.get("content", ""):
                message["content"] = cleaned
                changed = True
            if legacy:
                snapshot = dict(record.get("snapshot") or {})
                snapshot.update(legacy)
                record["snapshot"] = snapshot
                changed = True
        for key in ("image_url", "image_prompt"):
            if key in message:
                media = dict(record.get("media") or {})
                media["path" if key == "image_url" else "prompt"] = message.pop(key)
                record["media"] = media
                changed = True
        if "emotion" in message:
            snapshot = dict(record.get("snapshot") or {})
            snapshot.setdefault("emotion", message.pop("emotion"))
            record["snapshot"] = snapshot
            changed = True
        if record:
            turns[turn_id] = record
        stored.append(message)
    if state is not None:
        hydrated, _ = sync_table(root, state, stored, update_latest_turn_from_current=False)
        return hydrated, changed
    if changed:
        _write(root / "history.json", stored)
        _write(_metadata_path(root), data)
    return hydrate(stored, data), changed


def hydrate(history: Iterable[Dict[str, Any]], data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Attach metadata (`datablock` + `snapshot`) for server/UI use and media fields for transport."""
    turns = (data or {}).get("turns") or {}
    result: List[Dict[str, Any]] = []
    for idx, raw in enumerate(history or []):
        message = copy.deepcopy(raw)
        turn_id = str(message.get("turn_id") or "")
        record = copy.deepcopy(turns.get(turn_id) or {})
        if record:
            if "datablock" not in record and isinstance(record.get("snapshot"), dict):
                record["datablock"] = build_datablock(record["snapshot"], turn_index=idx, turn_id=turn_id)
            message["metadata"] = record
            snapshot = record.get("snapshot") or {}
            datablock = record.get("datablock") or {}
            emotion_val = datablock.get("emotion") or snapshot.get("emotion")
            if emotion_val:
                message["emotion"] = emotion_val
            media = record.get("media") or {}
            if media.get("path"):
                message["image_url"] = media["path"]
            if media.get("prompt"):
                message["image_prompt"] = media["prompt"]
            if media.get("user_file"):
                message["user_image_path"] = media["user_file"]
        result.append(message)
    return result


def hydrate_from_disk(root: Path, history: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return hydrate(history, _load(root))


def prepare_for_storage(
    history: Iterable[Dict[str, Any]],
    root: Path,
    state: Optional[Dict[str, Any]] = None,
    *,
    update_latest_turn_from_current: bool = False,
) -> List[Dict[str, Any]]:
    """Persist clean dialogue in `history.json` and update unified Data Block table in `turn_metadata.json`."""
    if state is not None:
        _, table = sync_table(
            root,
            state,
            history,
            update_latest_turn_from_current=update_latest_turn_from_current,
        )
        # Return clean stored messages for history.json
        clean_rows: List[Dict[str, Any]] = []
        for raw in history or []:
            if not isinstance(raw, dict):
                continue
            msg = copy.deepcopy(raw)
            for transient in ("metadata", "emotion", "user_image", "user_image_path", "image_url", "image_prompt"):
                msg.pop(transient, None)
            if not msg.get("turn_id"):
                msg["turn_id"] = uuid.uuid4().hex
            clean_rows.append(msg)
        return clean_rows

    data = _load(root)
    turns = data["turns"]
    stored: List[Dict[str, Any]] = []
    new_turn_records: List[Dict[str, Any]] = []
    active_ids = set()
    for idx, raw in enumerate(history or []):
        if not isinstance(raw, dict):
            continue
        message = copy.deepcopy(raw)
        turn_id = str(message.get("turn_id") or uuid.uuid4().hex)
        message["turn_id"] = turn_id
        active_ids.add(turn_id)
        record = dict(turns.get(turn_id) or {})
        supplied = message.pop("metadata", None)
        if isinstance(supplied, dict):
            record.update(copy.deepcopy(supplied))
        snapshot = dict(record.get("snapshot") or {})
        if "emotion" in message:
            snapshot["emotion"] = message.pop("emotion")
        if snapshot:
            record["snapshot"] = snapshot
        if "datablock" not in record and snapshot:
            record["datablock"] = build_datablock(snapshot, turn_index=idx, turn_id=turn_id)
        media = dict(record.get("media") or {})
        if "user_image" in message:
            user_file = _store_user_image(root, turn_id, message.pop("user_image"))
            if user_file:
                media["user_file"] = user_file
        if "user_image_path" in message:
            media.setdefault("user_file", message.pop("user_image_path"))
        if "image_url" in message:
            media["path"] = message.pop("image_url")
        if "image_prompt" in message:
            media["prompt"] = message.pop("image_prompt")
        if media:
            record["media"] = media
        record["turn_index"] = idx
        record["turn_id"] = turn_id
        record["role"] = str(message.get("role") or "assistant")
        record["timestamp"] = float(message.get("timestamp") or time.time())
        turns[turn_id] = record
        new_turn_records.append(record)
        stored.append(message)
    removed = {turn_id: value for turn_id, value in turns.items() if turn_id not in active_ids}
    for record in removed.values():
        relative = str((record.get("media") or {}).get("user_file") or "")
        candidate = (root / relative).resolve()
        media_root = (root / "media").resolve()
        if relative and candidate.is_file() and candidate.is_relative_to(media_root):
            try:
                candidate.unlink()
            except OSError:
                pass
    data["turns"] = {turn_id: value for turn_id, value in turns.items() if turn_id in active_ids}
    data["turn_records"] = new_turn_records
    if new_turn_records and isinstance(new_turn_records[-1].get("datablock"), dict):
        data["current_datablock"] = copy.deepcopy(new_turn_records[-1]["datablock"])
    data["updated_at"] = time.time()
    _write(_metadata_path(root), data)
    return stored
