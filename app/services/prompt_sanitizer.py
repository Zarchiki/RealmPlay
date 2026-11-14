"""Deterministic image-prompt tag sanitizer (standalone, no server.py dependency)."""

from typing import Iterable, List


def _split_tags(prompt: str) -> List[str]:
    return [t.strip() for t in (prompt or "").split(",") if t.strip()]


def sanitize_prompt(prompt: str, removed_terms: Iterable[str] = ()) -> str:
    """Drop duplicate tags and any tag containing a removed wardrobe term."""
    removed = [r.lower().strip() for r in removed_terms if r and r.strip()]
    seen = set()
    out = []
    for tag in _split_tags(prompt):
        key = tag.lower()
        if key in seen:
            continue
        if any(r in key for r in removed):
            continue
        seen.add(key)
        out.append(tag)
    return ", ".join(out)

