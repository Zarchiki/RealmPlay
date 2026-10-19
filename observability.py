"""Inspectable rule registry and bounded per-user generation activity traces."""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
import os
import subprocess
from collections import deque
from pathlib import Path


RULES = {
    "system_instruction": {"stage": "llm", "description": "Character Card, user context, and active state sent as the LLM system instruction."},
    "language_adaptation": {"stage": "llm/tts", "description": "Selects Thai or English from the latest user message and applies it only to every user-facing AI response, including TTS dialogue."},
    "self_recognition": {"stage": "llm", "description": "Makes the character aware of its card identity, appearance, personality, memories, current situation, outfit, emotion, recent actions, and location without inventing missing facts."},
    "non_literal_writing": {"stage": "llm", "description": "Roleplay formatting, natural scene progression, anti-repetition, and no assistant-like prose."},
    "loop_guard": {"stage": "llm/output", "description": "Caps corrective retries at one, compares against recent replies, and removes adjacent duplicate output blocks."},
    "prohibitions": {"stage": "llm/output", "description": "Prevents hidden reasoning, fake tool outcomes, system-prompt disclosure, control of the user's character, and malformed internal state from being shown."},
    "pronoun": {"stage": "llm", "description": "Thai pronouns and ending particles selected from relationship, hierarchy, and emotion."},
    "expressive_vocalization": {"stage": "llm/tts", "description": "Allows natural interjections, breaths, laughs, gasps, and short vocal reactions only when the immediate roleplay context and character voice support them."},
    "time_recognition": {"stage": "state/llm/image", "description": "Keeps an explicit story clock and place when a validated {{time}} state block changes them."},
    "emotional_clarity": {"stage": "state/llm/image", "description": "Keeps emotion name, intensity, and a short cause when a validated {{emotion}} block changes them."},
    "time_recognition": {"stage": "state/llm/image", "description": "Keeps an explicit story clock and place when a validated {{time}} state block changes them."},
    "emotional_clarity": {"stage": "state/llm/image", "description": "Keeps emotion name, intensity, and a short cause when a validated {{emotion}} block changes them."},
    "proactive_state": {"stage": "llm", "description": "Always-active fenced Status, Situation, and Emotion snapshots update isolated state on every dialogue reply; memory records only new durable facts."},
    "image_trigger": {"stage": "image", "description": "ComfyUI is called only for an explicit image request or an image-generation command."},
    "image_context": {"stage": "image", "description": "Scene/action first, then per-user appearance, wardrobe, emotion, configured situation/memory, and suffix."},
    "wardrobe": {"stage": "state/image", "description": "Uses the active wardrobe selection. Automatic clothing changes are opt-in and require a canonical {{wardrobe}} state block."},
    "tts_dialogue": {"stage": "tts", "description": "Sends quoted dialogue to TTS; falls back to the complete supplied text when no dialogue is found."},
    "nsfw": {"stage": "policy", "description": "A visible policy mode is included with every request. It never silently rewrites the configured local prompts."},
}

DEFAULT_RULE_SETTINGS = {
    "proactive_state": True,
    "proactive_auto_reply": True,
    "loop_guard": True,
    "prohibitions": True,
    "expressive_vocalization": True,
    "image_trigger": True,
    "auto_wardrobe": False,
    "nsfw_mode": "local",  # local | fade_to_black | block
    "trace_prompts": True,
}


def resource_snapshot():
    """Best-effort local process/VRAM snapshot; never blocks generation."""
    snapshot = {"process_ram_mb": None, "process_cpu_percent": None, "gpu_vram_used_mb": None,
                "gpu_vram_total_mb": None}
    try:
        import psutil
        process = psutil.Process(os.getpid())
        snapshot["process_ram_mb"] = round(process.memory_info().rss / 1024 / 1024, 1)
        snapshot["process_cpu_percent"] = round(process.cpu_percent(interval=None), 1)
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=1, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        first = result.stdout.splitlines()[0].split(",")
        snapshot["gpu_vram_used_mb"] = int(first[0].strip())
        snapshot["gpu_vram_total_mb"] = int(first[1].strip())
    except Exception:
        pass
    return snapshot


