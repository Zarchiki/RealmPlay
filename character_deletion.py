"""Remove a shared character and every user's data for that character."""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Dict


def _child_path(root: Path, name: str) -> Path:
    """Return a direct child path, refusing names that escape ``root``."""
    resolved_root = root.resolve()
    target = (resolved_root / name).resolve()
    if target.parent != resolved_root:
        raise ValueError("Character name must identify a direct child directory")
    return target


def delete_character_everywhere(
    character_name: str,
    *,
    characters_root: Path | str = Path("characters"),
    users_root: Path | str = Path("users"),
    state_db: Path | str = Path("data") / "realmplay_state.sqlite",
) -> Dict[str, int | str]:
    """Delete the character card and all user-owned data associated with it.

    The caller must perform authorization before calling this irreversible
    operation.  Database rows are removed as well as the per-user directories,
    so stale history summaries and state cannot return after a re-import.
    """
    characters_root = Path(characters_root)
    users_root = Path(users_root)
    state_db = Path(state_db)
    character_dir = _child_path(characters_root, character_name)
    if not character_dir.is_dir():
        raise FileNotFoundError(character_name)

    user_character_dirs = []
    if users_root.is_dir():
        for user_dir in users_root.iterdir():
            if user_dir.is_dir():
                target = _child_path(user_dir, character_name)
                if target.is_dir():
                    user_character_dirs.append(target)

    # Validate all targets before beginning a destructive operation.
    for target in [character_dir, *user_character_dirs]:
        if not target.is_dir():
            raise FileNotFoundError(target)

    shutil.rmtree(character_dir)
    for target in user_character_dirs:
        shutil.rmtree(target)

    deleted_state_rows = 0
    deleted_receipts = 0
    if state_db.exists():
        connection = sqlite3.connect(state_db)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "character_state" in tables:
                cursor = connection.execute(
                    "DELETE FROM character_state WHERE character_name=?", (character_name,)
                )
                deleted_state_rows = max(cursor.rowcount, 0)
            if "chat_receipts" in tables:
                cursor = connection.execute(
                    "DELETE FROM chat_receipts WHERE character_name=?", (character_name,)
                )
                deleted_receipts = max(cursor.rowcount, 0)
            connection.commit()
        finally:
            connection.close()

    return {
        "deleted_character": character_name,
        "deleted_user_histories": len(user_character_dirs),
        "deleted_state_rows": deleted_state_rows,
        "deleted_receipts": deleted_receipts,
    }
