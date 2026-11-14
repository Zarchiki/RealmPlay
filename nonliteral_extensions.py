"""Optional nonliteral prompt experiments.  The base rule remains the default."""
import json
from pathlib import Path


ROOT = Path("rules") / "nonliteral" / "extensions"


def active_blocks(language: str) -> str:
    try:
        config = json.loads(Path("config.json").read_text(encoding="utf-8"))
        selected = config.get("rules", {}).get("nonliteral_extensions", [])
    except (OSError, ValueError):
        selected = []
    if not isinstance(selected, list):
        return ""
    filename = "Thai.md" if language == "thai" else "English.md"
    blocks = []
    for name in selected:
        safe = str(name).strip().lower().replace("_", "-")
        if safe not in {"final-contract", "style-quarantine", "motif-budget", "direct-dialogue"}:
            continue
        try:
            text = (ROOT / safe / filename).read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            blocks.append(f"[Nonliteral Extension: {safe}]\n{text}")
    return "\n\n".join(blocks)
