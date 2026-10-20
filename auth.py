"""Authentication and User Profile Management for RealmPlay.

Supports:
- Hashed password verification (PBKDF2-HMAC-SHA256)
- User profile isolation
- Session tokens for Port 8000 Remote Play & Local login
"""
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from typing import Optional, Dict, Any

AUTH_FILE = "data/auth.json"
SESSIONS_FILE = "data/sessions.json"
_sessions_lock = threading.RLock()

def _ensure_data_dir():
    os.makedirs("data", exist_ok=True)
    os.makedirs("users", exist_ok=True)
    if not os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
    if not os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${hashed.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected_hex = stored_hash.split("$", 1)
        actual_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hmac.compare_digest(actual_hash.hex(), expected_hex)
    except Exception:
        return False

def register_user(username: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    _ensure_data_dir()
    username = username.strip()
    if not username:
        return {"ok": False, "error": "Username cannot be empty (Username สำหรับล็อกอินต้องไม่ว่างเปล่า)"}
    if any(c in username for c in ("/", "\\", "\x00", ":")) or ".." in username or username.startswith("."):
        return {"ok": False, "error": "Invalid username characters (ห้ามใช้ / \\ : หรือ ..)"}
    if len(password) < 4:
        return {"ok": False, "error": "Password must be at least 4 characters (รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร)"}

    with open(AUTH_FILE, "r", encoding="utf-8") as f:
        auth_data = json.load(f)

    if username in auth_data:
        return {"ok": False, "error": "Username already exists (ชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว)"}

    name_to_use = display_name.strip() if display_name and display_name.strip() else username
    auth_data[username] = {
        "password": hash_password(password),
        "created_at": time.time(),
        "display_name": name_to_use
    }

    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(auth_data, f, indent=2, ensure_ascii=False)

    # Initialize isolated user folder
    user_dir = os.path.join("users", username)
    os.makedirs(user_dir, exist_ok=True)
    user_settings = os.path.join(user_dir, "settings.json")
    if not os.path.exists(user_settings):
        with open(user_settings, "w", encoding="utf-8") as f:
            json.dump({
                "theme": "dark",
                "tts_voice": "th-TH-PremwadeeNeural",
                "tts_speed": "+0%",
                "tts_pitch": 0,
                "language": "th"
            }, f, indent=2, ensure_ascii=False)

    return {"ok": True, "message": "Registered successfully"}

def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    _ensure_data_dir()
    username = username.strip()
    with open(AUTH_FILE, "r", encoding="utf-8") as f:
        auth_data = json.load(f)

    user_info = auth_data.get(username)
    if not user_info or not verify_password(password, user_info["password"]):
        return {"ok": False, "error": "Invalid username or password (ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง)"}

    # One account owns one active browser session.  A new login deliberately
    # invalidates old PC/mobile sessions so concurrent edits cannot overwrite
    # each other silently.
    token = secrets.token_urlsafe(32)
    with _sessions_lock:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            sessions = json.load(f)
        revoked = sum(1 for session in sessions.values() if session.get("username") == username)
        sessions = {key: session for key, session in sessions.items() if session.get("username") != username}
        sessions[token] = {
            "username": username,
            "created_at": time.time(),
            "expires_at": time.time() + (30 * 86400) # 30 days
        }
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)

    display_name = user_info.get("display_name") or username
    return {"ok": True, "token": token, "username": username, "display_name": display_name,
            "previous_session_revoked": bool(revoked)}

def validate_token(token: str) -> Optional[str]:
    """Validates session token and returns username if valid."""
    _ensure_data_dir()
    if not token:
        return None
    try:
        with _sessions_lock:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                sessions = json.load(f)
        session = sessions.get(token)
        if not session:
            return None
        if time.time() > session.get("expires_at", 0):
            return None
        return session.get("username")
    except Exception:
        return None

def revoke_token(token: str) -> None:
    """Sign out one browser session without affecting other users or tabs."""
    _ensure_data_dir()
    with _sessions_lock:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            sessions = json.load(f)
        if token in sessions:
            del sessions[token]
            with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(sessions, f, indent=2, ensure_ascii=False)

def get_user_display_name(username: str) -> str:
    """Returns character-facing display name of user, defaulting to username."""
    prof = get_user_profile(username)
    return prof.get("display_name") or username

def get_user_profile(username: str) -> Dict[str, Any]:
    """Returns user profile dictionary (display_name, persona, bio)."""
    _ensure_data_dir()
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            auth_data = json.load(f)
        info = auth_data.get(username, {})
        display_name = info.get("display_name") or username
        persona = info.get("persona") or ""
        return {
            "username": username,
            "display_name": display_name,
            "persona": persona
        }
    except Exception:
        return {"username": username, "display_name": username, "persona": ""}

def update_user_profile(username: str, display_name: Optional[str] = None, persona: Optional[str] = None) -> bool:
    """Updates user profile (display_name and character-facing user persona/bio)."""
    _ensure_data_dir()
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            auth_data = json.load(f)
        if username in auth_data:
            if display_name is not None:
                auth_data[username]["display_name"] = display_name.strip() or username
            if persona is not None:
                auth_data[username]["persona"] = persona.strip()
            with open(AUTH_FILE, "w", encoding="utf-8") as f:
                json.dump(auth_data, f, indent=2, ensure_ascii=False)
            return True
        return False
    except Exception:
        return False

def update_user_display_name(username: str, display_name: str) -> bool:
    """Updates character-facing name of user."""
    return update_user_profile(username, display_name=display_name)

def list_users():
    _ensure_data_dir()
    with open(AUTH_FILE, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
    return list(auth_data.keys())

def reset_password(username: str, new_password: str) -> Dict[str, Any]:
    """Admin or direct reset of user password."""
    _ensure_data_dir()
    username = username.strip()
    if len(new_password) < 4:
        return {"ok": False, "error": "Password must be at least 4 characters (รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร)"}
    with open(AUTH_FILE, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
    if username not in auth_data:
        return {"ok": False, "error": "User not found (ไม่พบบัญชีผู้ใช้นี้)"}
    auth_data[username]["password"] = hash_password(new_password)
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(auth_data, f, indent=2, ensure_ascii=False)
    # Revoke active sessions for that user so they must log in with new password
    with _sessions_lock:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            sessions = json.load(f)
        sessions = {k: v for k, v in sessions.items() if v.get("username") != username}
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
    return {"ok": True, "message": "Password updated successfully"}

ADMIN_USERS = {"Zarch", "admin"}

def is_admin_user(username: str) -> bool:
    """Checks whether the given username has administrative rights."""
    return bool(username and (username.strip() in ADMIN_USERS or username.strip().lower() in {"zarch", "admin"}))

def delete_user(username: str) -> Dict[str, Any]:
    """Admin delete user account."""
    _ensure_data_dir()
    username = username.strip()
    if is_admin_user(username) and username.lower() == "zarch":
        return {"ok": False, "error": "Cannot delete primary admin account (ห้ามลบบัญชีผู้ดูแลหลัก)"}
    with open(AUTH_FILE, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
    if username not in auth_data:
        return {"ok": False, "error": "User not found (ไม่พบบัญชีผู้ใช้นี้)"}
    del auth_data[username]
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(auth_data, f, indent=2, ensure_ascii=False)
    # Revoke sessions
    with _sessions_lock:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            sessions = json.load(f)
        sessions = {k: v for k, v in sessions.items() if v.get("username") != username}
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
    return {"ok": True, "message": f"User {username} deleted successfully"}

def list_users_details() -> list:
    _ensure_data_dir()
    with open(AUTH_FILE, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
    result = []
    for uname, info in auth_data.items():
        result.append({
            "username": uname,
            "display_name": info.get("display_name") or uname,
            "is_admin": is_admin_user(uname),
            "created_at": info.get("created_at")
        })
    return result


