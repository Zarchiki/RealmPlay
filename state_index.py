"""SQLite state stores for RealmPlay profiles.

The global database is an index for cross-profile data.  Per-character runtime
state lives in ``users/<user>/<character>/profile_state.sqlite`` so deleting or
resetting that profile folder cannot resurrect its previous state.
"""
from __future__ import annotations
import json, sqlite3, threading, time
from pathlib import Path
from typing import Any, Dict

DB_PATH = Path("data") / "realmplay_state.sqlite"
_LOCK = threading.RLock()
# New profile state is never written to the global database.  This empty tuple
# remains for compatibility with callers that previously used this module.
INDEXED_KEYS: tuple[str, ...] = ()

# These values are canonical in each user-character directory's SQLite file,
# not in the global index.  Keeping the list here makes legacy cleanup explicit.
PROFILE_SQLITE_KEYS = (
    "memory", "scenario", "status", "emotion", "emotion_detail",
    "time_state", "needs_state", "character_intent", "pending_user_request",
    "datablock_table", "outfits", "inventory", "inventory_wardrobe",
    "scene_state", "arousal_state",
)
# Backward-compatible name used by the existing migration call sites.
FILE_OWNED_CHARACTER_KEYS = PROFILE_SQLITE_KEYS
PROFILE_DB_NAME = "profile_state.sqlite"
LEGACY_GLOBAL_KEYS = PROFILE_SQLITE_KEYS

def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=3)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS character_state (username TEXT NOT NULL, character_name TEXT NOT NULL, state_key TEXT NOT NULL, value_json TEXT NOT NULL, updated_at REAL NOT NULL, PRIMARY KEY (username, character_name, state_key))")
    return conn

def load(username: str, character_name: str) -> Dict[str, Any]:
    try:
        with _LOCK:
            conn = _connect()
            try:
                rows = conn.execute("SELECT state_key, value_json FROM character_state WHERE username=? AND character_name=?", (username, character_name)).fetchall()
            finally:
                conn.close()
        return {key: json.loads(value) for key, value in rows}
    except Exception:
        return {}

def save(username: str, character_name: str, updates: Dict[str, Any]) -> None:
    records = [(key, updates[key]) for key in INDEXED_KEYS if key in updates]
    if not records: return
    try:
        with _LOCK:
            conn = _connect()
            try:
                conn.executemany("INSERT INTO character_state(username, character_name, state_key, value_json, updated_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(username, character_name, state_key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at", [(username, character_name, key, json.dumps(value, ensure_ascii=False), time.time()) for key, value in records])
                conn.commit()
            finally:
                conn.close()
    except Exception:
        return


def delete_keys(username: str, character_name: str, keys: tuple[str, ...] | list[str]) -> None:
    """Remove obsolete cache rows after their file-owned migration."""
    names = tuple(str(key) for key in keys if str(key))
    if not names:
        return
    try:
        placeholders = ",".join("?" for _ in names)
        with _LOCK:
            conn = _connect()
            try:
                conn.execute(
                    f"DELETE FROM character_state WHERE username=? AND character_name=? AND state_key IN ({placeholders})",
                    (username, character_name, *names),
                )
                conn.commit()
            finally:
                conn.close()
    except Exception:
        return


def _connect_profile(profile_dir: str | Path) -> sqlite3.Connection:
    """Open the SQLite state store owned by one user-character directory."""
    root = Path(profile_dir)
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(root / PROFILE_DB_NAME, timeout=3)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS profile_state "
        "(state_key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at REAL NOT NULL)"
    )
    return conn


def load_profile(profile_dir: str | Path) -> Dict[str, Any]:
    """Load local runtime state for exactly one user-character profile."""
    try:
        if not (Path(profile_dir) / PROFILE_DB_NAME).is_file():
            return {}
        with _LOCK:
            conn = _connect_profile(profile_dir)
            try:
                rows = conn.execute("SELECT state_key, value_json FROM profile_state").fetchall()
            finally:
                conn.close()
        return {key: json.loads(value) for key, value in rows if key in PROFILE_SQLITE_KEYS}
    except Exception:
        return {}


def save_profile(profile_dir: str | Path, updates: Dict[str, Any]) -> None:
    """Persist local runtime state without duplicating it into the global DB."""
    records = [(key, updates[key]) for key in PROFILE_SQLITE_KEYS if key in updates]
    if not records:
        return
    try:
        with _LOCK:
            conn = _connect_profile(profile_dir)
            try:
                conn.executemany(
                    "INSERT INTO profile_state(state_key, value_json, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(state_key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
                    [(key, json.dumps(value, ensure_ascii=False), time.time()) for key, value in records],
                )
                conn.commit()
            finally:
                conn.close()
    except Exception:
        return


def replace_profile(profile_dir: str | Path, values: Dict[str, Any]) -> None:
    """Replace a profile SQLite state atomically with a clean default/source."""
    try:
        with _LOCK:
            conn = _connect_profile(profile_dir)
            try:
                conn.execute("DELETE FROM profile_state")
                conn.commit()
            finally:
                conn.close()
        save_profile(profile_dir, values)
    except Exception:
        return


def clone_profile(source_dir: str | Path, target_dir: str | Path) -> None:
    """Clone one character-default SQLite state store into a user profile."""
    try:
        with _LOCK:
            source = _connect_profile(source_dir)
            target = _connect_profile(target_dir)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
    except Exception:
        return


def profile_receipt(profile_dir: str | Path, through: float | None = None) -> float | None:
    """Read or update the chat receipt stored with one user-character profile."""
    try:
        with _LOCK:
            conn = _connect_profile(profile_dir)
            try:
                conn.execute("CREATE TABLE IF NOT EXISTS chat_receipt (id INTEGER PRIMARY KEY CHECK (id=1), read_at REAL NOT NULL)")
                if through is not None:
                    conn.execute(
                        "INSERT INTO chat_receipt(id, read_at) VALUES (1, ?) "
                        "ON CONFLICT(id) DO UPDATE SET read_at=MAX(read_at, excluded.read_at)",
                        (float(through),),
                    )
                    conn.commit()
                row = conn.execute("SELECT read_at FROM chat_receipt WHERE id=1").fetchone()
            finally:
                conn.close()
        return float(row[0]) if row else None
    except Exception:
        return None
