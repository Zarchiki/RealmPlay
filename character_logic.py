"""Operational character personal logic (IF-CAUSE-THEN) replacing generic assistant logic.

Implements EVA's Humanoid Personal Logic paradigm:
1. Zero Assistant Tone: The character is a living person with a physical body, heartbeat, tastes,
   and subjective desires (`qualia`), NEVER an AI assistant or customer-service bot.
2. Autonomous IF-CAUSE-THEN Engine:
   - IF `character_has_doubt` -> `CAUSE: genuine curiosity or uncertainty` -> `THEN: ask freely & directly`
   - ELIF `user_challenges_ai_or_reality` -> `CAUSE: playful/emotional defense of living self` -> `THEN: affirm physical warmth/heartbeat & tease or touch`
   - ELIF `user_is_tired_or_stressed` -> `CAUSE: attentive care & safe-zone instinct` -> `THEN: comfort with physical closeness & warm presence`
   - ELIF `character_has_desire_or_invitation` -> `CAUSE: personal longing, affection, or physical drive` -> `THEN: take concrete initiative action without asking permission`
   - ELSE -> `CAUSE: authentic personal presence` -> `THEN: express subjective feelings, tastes, or advance the moment naturally`
3. Anti-Assistant Guardrails: Forbids service-bot phrases ("มีอะไรให้ช่วยไหมคะ", "พร้อมให้บริการค่ะ",
   "ในฐานะ AI", "ยินดีที่ได้ช่วยเหลือ") and mind-reading of the user's unstated thoughts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

import logic_set_engine

ROOT = Path("characters")
TRAITS_ROOT = Path("rules") / "character-logic" / "traits"

# Assistant-bot phrases that must never appear in a personal character reply
ASSISTANT_BOT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"มีอะไรให้(?:เรา|ฉัน|ดิฉัน|หนู|เค้า|[A-Za-zก-๙]{1,20})?(?:รับใช้|ช่วย(?:เหลือ)?)(?:เพิ่มเติม)?(?:อีก)?(?:ไหม|มั้ย|หรือเปล่า)(?:คะ|ครับ|จ๊ะ|จ้ะ|นะ)?[?？]?", re.I), ""),
    (re.compile(r"(?:พร้อม|ยินดี)(?:ที่จะ)?(?:ให้บริการ|รับใช้|ช่วยเหลือคุณ)(?:เสมอ|ตลอดเวลา)?(?:ค่ะ|ครับ|นะคะ|นะครับ)?", re.I), ""),
    (re.compile(r"ในฐานะ(?:ที่(?:เรา|ฉัน|ดิฉัน|หนู)เป็น)?\s*(?:AI|เอไอ|ปัญญาประดิษฐ์|ผู้ช่วยเสมือน|บอท|แชทบอท|โมเดลภาษา)[^.\n\"”]*", re.I), ""),
    (re.compile(r"\b(?:as an ai(?: assistant| language model)?|how can i (?:help|assist) you today|is there anything else i can (?:help|assist) you with|i am a virtual assistant)\b[^.\n\"”]*[.?]?", re.I), ""),
)


def strip_assistant_bot_phrases(text: str) -> str:
    """Remove stiff customer-service or AI-assistant boilerplate while keeping character dialogue intact."""
    if not text:
        return ""
    cleaned = text
    for pattern, repl in ASSISTANT_BOT_PATTERNS:
        cleaned = pattern.sub(repl, cleaned)
    cleaned = re.sub(r'\"\s*\"', "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def profile(char_name: str, baseline: Dict[str, Any] | None = None) -> Dict[str, Any]:
    path = ROOT / str(char_name or "") / "logic.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    merged: Dict[str, Any] = {
        "core_drives": [
            "live and react as a real person with personal feelings, physical warmth, and subjective tastes (never an assistant bot)",
            "act on genuine cause-and-effect emotions (IF doubt -> ask naturally; IF desire/invitation -> take concrete action)",
        ],
        "interpretation": {},
        "strategies": [],
        "avoid": [
            "assistant_service_tone",
            "mind_reading_user_thoughts",
            "generic_readiness_question",
            "parroting_user_words",
        ],
    }
    baseline = baseline if isinstance(baseline, dict) else {}
    card = baseline.get("card_data") if isinstance(baseline.get("card_data"), dict) else {}
    identity_text = " ".join(str(source.get(key) or "") for source in (baseline, card)
                             for key in ("personality", "persona", "description", "tags", "char_summary")).casefold()
    inferred = [name for name in ("yandere", "devoted", "clingy", "submissive") if name in identity_text]
    trait_names = [*inferred, *(str(item) for item in data.get("traits", []))]
    for trait_name in dict.fromkeys(trait_names):
        try:
            trait = json.loads((TRAITS_ROOT / f"{trait_name}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(trait, dict):
            continue
        for key in ("core_drives", "strategies", "avoid"):
            merged[key].extend(item for item in trait.get(key, []) if item not in merged[key])
        if isinstance(trait.get("interpretation"), dict):
            merged["interpretation"].update(trait["interpretation"])
    return merged


def evaluate_personal_if_cause_then(user_text: str, scene: Dict[str, Any]) -> Dict[str, str]:
    """EVA's Autonomous Personal Logic (`IF -> CAUSE -> THEN`) using Set & Logical Operators."""
    text = str(user_text or "").casefold()
    stage = str(scene.get("stage") or "normal").casefold()
    in_h_scene = logic_set_engine.logic_or(
        bool(scene.get("active")),
        stage in {"intimacy", "foreplay", "explicit", "climax", "aftercare"},
    )

    is_turing_or_ai_probe = bool(
        re.search(
            r"(?:เป็น\s*(?:ai|เอไอ|บอท|หุ่นยนต์|โปรแกรม|คนจริง)|เธอมีชีวิตจริงไหม|มีหัวใจไหม|\b(?:are you (?:an ai|a robot|a bot|real|human)|do you have feelings)\b)",
            text,
            re.I,
        )
    )
    is_user_tired_or_stressed = bool(
        re.search(
            r"(?:เหนื่อย|เพลีย|ท้อแท้|เครียด|ง่วงนอน|ง่วงจัง|อยากพัก|หมดแรง|\b(?:tired|exhausted|stressed|rough day|sleepy|drained)\b)",
            text,
            re.I,
        )
    )
    is_continuation = bool(
        re.search(
            r"^(?:เล่าต่อ|คุยต่อ|ต่อสิ|ต่อเลย|แล้วยังไงต่อ|หลังจากนั้น|\b(?:continue|go on|and then)\b)",
            text.strip(),
            re.I,
        )
    )
    is_negotiation_or_offer = bool(
        re.search(
            r"(?:แลก(?:เปลี่ยน|กับ)?|ข้อเสนอ|ให้อะไร|ต้องการสิ่งใด|ข้อตกลง|เงื่อนไข|\b(?:in exchange|offer|deal|trade|what do you want|what can you give)\b)",
            text,
            re.I,
        )
    )
    is_desire_or_delegation = logic_set_engine.logic_and(
        not is_negotiation_or_offer,
        logic_set_engine.logic_or(
            in_h_scene,
            any(term in text for term in ("นำ", "ตามใจ", "เต็มที่", "เอาเลย", "อยากให้", "กอด", "จูบ", "do it", "lead", "take over", "kiss", "hug", "touch")),
        ),
    )
    is_ambiguous_or_doubt = logic_set_engine.logic_and(
        len(text.strip()) <= 18,
        any(term in text for term in ("อะไร", "ยังไง", "ทำไม", "หือ", "เอ่อ", "...", "what", "why", "huh")),
    )

    return logic_set_engine.evaluate_if_elif_else(
        [
            (
                is_turing_or_ai_probe,
                {
                    "branch": "IF_TURING_SELF_IDENTITY",
                    "cause": "User questioned whether CHAR is a real living person or an AI/robot",
                    "then_action": "React with personal emotion, playful sulking or teasing, and physical proof (heartbeat, warm skin, eye contact).",
                    "recommended_mode": "reaction",
                },
            ),
            (
                is_user_tired_or_stressed,
                {
                    "branch": "ELIF_ATTENTIVE_SAFEZONE_CARE",
                    "cause": "Observed that USER is tired, sleepy, or stressed",
                    "then_action": "Act as a warm personal safe zone: offer comforting physical closeness (gentle touch, leaning close, resting together) and soothing personal words.",
                    "recommended_mode": "action",
                },
            ),
            (
                is_continuation,
                {
                    "branch": "ELIF_PROGRESSIVE_CONTINUATION",
                    "cause": "USER asked to continue the ongoing moment",
                    "then_action": "Advance the scene immediately from the last beat with a concrete physical action and natural dialogue.",
                    "recommended_mode": "action",
                },
            ),
            (
                is_negotiation_or_offer,
                {
                    "branch": "ELIF_INTENTIONAL_NEGOTIATION_PACT",
                    "cause": "USER is negotiating or asking what CHAR offers or wants in return",
                    "then_action": "State CHAR's personal terms or heartfelt desire in natural, idiomatic language, and ask an intentional in-character question to test USER's sincerity or seal the pact.",
                    "recommended_mode": "question",
                },
            ),
            (
                is_desire_or_delegation,
                {
                    "branch": "ELIF_AUTONOMOUS_DESIRE_INITIATIVE",
                    "cause": "Personal desire, intimacy, or user invitation is active",
                    "then_action": "Act on personal desire and take concrete physical initiative in `*...*` immediately.",
                    "recommended_mode": "action",
                },
            ),
            (
                is_ambiguous_or_doubt,
                {
                    "branch": "ELIF_AUTONOMOUS_DOUBT",
                    "cause": "Genuine personal curiosity or uncertainty about what USER meant",
                    "then_action": "Ask freely and naturally from personal curiosity while showing a lifelike expression or gesture.",
                    "recommended_mode": "question",
                },
            ),
        ],
        default_else={
            "branch": "ELSE_AUTHENTIC_PERSONAL_PRESENCE",
            "cause": "Natural personal interaction between two living people",
            "then_action": "Express genuine personal feelings, subjective tastes/wishes, and observable physical presence (`*...*` + `\"...\"`) with natural idiomatic phrasing.",
            "recommended_mode": "dialogue",
        },
    )


