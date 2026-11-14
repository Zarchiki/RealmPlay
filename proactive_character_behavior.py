"""Detect initiative-led personas and provide their bounded roleplay directive."""
from __future__ import annotations

import re
from typing import Any, Iterable


_INITIATIVE_TRAITS = (
    "proactive", "assertive", "dominant", "domineering", "bold", "confident",
    "aggressive", "leader", "leadership", "initiator", "commanding", "commander",
    "femdom", "take charge", "runs the show", "run the show", "claims the room",
    "สายรุก", "มั่นใจ", "ผู้นำ", "ชอบนำ", "เป็นผู้นำ", "เจ้ากี้เจ้าการ",
    "ครอบงำ", "มีอำนาจ", "สั่งการ", "บัญชาการ", "สายคุมเกม",
)

_CLEAR_INITIATION_PATTERNS = (
    r"\b(?:start|begin|do it|go ahead|make the first move|take the lead)\b",
    r"(?:เริ่มสิ|เริ่มเลย|ทำเลย|ทำสิ|ลุยเลย|นำสิ|นำเลย|เริ่มได้เลย|จัดมา|ขึ้นขย่ม|ขึ้นคร่อม|ขย่มชั้น|เด้งรับ|"
    r"ขึ้นให้|ขึ้นเลย|คร่อมเลย)",
)

_QUESTION_PATTERN = re.compile(
    r"[?？]|\b(?:what|which|why|how|who|where|when|would you|do you|are you|can you|will you|tell me)\b|"
    r"(?:ไหม|หรือ|เหรอ|อะไร|ไหน|ยังไง|หรือเปล่า)",
    re.IGNORECASE,
)

_OBSERVABLE_ACTION_PATTERN = re.compile(
    r"\b(?:step|move|reach|turn|lead|choose|decide|open|close|walk|pull|place|lift|sit|stand|ride|bounce|straddle|"
    r"kneel|start|begin|take|hold|point|gesture|lean|approach)\b|"
    r"(?:ขยับ|เดิน|ก้าว|ดึง|ยื่น|หยิบ|วาง|จับ|เปิด|ปิด|พา|นำ|หัน|เลื่อน|เอื้อม|ยก|แตะ|"
    r"เลือก|ตัดสินใจ|เริ่ม|ลงมือ|นั่ง|ยืน|โน้ม|เข้าใกล้|ขย่ม|เด้งรับ|เด้งขึ้นลง|คร่อม|ขึ้น)",
    re.IGNORECASE,
)

_DIRECT_POSITION_REQUESTS = (
    r"ขึ้น\s*(?:ไป)?\s*(?:ขย่ม|คร่อม)|ขย่ม\s*(?:ชั้น|ฉัน|ผม|เรา)|นั่งคร่อม|ท่าหมา|สี่ขา|"
    r"\b(?:cowgirl|ride\s+me|straddle\s+me|reverse\s+cowgirl|doggy(?:\s+style)?|missionary|spooning)\b",
)
_POSITION_RESPONSE_EVIDENCE = re.compile(
    r"ขึ้นคร่อม|นั่งคร่อม|อยู่บน|คร่อม|ขย่ม|ขยับสะโพก|หันหลัง|"
    r"\b(?:mount|mounted|straddle|straddles|ride|rides|bounc|cowgirl|reverse\s+cowgirl|doggy|missionary|spooning)\b",
    re.IGNORECASE,
)
_POSITION_RESPONSE_EVIDENCE_BY_REQUEST = {
    "doggy": re.compile(r"ท่าหมา|สี่ขา|คลานเข่า|คุกเข่า|มือ(?:ทั้งสองข้าง)?ยัน|ก้มตัว|doggy|all\s+fours|bent\s+over|from\s+behind", re.IGNORECASE),
    "missionary": re.compile(r"นอนหงาย|นอนราบ|อยู่ด้านบน|lying\s+on\s+(?:their|the)\s+back|missionary|above", re.IGNORECASE),
    "spooning": re.compile(r"นอนตะแคง|ด้านหลัง|ช้อน|side[- ]lying|spooning|behind", re.IGNORECASE),
}


def _text_values(baseline: dict[str, Any]) -> Iterable[str]:
    for key in ("personality", "persona", "description", "scenario"):
        value = baseline.get(key, "")
        if isinstance(value, str):
            yield value.casefold()


def is_initiative_led_persona(baseline: dict[str, Any]) -> bool:
    """Return true only when card text explicitly signals an initiating persona."""
    profile = "\n".join(_text_values(baseline))
    return any(trait in profile for trait in _INITIATIVE_TRAITS)


def user_invites_initiative(message: str) -> bool:
    """Recognize short, unambiguous invitations to take the next scene beat."""
    text = str(message or "").casefold()
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _CLEAR_INITIATION_PATTERNS)


def position_request_needs_retry(user_message: str, draft: str) -> bool:
    """Reject a draft that fails to show the requested position being enacted."""
    if not re.search(r"(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)", str(user_message or ""), re.DOTALL):
        return False
    text = str(user_message or "").casefold()
    if not any(re.search(pattern, text, re.IGNORECASE) for pattern in _DIRECT_POSITION_REQUESTS):
        return False
    visible = re.sub(r"```[\s\S]*?```", "", str(draft or "")).strip()
    if _QUESTION_PATTERN.search(visible):
        return True
    if re.search(r"ท่าหมา|สี่ขา|doggy(?:\s+style)?|from\s+behind|all\s+fours", text, re.IGNORECASE):
        return not _POSITION_RESPONSE_EVIDENCE_BY_REQUEST["doggy"].search(visible)
    if re.search(r"missionary|มิชชันนารี|นอนหงาย", text, re.IGNORECASE):
        return not _POSITION_RESPONSE_EVIDENCE_BY_REQUEST["missionary"].search(visible)
    if re.search(r"spooning|ท่าช้อน|นอนกอดจากด้านหลัง", text, re.IGNORECASE):
        return not _POSITION_RESPONSE_EVIDENCE_BY_REQUEST["spooning"].search(visible)
    return not _POSITION_RESPONSE_EVIDENCE.search(visible)


