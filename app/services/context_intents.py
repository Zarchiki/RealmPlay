"""Deterministic intent scoring for context selection."""

from typing import Any, Dict


CONTEXT_INTENT_RULES = {
    "memory": {"strong": ("จำได้ไหม", "จำเรื่อง", "remember when", "remember our", "what happened", "ความสัมพันธ์", "เรื่องในอดีต", "สัญญาของเรา", "ความลับ"), "terms": ("memory", "remember", "relationship", "secret", "จำ", "เคย", "อดีต", "ประวัติ", "สัญญา")},
    "appearance": {"strong": ("หน้าตาเป็นยังไง", "รูปลักษณ์เป็น", "what do you look like", "describe your appearance"), "terms": ("appearance", "look", "face", "รูปลักษณ์", "หน้าตา", "ลักษณะ")},
    "wardrobe": {"strong": ("ใส่ชุดอะไร", "แต่งตัวแบบ", "what are you wearing", "describe your outfit"), "terms": ("outfit", "wardrobe", "clothes", "wearing", "แต่งตัว", "ชุด", "เสื้อ", "กางเกง")},
    "emotion": {"strong": ("รู้สึกยังไง", "อารมณ์เป็นยังไง", "how do you feel", "why are you angry", "ทำไมโกรธ", "ทำไมเศร้า"), "terms": ("emotion", "feel", "angry", "sad", "happy", "afraid", "กลัว", "โกรธ", "เศร้า", "ดีใจ", "เขิน", "รู้สึก", "อารมณ์")},
    "story_time": {"strong": ("ตอนนี้กี่โมง", "วันนี้วันอะไร", "อยู่ที่ไหน", "where are we", "what time is it", "what is the weather", "อากาศเป็นยังไง"), "terms": ("time", "date", "weather", "morning", "night", "location", "เวลา", "วัน", "อากาศ", "เช้า", "กลางคืน", "ที่ไหน")},
}


def score_context_intents(input_text: str) -> Dict[str, Dict[str, Any]]:
    """Score explicit phrases locally; no LLM call is used for routing."""
    text = (input_text or "").casefold()
    result: Dict[str, Dict[str, Any]] = {}
    for node, rules in CONTEXT_INTENT_RULES.items():
        strong = [phrase for phrase in rules["strong"] if phrase.casefold() in text]
        terms = [term for term in rules["terms"] if term.casefold() in text and term not in strong]
        score = len(strong) * 3 + min(len(terms), 2)
        if terms and len(text) <= 20:
            score = max(score, 2)
        result[node] = {"score": score, "matched": [*strong, *terms]}
    return result