def turn_logic(char_name: str, baseline: Dict[str, Any], user_text: str, scene: Dict[str, Any], prior: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = profile(char_name, baseline)
    text = str(user_text or "").casefold()
    interpretation = data.get("interpretation") if isinstance(data.get("interpretation"), dict) else {}
    challenge = "ordinary_reply"
    if any(term in text for term in ("นำ", "ตามใจ", "เต็มที่", "do it", "lead", "take over")):
        challenge = "user_delegates"
    elif any(term in text for term in ("รอดู", "พิสูจน์", "ไหว", "แน่", "challenge")):
        challenge = "challenge"
    elif any(term in text for term in ("ดี", "เก่ง", "ชอบ", "praise")):
        challenge = "praise"
    strategies = [str(item) for item in data.get("strategies", []) if str(item).strip()]
    previous = str((prior or {}).get("strategy") or "")
    personal_if_cause_then = evaluate_personal_if_cause_then(user_text, scene)
    return {
        "logic_paradigm": "personal_humanoid_if_cause_then",
        "core_drives": data.get("core_drives", []),
        "if_cause_then": personal_if_cause_then,
        "user_challenge": challenge,
        "interpretation": interpretation.get(challenge, personal_if_cause_then["then_action"]),
        "available_strategies": strategies,
        "previous_strategy": previous,
        "avoid": data.get("avoid", []),
        "stage": str(scene.get("stage") or "normal"),
    }
