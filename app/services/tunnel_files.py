"""Filesystem and process helpers for the Cloudflare tunnel lifecycle."""

import json
import os
import re
import shutil
from typing import Any, Optional


def read_state(state_file: str) -> dict:
    try:
        with open(state_file, "r", encoding="utf-8") as file:
            state = json.load(file)
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(state_file: str, pid: int, url: Optional[str]) -> None:
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    temporary_file = state_file + ".tmp"
    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump({"pid": int(pid), "url": url}, file, ensure_ascii=False)
    os.replace(temporary_file, state_file)


def clear_state(state_file: str) -> None:
    try:
        os.remove(state_file)
    except FileNotFoundError:
        pass


def pid_is_running(pid: Any) -> bool:
    try:
        pid = int(pid)
        if pid <= 0:
            return False
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return False
            try:
                exit_code = wintypes.DWORD()
                return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) and exit_code.value == 259)
            finally:
                kernel32.CloseHandle(handle)
        os.kill(pid, 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def cloudflared_exe(app_dir: str) -> Optional[str]:
    bundled = os.path.join(app_dir, "runtime", "cloudflared", "cloudflared.exe")
    return bundled if os.path.isfile(bundled) else shutil.which("cloudflared")


def find_public_url(log_file: str) -> Optional[str]:
    if not os.path.exists(log_file):
        return None
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as file:
            matches = re.findall(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", file.read())
        return matches[-1] if matches else None
    except OSError:
        return None


def log_tail(log_file: str, limit: int = 4000) -> str:
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as file:
            file.seek(0, os.SEEK_END)
            file.seek(max(0, file.tell() - limit))
            return file.read().strip()
    except OSError:
        return ""
