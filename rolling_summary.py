"""Persisted rolling conversation summary per user + character.

Older turns fall out of the (small) prompt window.  This module keeps one
compact summary in ``users/<user>/<char>/rolling_summary.json`` that is refreshed
incrementally after a reply, so the model keeps long-range continuity without
growing the prompt.  The summarizer is injected, so this module has no LLM or
server.py dependency.
"""

import hashlib
import json
import os
import threading
from typing import Any, Callable, Dict, List, Optional

from app.services.context_utils import estimate_context_tokens

FILE_NAME = "rolling_summary.json"
KEEP_RECENT = 4          # newest messages stay verbatim in the prompt window
TRIGGER_TOKENS = 600     # summarize once this many uncovered older tokens exist
BATCH_MESSAGES = 10      # summarizer reads at most this many messages per call
MAX_BATCHES = 2          # bound LLM calls per refresh
MAX_SUMMARY_CHARS = 900

_inflight: set = set()
_inflight_lock = threading.Lock()


def _path(users_root: str, user: str, char: str) -> str:
    return os.path.join(users_root, user, char, FILE_NAME)


def _fingerprint(message: Dict[str, Any]) -> str:
    return hashlib.sha1(str(message.get("content", "")).encode("utf-8")).hexdigest()[:16]


def _usable(message: Any) -> bool:
    return isinstance(message, dict) and message.get("role") in {"user", "assistant"} \
        and bool(str(message.get("content", "")).strip())


def load(users_root: str, user: str, char: str) -> Dict[str, Any]:
    try:
        with open(_path(users_root, user, char), encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {"summary": "", "covered": 0, "fingerprint": ""}


def load_text(users_root: str, user: str, char: str) -> str:
    return str(load(users_root, user, char).get("summary", "") or "")


def _save(users_root: str, user: str, char: str, data: Dict[str, Any]) -> None:
    path = _path(users_root, user, char)
    if not os.path.isdir(os.path.dirname(path)):
        return  # never recreate a deleted character profile
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    os.replace(tmp, path)


def pending_messages(history: List[Dict[str, Any]], covered: int) -> List[Dict[str, Any]]:
    """Messages older than the recent window that are not yet summarized."""
    end = max(0, len(history) - KEEP_RECENT)
    return [m for m in history[covered:end] if _usable(m)]


def needs_refresh(users_root: str, user: str, char: str, history: List[Dict[str, Any]]) -> bool:
    data = load(users_root, user, char)
    covered = int(data.get("covered", 0) or 0)
    if covered > len(history):
        return bool(pending_messages(history, 0))
    pending = pending_messages(history, covered)
    return sum(estimate_context_tokens(m.get("content", "")) for m in pending) >= TRIGGER_TOKENS


def refresh(
    users_root: str, user: str, char: str, history: List[Dict[str, Any]],
    summarizer: Callable[[List[Dict[str, Any]], str], str],
) -> bool:
    """Run summarizer over new older turns. Blocking; call from a worker thread.

    ``summarizer(messages, previous_summary)`` returns the new full summary, or
    "" on failure (the stored summary is then left unchanged).
    """
    key = (user, char)
    with _inflight_lock:
        if key in _inflight:
            return False
        _inflight.add(key)
    try:
        data = load(users_root, user, char)
        covered = int(data.get("covered", 0) or 0)
        summary = str(data.get("summary", "") or "")
        # History edited/deleted/reset since last time: restart from scratch.
        stale = covered > len(history) or (
            covered > 0 and _fingerprint(history[covered - 1]) != data.get("fingerprint")
        )
        if stale:
            covered, summary = 0, ""
        changed = False
        end = max(0, len(history) - KEEP_RECENT)
        pending_tokens = sum(
            estimate_context_tokens(m.get("content", "")) for m in pending_messages(history, covered)
        )
        if pending_tokens < TRIGGER_TOKENS:
            if stale:
                _save(users_root, user, char, {"summary": "", "covered": 0, "fingerprint": ""})
            return False
        for _ in range(MAX_BATCHES):
            batch_idx = []
            i = covered
            while i < end and len(batch_idx) < BATCH_MESSAGES:
                if _usable(history[i]):
                    batch_idx.append(i)
                i += 1
            batch = [history[j] for j in batch_idx]
            if not batch:
                break
            result = (summarizer(batch, summary) or "").strip()
            if not result:
                break
            summary = result[:MAX_SUMMARY_CHARS]
            covered = i
            changed = True
        if changed or stale:
            data = {
                "summary": summary,
                "covered": covered,
                "fingerprint": _fingerprint(history[covered - 1]) if covered else "",
            }
            _save(users_root, user, char, data)
        return changed
    finally:
        with _inflight_lock:
            _inflight.discard(key)