class ActivityRegistry:
    def __init__(self):
        self._lock = threading.RLock()
        self._active: dict[str, dict] = {}
        self._aborters: dict[str, object] = {}
        self._recent: deque[dict] = deque(maxlen=80)
        Path("logs").mkdir(exist_ok=True)
        self._logger = logging.getLogger("realmplay.activity")
        if not self._logger.handlers:
            handler = logging.FileHandler(Path("logs") / "rule-activity.log", encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def start(self, user: str, operation: str, rules=()):
        run_id = uuid.uuid4().hex[:12]
        record = {"id": run_id, "user": user, "operation": operation, "status": "running", "progress": 1,
                  "stage": "Starting", "rules": list(dict.fromkeys(rules)), "started_at": time.time(),
                  "updated_at": time.time(), "duration_ms": 0, "error": None, "prompts": {}, "cancel_requested": False,
                  "resources_start": resource_snapshot(), "resources_end": None}
        with self._lock:
            self._active[run_id] = record
        self._log(record)
        return run_id

    def update(self, run_id: str, stage: str, progress: int, rules=(), prompt_name=None, prompt=None):
        with self._lock:
            record = self._active.get(run_id)
            if not record:
                return
            record["stage"] = stage
            record["progress"] = max(1, min(99, int(progress)))
            record["updated_at"] = time.time()
            record["duration_ms"] = round((record["updated_at"] - record["started_at"]) * 1000)
            record["resources_end"] = resource_snapshot()
            record["rules"] = list(dict.fromkeys([*record["rules"], *rules]))
            if prompt_name and prompt is not None:
                record["prompts"][prompt_name] = prompt
            self._log(record)

    def finish(self, run_id: str, error: str | None = None):
        with self._lock:
            self._aborters.pop(run_id, None)
            record = self._active.pop(run_id, None)
            if not record:
                return
            cancelled = record.get("cancel_requested")
            record["status"] = "cancelled" if cancelled else ("error" if error else "complete")
            record["stage"] = "Cancelled" if cancelled else ("Failed" if error else "Complete")
            record["progress"] = 100 if not error else record["progress"]
            record["error"] = error
            record["updated_at"] = time.time()
            record["duration_ms"] = round((record["updated_at"] - record["started_at"]) * 1000)
            self._recent.appendleft(record.copy())
            self._log(record, logging.ERROR if error else logging.INFO)

    def request_cancel(self, run_id: str, user: str) -> bool:
        with self._lock:
            record = self._active.get(run_id)
            if not record or record["user"] != user:
                return False
            record["cancel_requested"] = True
            record["stage"] = "Cancellation requested"
            record["updated_at"] = time.time()
            self._log(record)
            aborter = self._aborters.get(run_id)
        if aborter:
            try:
                aborter()
            except Exception:
                pass
        return True

    def set_aborter(self, run_id: str, aborter) -> None:
        with self._lock:
            if run_id not in self._active:
                return
            if aborter is None:
                self._aborters.pop(run_id, None)
            else:
                self._aborters[run_id] = aborter

    def is_cancelled(self, run_id: str) -> bool:
        with self._lock:
            return bool(self._active.get(run_id, {}).get("cancel_requested"))

    def snapshot(self, user: str):
        with self._lock:
            active = [self._public(r) for r in self._active.values() if r["user"] == user]
            recent = [self._public(r) for r in self._recent if r["user"] == user]
        return {"active": active, "recent": recent[:12]}

    def statistics(self, user: str):
        """Small, per-user summary suitable for the UI and log review."""
        with self._lock:
            runs = [r.copy() for r in self._recent if r["user"] == user]
        grouped = {}
        for run in runs:
            item = grouped.setdefault(run["operation"], {"count": 0, "complete": 0, "error": 0, "cancelled": 0, "total_ms": 0})
            item["count"] += 1
            item[run["status"]] = item.get(run["status"], 0) + 1
            item["total_ms"] += run["duration_ms"]
        for item in grouped.values():
            item["average_ms"] = round(item["total_ms"] / item["count"]) if item["count"] else 0
        latest = self._public(runs[0]) if runs else None
        return {"operations": grouped, "latest": latest, "retained_runs": len(runs)}

    @staticmethod
    def _public(record):
        return {k: v for k, v in record.items() if k != "user"}

    def _log(self, record, level=logging.INFO):
        msg = json.dumps({k: v for k, v in self._public(record).items() if k != "prompts"}, ensure_ascii=False)
        self._logger.log(level, msg)
        print(f"[RealmPlay][{record['operation']}][{record['id']}] {record['progress']}% {record['stage']} rules={','.join(record['rules'])}")


ACTIVITY = ActivityRegistry()
