"""Pending account requests; approval happens locally, outside the public API."""
import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUESTS_FILE = ROOT / "data" / "registration_requests.json"
_lock = threading.Lock()
_username_re = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
_email_re = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _read():
    if not REQUESTS_FILE.exists():
        return []
    with REQUESTS_FILE.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, list):
        raise ValueError("Registration request file must contain a list")
    return data


def _write(rows):
    REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="registration-", suffix=".json", dir=REQUESTS_FILE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(rows, stream, ensure_ascii=False, indent=2)
        os.replace(temp_name, REQUESTS_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def request_account(username, email, auth_file=None):
    username, email = username.strip(), email.strip().lower()
    if not _username_re.fullmatch(username):
        raise ValueError("ID ต้องมี 3–32 ตัว ใช้ตัวอักษรอังกฤษ ตัวเลข _ หรือ -")
    if len(email) > 254 or not _email_re.fullmatch(email):
        raise ValueError("กรุณาระบุอีเมลที่ถูกต้อง")
    auth_file = Path(auth_file) if auth_file else ROOT / "data" / "auth.json"
    with _lock:
        if auth_file.exists():
            with auth_file.open(encoding="utf-8") as stream:
                accounts = json.load(stream)
            if any(name.casefold() == username.casefold() for name in accounts):
                raise ValueError("ID นี้มีบัญชีอยู่แล้ว")
        rows = _read()
        if any(row["username"].casefold() == username.casefold() and row["status"] == "pending" for row in rows):
            raise ValueError("ID นี้มีคำขอรออนุมัติอยู่แล้ว")
        rows.append({"username": username, "email": email, "status": "pending", "requested_at": int(time.time())})
        _write(rows)
    return {"ok": True, "message": "รับคำขอแล้ว ผู้ดูแลจะตรวจสอบและส่งข้อมูลเข้าระบบทางอีเมล"}


def list_requests():
    with _lock:
        return _read()


def mark_approved(username):
    with _lock:
        rows = _read()
        row = next((item for item in rows if item["username"] == username and item["status"] == "pending"), None)
        if row is None:
            raise ValueError("ไม่พบคำขอที่รออนุมัติ")
        row["status"] = "approved"
        row["approved_at"] = int(time.time())
        _write(rows)
        return row["email"]
