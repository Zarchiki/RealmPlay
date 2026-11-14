"""Audio cache maintenance for generated TTS/RVC files (standalone, no server.py dependency)."""

import os
import time
from typing import Dict, List

AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".m4a")


def _audio_files(directory: str) -> List[str]:
    if not os.path.isdir(directory):
        return []
    return [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name.lower().endswith(AUDIO_EXTENSIONS) and os.path.isfile(os.path.join(directory, name))
    ]


def cache_stats(directory: str) -> Dict[str, int]:
    files = _audio_files(directory)
    return {"files": len(files), "bytes": sum(os.path.getsize(f) for f in files)}


def prune_audio_cache(directory: str, max_age_hours: float = 48, max_total_mb: float = 500) -> Dict[str, int]:
    """Delete audio older than max_age_hours, then oldest-first until under max_total_mb."""
    removed = freed = 0
    now = time.time()
    files = sorted(_audio_files(directory), key=os.path.getmtime)
    keep = []
    for path in files:
        if now - os.path.getmtime(path) > max_age_hours * 3600:
            try:
                size = os.path.getsize(path)
                os.remove(path)
                removed += 1
                freed += size
            except OSError:
                keep.append(path)
        else:
            keep.append(path)
    total = sum(os.path.getsize(f) for f in keep)
    limit = int(max_total_mb * 1024 * 1024)
    for path in keep:
        if total <= limit:
            break
        try:
            size = os.path.getsize(path)
            os.remove(path)
            total -= size
            removed += 1
            freed += size
        except OSError:
            pass
    return {"removed": removed, "freed_bytes": freed}

