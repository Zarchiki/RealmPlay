"""Reset an existing account password locally without exposing it to the web UI."""
import getpass
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import auth


def write_json_atomic(path, payload):
    fd, temp_name = tempfile.mkstemp(prefix="account-reset-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main():
    if len(sys.argv) != 2:
        print("Usage: python reset_user_password.py ID")
        return 2
    username = sys.argv[1].strip()
    auth_path = ROOT / "data" / "auth.json"
    sessions_path = ROOT / "data" / "sessions.json"
    with auth_path.open(encoding="utf-8") as stream:
        accounts = json.load(stream)
    if username not in accounts:
        print("Account not found. Check the exact ID, including capitals.")
        return 1
    password = getpass.getpass("New password: ")
    confirmation = getpass.getpass("Confirm new password: ")
    if len(password) < 8 or password != confirmation:
        print("Passwords must match and contain at least 8 characters.")
        return 1
    backup = ROOT / "backups" / f"auth-before-reset-{int(time.time())}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(auth_path, backup)
    accounts[username]["password"] = auth.hash_password(password)
    write_json_atomic(auth_path, accounts)
    if sessions_path.exists():
        with sessions_path.open(encoding="utf-8") as stream:
            sessions = json.load(stream)
        sessions = {token: session for token, session in sessions.items() if session.get("username") != username}
        write_json_atomic(sessions_path, sessions)
    print(f"Password updated for {username}. Existing sessions were signed out; chat and profile data are unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
