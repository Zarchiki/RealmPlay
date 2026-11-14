"""Safe lookup of generated images referenced by chat history."""

import os
from pathlib import Path
from typing import Any, Dict, List


def generated_images(history: List[Dict[str, Any]], generated_root: Path = Path("generated_images")) -> List[Dict[str, str]]:
    """Return existing image files referenced by a character's chat history."""
    root = generated_root.resolve()
    images: List[Dict[str, str]] = []
    seen = set()
    for message in reversed(history or []):
        raw_url = str(message.get("image_url") or "")
        filename = os.path.basename(raw_url.split("?", 1)[0])
        candidate = (root / filename).resolve()
        if not filename or filename in seen or candidate.parent != root or not candidate.is_file():
            continue
        seen.add(filename)
        images.append({
            "kind": "generated", "url": f"/images/{filename}",
            "turn_id": str(message.get("turn_id") or ""),
        })
    return images
