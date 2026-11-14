"""Durable memory deduplication and retention rules."""

import re


def append(current_memory: str, fact: str) -> str:
    if not fact or not fact.strip():
        return (current_memory or "").strip()

    ignored = {"none", "n/a", "null", "no new permanent memories", "no new memories", "ไม่มี", "ไม่มีเหตุการณ์ใหม่ที่ยั่งยืนเกิดขึ้นในเทิร์นนี้"}

    existing = [
        line.strip(" -\t") for line in (current_memory or "").splitlines()
        if line.strip() and "ไม่มีเหตุการณ์ใหม่" not in line and line.strip(" -\t()").casefold() not in {"none", "n/a"}
    ]
    existing_lowered = {line.casefold() for line in existing}

    for raw_line in fact.splitlines():
        cleaned_line = re.sub(r"\s+", " ", raw_line).strip(" -\t\r\n")
        if not cleaned_line:
            continue
        lowered = cleaned_line.casefold().strip("()")
        if lowered in ignored or "ไม่มีเหตุการณ์ใหม่" in lowered:
            continue
        if lowered not in existing_lowered:
            existing.append(cleaned_line)
            existing_lowered.add(lowered)

    return "\n".join(f"- {line}" for line in existing[-80:])
