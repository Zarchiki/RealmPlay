"""Stage-aware continuity rules for wardrobe, inventory, and emotion."""
from pathlib import Path
from typing import Any, Dict
import language_context


def _section(kind: str, language: str, stage: str) -> str:
    filename = "Thai.md" if language == "thai" else "English.md"
    try:
        raw = (Path("rules") / kind / filename).read_text(encoding="utf-8")
    except OSError:
        return ""
    for key in (stage, "default"):
        part = raw.split(f"## {key}", 1)
        if len(part) == 2:
            return part[1].split("\n## ", 1)[0].strip()
    return ""


def rules(language: str, state: Dict[str, Any], trigger: str) -> str:
    stage = language_context.active_stage(state)
    folded = (trigger or "").casefold()
    selected = [("nonliteral", "default"), ("wardrobe", stage), ("emotion", stage)]
    if any(word in folded for word in ("inventory", "item", "give", "use", "trade", "ไอเทม", "ของ", "ให้", "ใช้", "แลก")):
        selected.append(("inventory", "activity"))
    blocks = []
    for kind, rule_stage in selected:
        text = _section(kind, language, rule_stage)
        if text:
            blocks.append(f"[{kind.title()} Continuity]\n{text}")
    return "\n\n".join(blocks)
