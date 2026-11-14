"""Pure memory/context helpers: relevance-ranked memory under a token budget and
rolling-summary planning. No server.py dependency; wire in from callers later."""

import re
from typing import Any, Dict, List, Sequence

from app.services.context_utils import estimate_context_tokens

_WORD = re.compile(r"[A-Za-z0-9_]{2,}|[\u0E00-\u0E7F]{2,}")


def _terms(text: str) -> set:
    return {t.lower() for t in _WORD.findall(str(text or ""))}


def _bigrams(text: str) -> set:
    """Character bigrams so Thai (no spaces) still matches partially."""
    s = re.sub(r"\s+", "", str(text or "").lower())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def score_memory(fact: str, query: str) -> float:
    """Overlap score of a memory fact against the query (0..~2)."""
    ft, qt = _terms(fact), _terms(query)
    word = len(ft & qt) / max(1, len(qt)) if qt else 0.0
    fb, qb = _bigrams(fact), _bigrams(query)
    gram = len(fb & qb) / max(1, len(qb)) if qb else 0.0
    return word + gram


def select_memories(
    memory_text: str, query: str, token_budget: int = 200, max_facts: int = 5,
    recency_weight: float = 0.15,
) -> List[str]:
    """Pick the most relevant facts (newer lines get a small boost) within budget.

    Returned facts keep their original chronological order.
    """
    facts = [ln.strip() for ln in str(memory_text or "").split("\n") if ln.strip()]
    if not facts:
        return []
    n = len(facts)
    ranked = sorted(
        range(n),
        key=lambda i: score_memory(facts[i], query) + recency_weight * (i / max(1, n - 1)),
        reverse=True,
    )
    chosen, used = [], 0
    for i in ranked:
        cost = estimate_context_tokens(facts[i])
        if used + cost > token_budget:
            continue
        chosen.append(i)
        used += cost
        if len(chosen) >= max_facts:
            break
    return [facts[i] for i in sorted(chosen)]


def plan_rolling_summary(
    history: Sequence[Dict[str, Any]], keep_recent: int = 12, trigger_tokens: int = 4000,
) -> Dict[str, Any]:
    """Decide whether older turns should be summarized.

    Returns {"summarize": bool, "older": [...], "recent": [...], "tokens": int}.
    Only turns before the `keep_recent` window are candidates.
    """
    items = [h for h in (history or []) if isinstance(h, dict) and str(h.get("content", "")).strip()]
    recent = items[-max(1, keep_recent):]
    older = items[:len(items) - len(recent)]
    tokens = sum(estimate_context_tokens(h.get("content", "")) for h in older)
    return {"summarize": bool(older) and tokens >= trigger_tokens,
            "older": older, "recent": recent, "tokens": tokens}


def merge_summary(previous: str, new_part: str, max_chars: int = 1200) -> str:
    """Append a new summary chunk, trimming oldest text to stay under max_chars."""
    merged = " ".join(p.strip() for p in (previous, new_part) if p and p.strip())
    if len(merged) <= max_chars:
        return merged
    return "…" + merged[-(max_chars - 1):].lstrip()

