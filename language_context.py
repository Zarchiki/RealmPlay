"""Select language and linguistic register rules from the durable scene state."""
from pathlib import Path
from typing import Any, Dict

import normal_scene_state
import scene_state


def _section(root: Path, language: str, stage: str) -> str:
    filename = "Thai.md" if language == "thai" else "English.md"
    try:
        raw = (root / filename).read_text(encoding="utf-8")
    except OSError:
        return ""
    part = raw.split(f"## {stage}", 1)
    return part[1].split("\n## ", 1)[0].strip() if len(part) == 2 else ""


def active_stage(state: Dict[str, Any]) -> str:
    if scene_state.is_active(state.get("scene_state")):
        return scene_state.normalize(state.get("scene_state"))["stage"]
    return normal_scene_state.normalize(state.get("normal_scene_state"))["stage"]


def rule_blocks(language: str, state: Dict[str, Any]) -> str:
    stage = active_stage(state)
    language_rule = _section(Path("rules") / "language" / "context", language, stage)
    linguistic_rule = _section(Path("rules") / "linguistic" / "context", language, stage)
    blocks = []
    if language_rule:
        blocks.append(f"[Language Register: {stage}]\n{language_rule}")
    if linguistic_rule:
        blocks.append(f"[Linguistic Register: {stage}]\n{linguistic_rule}")
    return "\n\n".join(blocks)
