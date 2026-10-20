"""SQLite index for durable per-user RealmPlay state; source files stay intact."""
from __future__ import annotations
import json, sqlite3, threading, time
from pathlib import Path
from typing import Any, Dict

DB_PATH = Path("data") / "realmplay_state.sqlite"
_LOCK = threading.RLock()
INDEXED_KEYS = ("memory", "scenario", "status", "emotion", "emotion_detail", "time_state")

def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=3)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS character_state (username TEXT NOT NULL, character_name TEXT NOT NULL, state_key TEXT NOT NULL, value_json TEXT NOT NULL, updated_at REAL NOT NULL, PRIMARY KEY (username, character_name, state_key))")
    return conn

def load(username: str, character_name: str) -> Dict[str, Any]:
    try:
        with _LOCK, _connect() as conn:
            rows = conn.execute("SELECT state_key, value_json FROM character_state WHERE username=? AND character_name=?", (username, character_name)).fetchall()
        return {key: json.loads(value) for key, value in rows}
    except Exception:
        return {}

def save(username: str, character_name: str, updates: Dict[str, Any]) -> None:
    records = [(key, updates[key]) for key in INDEXED_KEYS if key in updates]
    if not records: return
    try:
        with _LOCK, _connect() as conn:
            conn.executemany("INSERT INTO character_state(username, character_name, state_key, value_json, updated_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(username, character_name, state_key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at", [(username, character_name, key, json.dumps(value, ensure_ascii=False), time.time()) for key, value in records])
    except Exception:
        return