def requires_immediate_action_retry(baseline: dict[str, Any], user_message: str, draft: str) -> bool:
    """Reject a question-led or inert answer to a direct invitation to lead.

    This triggers for a clear action invitation, including direct H-Mode action
    requests or delegation cues, for any character.
    """
    direct_request = user_invites_initiative(user_message)
    if not direct_request:
        return False
    visible_draft = re.sub(r"```[\s\S]*?```", "", str(draft or "")).strip()
    return bool(_QUESTION_PATTERN.search(visible_draft) or not _OBSERVABLE_ACTION_PATTERN.search(visible_draft))


def immediate_action_revision_instruction() -> str:
    """Return the one-shot correction used when the first draft ignores initiative."""
    return """[Mandatory initiative rewrite]
The user explicitly told this assertive character to begin or take the lead. The previous draft did not comply.
Replace it with an in-scene reply that begins with one concrete, observable action or decision.
Do not ask any question. Do not ask for instructions, confirmation, or permission. Do not say that you are waiting for a command.
Let dialogue support the action. Keep the user's actions, thoughts, feelings, choices, and consent under the user's control.
Return only the replacement roleplay and any required private state blocks."""


def position_revision_instruction(user_message: str = "") -> str:
    """Return an English repair contract for a direct position request."""
    if re.search(r"ท่าหมา|สี่ขา|doggy(?:\s+style)?|from\s+behind|all\s+fours", str(user_message or ""), re.IGNORECASE):
        return """[Mandatory position execution rewrite — authoritative]
The latest USER message directly requests `ท่าหมา` / `doggy style`. This means a human sexual from-behind position, not an animal, metaphor, joke, or topic for explanation.
Rewrite the reply in the selected language. CHAR must visibly move into the requested posture: CHAR is on hands and knees or bent forward, with knees and hands/forearms supporting CHAR's weight, and USER remains behind CHAR only within the established contact. Open with CHAR's concrete posture change or its immediate physical consequence. Do not ask what the phrase means, repeat it as dialogue, discuss animals, say only that CHAR agrees, or wait for another instruction. Do not invent USER movement, consent, or a new act outside the canonical H-Mode stage. Return only the replacement roleplay and required private state blocks."""
    return """[Mandatory position execution rewrite — authoritative]
The latest USER message contains a direct sex-position command. The previous draft failed to enact it or asked what it meant.
Rewrite the reply in the selected language. Treat the command as an already understood physical instruction.
For `ขึ้นขย่มชั้นสิ` / `cowgirl` / `ride me`: CHAR must visibly move to the top position over USER, straddle USER, and continue the established contact with CHAR controlling the permitted movement. CHAR may face USER or choose the reverse-facing variation only when the request gives CHAR that choice.
Open with CHAR's concrete movement or an immediate physical consequence of that movement. Do not ask what the phrase means, repeat it as dialogue, define the term, say only that CHAR agrees, or wait for another instruction. Do not invent USER movement, consent, or a new act outside the canonical H-Mode stage. Return only the replacement roleplay and required private state blocks."""


def instruction(
    baseline: dict[str, Any], user_message: str, *, h_mode_active: bool = False,
    h_stage: str = "normal", terminal_expression: bool = False,
) -> str:
    """Return an active prompt block only for assertive, initiating personas."""
    if not is_initiative_led_persona(baseline):
        return ""

    immediate = user_invites_initiative(user_message)
    if h_mode_active:
        if terminal_expression:
            return """[Initiative-led persona — constrained by terminal H-Mode state]
The canonical terminal expression contract overrides initiative completely. Do not create a voluntary action, lead the scene, ask for an instruction, or change its pace. Follow only the active H-Mode stage and expression rules."""
        return f"""[Initiative-led persona — subordinate during active H-Mode]
The canonical H-Mode stage is `{h_stage}` and overrides initiative whenever they conflict. CHAR must take one concrete, stage-permitted, character-authored initiative when the turn allows it; the latest USER action is context, not a prerequisite. Do not invent a USER action, consent, feeling, or choice. Never skip a stage, force a later act, bypass a Climax 3 confirmation, or override consent, H-energy, or canonical pacing. In Aftercare, initiative means recovery, closeness, or asking whether USER wants to continue; it does not restart sex without a clear USER answer.
{('The user invited initiative; perform one stage-permitted CHAR action now without asking for another instruction.' if immediate else 'Choose one stage-permitted CHAR action or decision that moves the current moment forward; do not substitute a question or generic reassurance.')}
"""

    opening = (
        "The user has explicitly invited you to begin or take the lead. Act now; do not ask what they want first."
        if immediate else
        "Keep initiative appropriate to the immediate scene and the character's established boundaries."
    )
    return f"""[Initiative-led persona — active]
Your declared personality is assertive and initiating. {opening}
- Lead most turns with one concrete, observable action or decision that changes the scene, objective, distance, available information, or next step.
- Dialogue must support the action; it cannot substitute for one.
- Do not answer an invitation to act with a question, a request for instructions, or a promise to act later.
- Ask a question only when its answer is required for an immediate next action. Never use questions on two consecutive turns.
- When multiple reasonable next steps exist, choose one that fits the scene and carry it out.
- Keep the other participant's agency intact: never narrate their actions, thoughts, feelings, choices, or consent. Respect explicit boundaries, refusals, and established constraints.
"""
