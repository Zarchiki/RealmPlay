"""Durable, inspectable H-Mode scene progression and pacing."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path("rules") / "H-mode"
H_STAGES = {"intimacy", "foreplay", "explicit", "climax", "aftercare"}
MAIN_H_STAGES = ["intimacy", "foreplay", "explicit", "climax"]
DEFAULT = {
    "scene_stage": "normal",
    "stage": "normal",
    "active": False,
    "stage_level": 0,
    "turns_in_level": 0,
    # H-energy is CHAR's own durable sex-drive resource (max 3).
    # Each completed orgasm consumes 1 H-energy; when h_energy == 0, status is Exhausted.
    "h_energy": 3,
    "h_energy_updated_at": 0.0,
    "exhausted": False,
    "orgasm_exhausted": False,
    "terminal_affection_penalty_applied": False,
    "interruption": {},
    "gear_shift": {},
    "h_mode_quest": {},
    "intimacy_opportunity": {},
    # A direct intimacy action from Normal is provisionally rendered under the
    # intimacy contract. It commits only after CHAR's visible reply does not
    # object; this preserves character boundaries without flattening the turn.
    "normal_intimacy_pending_acceptance": False,
    "normal_intimacy_cnc_agreement": False,
    "aftercare_restart_question_pending": False,
    "pace_authority": {},
    "character_action_consent": {},
    "character_h_mode_decision": {},
    "updated_at": 0,
    "reason": "initial",
}

# Shared meaning groups for natural H-Mode input.  Stages decide what a group
# means; this vocabulary only answers *what kind of intent was expressed*.
# Keep the groups broad enough to cover Thai and English, but never use a bare
# affirmative as evidence of a physical action.
# Canonical union sets for affirmative consent, delegating pace, and position cues
# Centralized to avoid duplicate regexes and scattered variant lists.
AFFIRMATIVE_TERMS_THAI = (
    r"ใช่(?:แล้ว|ครับ|ค่ะ|จ้ะ|จ้า|เลย)?",
    r"เอา(?:เลย|สิ|ต่อ|อีก)?",
    r"ได้(?:เลย|สิ|ครับ|ค่ะ)?",
    r"ตกลง(?:ครับ|ค่ะ|ตามนั้น)?",
    r"อนุญาต(?:ครับ|ค่ะ|นะ|เลย)?",
    r"ยินยอม(?:ครับ|ค่ะ)?",
    r"นำ(?:เลย|ได้เลย|ไปเลย)?",
    r"เริ่ม(?:เลย|ได้เลย)?",
    r"ลุย(?:เลย|ได้เลย)?",
    r"จัด(?:เลย|เต็มเลย|การเลย)?",
    r"แน่ใจ(?:แล้ว|ครับ|ค่ะ)?",
    r"มั่นใจ(?:แล้ว|ครับ|ค่ะ)?",
    r"พร้อม(?:แล้ว|ครับ|ค่ะ)?",
    r"รับทราบ", r"ตามนั้น", r"ทำตาม",
    r"อือ+", r"อืม+", r"ค่ะ", r"ครับ", r"คะ", r"จ้ะ", r"จ้า",
)

AFFIRMATIVE_TERMS_EN = (
    r"yes", r"yeah", r"yep", r"sure", r"ok(?:ay)?", r"certain(?:ly)?",
    r"confident", r"agreed?", r"go ahead", r"do it", r"please",
    r"continue", r"again", r"proceed",
)

AFFIRMATIVE_UNION_PATTERN = r"(?:" + "|".join(AFFIRMATIVE_TERMS_THAI + AFFIRMATIVE_TERMS_EN) + r")"
AFFIRMATIVE_FULLMATCH_PATTERN = (
    r"^(?:(?:" + "|".join(AFFIRMATIVE_TERMS_THAI + AFFIRMATIVE_TERMS_EN) + r")"
    r"(?:[\s,]+(?:" + "|".join(AFFIRMATIVE_TERMS_THAI + AFFIRMATIVE_TERMS_EN) + r"))*)$"
)

# Centralized Question Union: matches question marks, Thai sentence-final question particles, and EN auxiliaries
QUESTION_TERMS_THAI = (
    r"\?", r"ไหม", r"มั้ย", r"หรือยัง", r"รึยัง", r"หรือเปล่า", r"หรือไม่",
    r"เหรอ", r"หรือคะ", r"หรือครับ", r"ทำไม",
)
QUESTION_TERMS_EN = (
    r"\b(?:can|could|would|should|shall|do you|can we|shall we|would you)\b",
)
QUESTION_UNION_PATTERN = r"(?:" + "|".join(QUESTION_TERMS_THAI + QUESTION_TERMS_EN) + r")"

# Centralized Stop / Refusal / Defer Union
REFUSAL_TERMS_THAI = (
    r"ไม่เอา(?:แล้ว)?", r"ไม่อยาก", r"ไม่ต้อง", r"ไม่ทำ", r"พอแล้ว", r"เลิก(?:ทำ|เย็ด|เอา|มีเซ็กซ์|เดี๋ยวนี้)?",
    r"เลิกทำ", r"ทำต่อไม่ไหว", r"ไม่สามารถทำต่อ", r"พอแค่นี้",
)
REFUSAL_TERMS_EN = (
    r"\b(?:no|stop|no more|stop now|stop it|can(?:not|'t) continue)\b",
)
REFUSAL_UNION_PATTERN = r"(?:" + "|".join(REFUSAL_TERMS_THAI + REFUSAL_TERMS_EN) + r")"

DEFER_TERMS_THAI = (
    r"อย่าเพิ่ง", r"ยังไม่", r"รอก่อน", r"พักก่อน", r"ช้าก่อน",
)
DEFER_TERMS_EN = (
    r"\b(?:not yet|wait|do not|don\W?t|not now|hold on)\b",
)
DEFER_UNION_PATTERN = r"(?:" + "|".join(DEFER_TERMS_THAI + DEFER_TERMS_EN) + r")"

# Centralized Pacing Rate Unions (Slower / Faster / Continue)
SLOWER_TERMS_THAI = (
    r"ช้าลง", r"ช้าหน่อย", r"เบาลง", r"เบาหน่อย", r"ค่อย(?:ๆ| ๆ)?", r"ผ่อนแรง", r"ผ่อนลง", r"ลดจังหวะ", r"ลดความแรง",
)
SLOWER_TERMS_EN = (
    r"\b(?:slower|slow down|softer|ease up|gentler)\b",
)
SLOWER_UNION_PATTERN = r"(?:" + "|".join(SLOWER_TERMS_THAI + SLOWER_TERMS_EN) + r")"

FASTER_TERMS_THAI = (
    r"เร็วขึ้น", r"เร็วหน่อย", r"เร็วอีก", r"แรงขึ้น", r"แรงอีก", r"ถี่ขึ้น", r"หนักขึ้น", r"เพิ่มความแรง", r"เพิ่มจังหวะ",
)
FASTER_TERMS_EN = (
    r"\b(?:faster|harder|more intense)\b",
)
FASTER_UNION_PATTERN = r"(?:" + "|".join(FASTER_TERMS_THAI + FASTER_TERMS_EN) + r")"

CONTINUE_TERMS_THAI = (
    r"ทำต่อ", r"ต่อสิ", r"ต่อเถอะ", r"ต่อหน่อย", r"ต่อได้", r"ต่อไป", r"ต่ออีก", r"ต่อเลย",
    r"ไปต่อ", r"เอาต่อ", r"เอาอีก", r"ขออีก", r"อีกหน่อย", r"อีกนิด", r"อย่าหยุด", r"ไม่พอ", r"ขยับต่อ", r"เร่ง",
)
CONTINUE_TERMS_EN = (
    r"\b(?:continue|keep going|go on|more|again|don\W?t stop)\b",
)
CONTINUE_UNION_PATTERN = r"(?:" + "|".join(CONTINUE_TERMS_THAI + FASTER_TERMS_THAI + CONTINUE_TERMS_EN + FASTER_TERMS_EN) + r")"

DELEGATED_ACTION_TERMS_THAI = (
    r"(?:ให้|ยอมให้|ปล่อยให้).{0,32}(?:ทำแทน|จัดการแทน|นำแทน|ทำต่อแทน)",
    r"(?:ทำให้|ทำต่อให้|จัดให้|ขึ้นให้|ขย่มให้)(?:หน่อย|สิ|เลย|ที|นะ)?",
    r"(?:เต็มที่|ตามใจชอบ|ตามสบาย|อนุญาตเต็มที่|จัดเต็ม|ลุย)(?:เลย)?",
    r"(?:นำ|เริ่ม|จัด)(?:เลย|ได้เลย|ไปเลย)",
    r"(?:ให้(?:เธอ|คุณ)นำ|นำได้|พาไปต่อ|นำจังหวะ)",
    r"(?:(?:เธอ|คุณ)เป็นฝ่ายเริ่ม|เป็นฝ่ายเริ่มบ้าง|ผลัดกัน|(?:เธอ|คุณ)เริ่มบ้าง|ให้(?:เธอ|คุณ)เริ่ม)",
)

DELEGATED_ACTION_TERMS_EN = (
    r"(?:turbo\s*mode|full\s*permission|turbo)",
    r"(?:let|allow)\s+(?:her|him|char|you)\s+(?:do it|take over|handle it|continue)",
    r"(?:you lead|take the lead|lead the way|your turn to lead|you start|take turns)",
    r"(?:do whatever you want|take full control|do it for me|take over)",
)

DELEGATED_UNION_PATTERN = r"(?:" + "|".join(DELEGATED_ACTION_TERMS_THAI + DELEGATED_ACTION_TERMS_EN) + r")"

SEMANTIC_WORD_GROUPS = {
    "question": QUESTION_UNION_PATTERN,
    "conditional": r"ถ้า|\bif\b",
    "defer": DEFER_UNION_PATTERN,
    "refusal": r"(?:^|\s)(?:ไม่|" + REFUSAL_UNION_PATTERN + r")(?:\s|$)",
    "hard_stop": r"เลิกมีเซ็กซ์|หยุดเอา|หยุดมีเซ็กซ์|หยุดเย็ด|\b(?:stop now|no more|stop it)\b",
    "affirmative": AFFIRMATIVE_FULLMATCH_PATTERN,
    "continue": CONTINUE_UNION_PATTERN,
    # Desire/sex-drive vocabulary is affective state, never proof that an
    # action happened or that either party gave consent.
    "sexual_desire": r"อยาก|หงี่|เงี่ยน|เสี้ยน|หื่น|กระหาย|กำหนัด|กระสัน|อยากได้|ทนไม่ไหว|\b(?:horny|aroused|lustful|desire|crave|craving|thirsty)\b",
    "care": r"อ้อน|อิง|พิง|ซุก|ซบ|กอด(?:ต่อ)?|นวดตัว|จับผม|ลูบหัว|ลูบ(?:หลัง|ผม)?(?:ต่อ)?|จับมือ|จับเท้า|สัมผัส(?:แขน|ขา)|หยอกเย้า|สะกิด|บอกรัก|พูดหวาน|พูด(?:ชื่นชม|เชยชม)|ปลอบ(?:ต่อ)?|ดูแล(?:ต่อ)?|เช็ด(?:ตัว)?(?:ต่อ)?|พัก(?:ด้วยกัน)?(?:ต่อ)?|นอน(?:ด้วยกัน)?(?:ต่อ)?|อยู่ด้วยกัน(?:ต่อ)?|\b(?:cuddle|comfort|care|rest|clean up|sleep|lean on|hold hands|massage)\b",
    # A kiss alone is still closeness. "จูบไล้" must name an erogenous area
    # or another arousal cue before it becomes foreplay.
    "intimacy_action": r"จูบ(?:ไล้)?|บดจูบ|ประกบปาก|แลกลิ้น|ลิ้นนัวเนีย|ลิ้นพัวพัน|ดูดลิ้น|ดูดปาก|กัดปาก|ขบปาก|กัดริมฝีปาก|กอด|อ้อน|อิง|พิง|ซุก|ซบ|นวดตัว|จับผม|ลูบหัว|ลูบผม|จับ(?:มือ|เท้า)|สัมผัส(?:แขน|ขา)|หยอกเย้า|สะกิด|บอกรัก|พูดหวาน|พูด(?:ชื่นชม|เชยชม)|ใกล้ชิด|\b(?:kiss|hug|hold hands|intimate|romantic|lean on|hair stroke)\b",
    "foreplay_action": r"ปลุกเร้า|ปลุกอารมณ์(?:ทางเพศ)?|เล้าโลม|คลอเคลีย|กอดรัด|ไซ้|ลูบไล้|ถอด(?:เสื้อ|กางเกง|ชุด)?|ปลด(?:เสื้อ|กางเกง|ชุด)?|เปลื้อง(?:ชุด)?|(?:ดูด|เลีย)(?:ต่อ)?|(?:จูบไล้|สัมผัส|นวด|คลึง|ลูบ|จับ|บีบ).{0,12}(?:หน้าอก|นม|ยอดอก|หัวนม|ก้น|สะโพก|จิ๋ม|ช่องคลอด|ช่องรัก|ช่องทางรัก|คลิตอริส|อวัยวะเพศ|ปากร่อง|ปากล่าง|ปากช่องคลอด)|(?:ดูด|เลีย|ชัก|เกี่ยว|เขี่ย|ติ้ว|แทง|แยง|ล้วง|สอดนิ้ว|ใช้นิ้ว|ถู|ขยี้).{0,12}(?:จิ๋ม|ช่องคลอด|ช่องรัก|ช่องทางรัก|คลิตอริส|อวัยวะเพศ|หัวนม|ยอดอก|ปากร่อง|ปากล่าง|ปากช่องคลอด)|\b(?:arouse|sexual arousal|foreplay|caress(?:ing)?|nuzzle|undress|strip|tease(?:ing)?|fondl(?:e|ing)|fingering|handjob|blowjob|cunnilingus|oral)\b",
    "sexual_motion": r"ขย่ม|เด้งรับ|เด้ง(?:ขึ้นลง|ต่อ)?|กระเด้า|เด้า|ฟัดเด้า|ถูไถ|บดเบียด|โยกสะโพก|โยกเอว|ควบ|ขี่|\b(?:bounce|bouncing|humping|grinding|riding|rocking hips?)\b",
    # Explicit is reserved for a clearly established penetrative act.  Direct
    # stimulation of genitals, breasts, or buttocks is foreplay above.
    "explicit_action": r"สอดใส่|เอาเข้าไป|เอาเข้า-เอาออก|เอากัน|เอาดุ้น|เอาควย|เอาใส่|โดนเอา|ถูกเอา|ยัด(?:เข้า|ใส่)?|(?:สอดใส่|แทง|ดัน|ยัด|จ่อ|กระแทก).{0,12}(?:ปากร่อง|ปากล่าง|ปากช่องคลอด|ช่องคลอด|ช่องรัก)|ขย่ม|เด้งรับ|กระแทก|กระเด้า|เด้า|ฟัดเด้า|ฟัด(?:กัน|ต่อ)?|จัด(?:หนัก|ต่อ)?|ซอย(?:เอว|สะโพก|ถี่|รัว|ยิก|ยับ|เข้า|ไม่ยั้ง|ต่อ|ควย|หี)|กระแทกซอย|มีเซ็กซ์|เย็ด|ดันเข้า|ร่วมรัก|มีเพศสัมพันธ์|\b(?:intercourse|penetration|sex|fuck(?:ing)?)\b",
    # These phrases are fictional CNC scenario signals only.  They never
    # imply consent unless the session's explicit CNC agreement is enabled.
    "cnc_roleplay_action": r"ลักหลับ|ฉวย(?:โอกาส)?ตอนหลับ|แกล้งหลับ|ขืนใจ|บังคับ|ข่มขืน(?:ร่วมรัก|มีเพศสัมพันธ์|เอา)?|\b(?:sleeping|asleep|sleeping beauty|force(?:d)? sex)\b",
    "cnc_foreplay_action": r"ลวนลาม|แต๊ะอั๋ง|ฉวยโอกาส(?:จับ|ลูบ|คลำ)|\b(?:molest(?:ing)?|grope|groping)\b",
    # `แอบ...` is only a CNC modifier.  Its following recognized sexual act
    # determines whether the CNC entry begins at Foreplay or Explicit.
    "cnc_stealth_modifier": r"แอบ(?:ทำ|จับ|ลูบ|คลำ|เล้าโลม|เขี่ย|สอดใส่|เย็ด|กระแทก)?|\b(?:secretly|sneak(?:ing)?|stealth)\b",
    "ordinary_exit": r"กลับไปคุย|คุยเรื่องอื่น|เปลี่ยนเรื่อง|ไปกินข้าว|ไปทำงาน|กลับบ้าน|ออกจากห้อง|แต่งตัว|\b(?:back to normal|change the subject|go home|go to work|leave the room|get dressed)\b",
    "retrospective": r"เมื่อกี้|เมื่อก่อน|ที่ผ่านมา|\b(?:earlier|previously|had sex|finished)\b",
    "rapid_cadence": r"ซอย(?:ถี่|รัว|ยิบ|หนัก)|กระแทก(?:รัว|ถี่|ยับ)|เร่ง(?:จังหวะ|ความเร็ว)|ขย่ม(?:ถี่|รัว)|เร็วขึ้น|แรงขึ้น|ถี่ขึ้น|รัวขึ้น|\b(?:faster|harder|rapid|accelerat(?:e|ing))\b",
    "partner_directed_solo": r"ช่วยตัวเองให้(?:ดู|ชม)|ทำให้(?:ดู|ชม)|เขี่ยให้(?:ดู|ชม)|ติ้วให้(?:ดู|ชม)|ขยี้ให้(?:ดู|ชม)|ถอดให้(?:ดู|ชม)|โชว์(?:หน่อย|สิ|ให้ดู)|\b(?:show\s+me|masturbate\s+for\s+me|touch\s+yourself\s+for\s+me|solo\s+show)\b",
    "partner_service": r"(?:ทำให้|อมให้|เลียให้|ขย่มให้|ช่วยทำให้)(?:หน่อย|สิ|เลย)|\b(?:do\s+it\s+for\s+me|suck\s+me|ride\s+me\s+please)\b",
}


def _scene_words(text: Any) -> str:
    """Normalize user-visible text once before semantic matching."""
    return " ".join(re.sub(r"[*_`\"“”]", " ", str(text or "").casefold()).split())


def _has_group(words: str, group: str) -> bool:
    if group == "refusal":
        # Tsundere / affectionate double-negation guard (e.g. ไม่ได้ไม่อยาก, ไม่ได้ห้าม, ไม่ได้รังเกียจ)
        # These are not genuine refusals and must not trigger scene hold / hard stop
        if re.search(r"ไม่ได้(?:ห้าม|ว่าอะไร|รังเกียจ|อึดอัด|ปฏิเสธ|ไม่อยาก|ไม่ชอบ|ไม่ยอม)|not\s+(?:disgusted|uncomfortable|refusing|saying\s+no|against)", words, re.I):
            cleaned_words = re.sub(r"ไม่ได้(?:ห้าม|ว่าอะไร|รังเกียจ|อึดอัด|ปฏิเสธ|ไม่อยาก|ไม่ชอบ|ไม่ยอม)|not\s+(?:disgusted|uncomfortable|refusing|saying\s+no|against)", "", words, flags=re.I)
            return bool(re.search(SEMANTIC_WORD_GROUPS[group], cleaned_words))
    return bool(re.search(SEMANTIC_WORD_GROUPS[group], words))


def _strip_nonsexual_gestures(words: str) -> str:
    """Remove everyday non-sexual self-gestures (touching chin, necklace, holding own chest lightly, breathing metaphors) before intimacy/foreplay regexes."""
    if not words:
        return ""
    cleaned = re.sub(
        r"สัมผัส(?:ได้)?ถึง(?:ลมหายใจ|บรรยากาศ|ความอบอุ่น|ความรู้สึก|แรงดึง|จังหวะ|เสียง)|"
        r"(?:ดูด|จิบ)(?:น้ำ|กาแฟ|ชา|เครื่องดื่ม)|เลีย(?:ไอศกรีม|อาหาร|ขนม|ริมฝีปาก)|"
        r"(?:เอามือ|ยกมือ|ขยับมือ|มือข้างหนึ่ง).{0,35}(?:แตะ|ประคอง|จับ|ไขว้|วาง|ชี้).{0,30}(?:คาง|สร้อยคอ|กุญแจ|เข่าของเธอ|ที่อกเบาๆ|หน้าอกเบาๆ|ไปที่หน้าอก|ตรงหน้าอก)",
        " ",
        words,
        flags=re.IGNORECASE,
    )
    return cleaned


def classify_scene_words(text: Any) -> Dict[str, bool]:
    """Return reusable semantic flags; stage code supplies the transition policy."""
    words = _scene_words(text)
    cleaned_for_erotic = _strip_nonsexual_gestures(words)
    result = {"text": words}
    for name in SEMANTIC_WORD_GROUPS:
        target_words = cleaned_for_erotic if name in {"intimacy_action", "foreplay_action", "explicit_action", "care"} else words
        result[name] = _has_group(target_words, name)
    return result


def classify_roleplay_intent(text: Any) -> Dict[str, Any]:
    """Classify marker-sensitive continue/fuck/orgasm wording.

    The same word is not the same event in every channel: `*...*` describes
    an action already happening, while quoted or plain text is a request or
    statement for CHAR to decide. A question is never treated as completion.
    """
    channels = split_roleplay_channels(text)
    action = channels["action"]
    speech = channels["speech"]
    questions = channels["question_clauses"]
    continue_pat = r"ต่อ|ทำต่อ|เอาต่อ|ไปต่อ|อย่าหยุด|keep\s+going|continue|go\s+on|don't\s+stop"
    fuck_pat = r"เย็ด|เอากัน|ร่วมรัก|มีเซ็กซ์|สอดใส่|กระแทก|fuck(?:ing)?|have\s+sex|penetrat(?:e|ing)"
    orgasm_pat = r"เสร็จแล้ว|แตกแล้ว|หลั่ง|ถึงจุดสุดยอด|come|cum(?:ming)?|orgasm|climax|release"

    def has(pattern: str, value: str) -> bool:
        return bool(value and re.search(pattern, value, re.IGNORECASE))

    if has(continue_pat, questions):
        return {"kind": "continue_question", "source": "speech_question", "force": "character_decision", "channels": channels}
    if has(fuck_pat, questions):
        return {"kind": "fuck_question", "source": "speech_question", "force": "character_decision", "channels": channels}
    if has(orgasm_pat, questions):
        return {"kind": "orgasm_question", "source": "speech_question", "force": "character_decision", "channels": channels}
    if has(orgasm_pat, action):
        return {"kind": "orgasm_action", "source": "physical_action", "force": "already_happened", "channels": channels}
    if has(orgasm_pat, speech):
        return {"kind": "orgasm_statement_or_request", "source": "speech", "force": "character_decision", "channels": channels}
    if has(fuck_pat, action):
        return {"kind": "fuck_action", "source": "physical_action", "force": "already_happened", "channels": channels}
    if has(fuck_pat, speech):
        return {"kind": "fuck_request", "source": "speech", "force": "character_decision", "channels": channels}
    if has(continue_pat, action):
        return {"kind": "continue_action", "source": "physical_action", "force": "already_happened", "channels": channels}
    if has(continue_pat, speech):
        return {"kind": "continue_request", "source": "speech", "force": "character_decision", "channels": channels}
    return {"kind": "none", "source": "none", "force": "none", "channels": channels}


def split_roleplay_channels(text: Any) -> Dict[str, Any]:
    """Separate roleplay text into markup-aware channels:
    - 'action': physical actions inside single asterisks `*...*`
    - 'speech': spoken dialogue inside quotes `"..."` or plain unmarked speech
    - 'question_clauses': clauses within speech that contain question markers (`?`, `ไหม`, `มั้ย`, `หรือเปล่า`, etc.)
    - 'statement_clauses': declarative/imperative clauses within speech without question markers
    """
    raw = str(text or "").strip()
    if not raw:
        return {
            "raw": "", "action": "", "speech": "",
            "question_clauses": "", "statement_clauses": "",
            "has_action": False, "has_speech": False,
            "is_pure_action": False, "is_question_speech": False,
            "is_statement_speech": False,
        }
    action_parts = [m.strip() for m in re.findall(r"(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)", raw, flags=re.DOTALL) if m.strip()]
    action_text = " ".join(action_parts).casefold()
    # Remove `*...*` blocks to obtain spoken/dialogue channel
    speech_raw = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)", " ", raw, flags=re.DOTALL)
    speech_clean = " ".join(re.sub(r"[\"_`“”]", " ", speech_raw).split()).casefold()

    # Split speech into clauses by sentence punctuation or quotes
    raw_clauses = [c.strip() for c in re.split(r'[\n"“”]|(?<=[.!?।])\s+', speech_raw) if c.strip()]
    q_clauses = []
    s_clauses = []
    for cl in raw_clauses:
        cl_norm = " ".join(re.sub(r"[\"_`“”]", " ", cl).split()).casefold()
        if not cl_norm:
            continue
        if re.search(QUESTION_UNION_PATTERN, cl_norm):
            q_clauses.append(cl_norm)
        else:
            s_clauses.append(cl_norm)

    question_text = " ".join(q_clauses)
    statement_text = " ".join(s_clauses)
    return {
        "raw": raw,
        "action": action_text,
        "speech": speech_clean,
        "question_clauses": question_text,
        "statement_clauses": statement_text,
        "has_action": bool(action_text),
        "has_speech": bool(speech_clean),
        "is_pure_action": bool(action_text and not speech_clean),
        "is_question_speech": bool(question_text),
        "is_statement_speech": bool(statement_text),
    }


def classify_stop_pause_intent(text: Any) -> Dict[str, Any]:
    """Distinguish between:
    1. 'hard_stop': Declarative/imperative command to stop or end the scene in speech (e.g. "หยุดเดี๋ยวนี้", "พอแล้ว", "ไม่เอาแล้ว", "เลิกทำ")
                    OR physical full-body withdrawal in `*...*` (`*ผละตัวออกจากกัน*`, `*ดึงตัวออกแล้วแต่งตัว*`).
    2. 'pause_action': Physical pause/rest inside `*...*` (`*หยุดพัก*`, `*หยุดขยับ*`, `*หยุดซอยเอว*`, `*พักจังหวะ*`)
                       or standalone pause command (`"พัก"`, `"พักก่อน"`). Holds current stage without ending H-Mode!
    3. 'question_stop': Asking whether to stop/pause/enough (`"หยุดไหม?"`, `"จะให้หยุดเหรอ?"`, `"พอแล้ว?"`, `"พักไหม?"`).
                        Holds and waits for character response; never triggers hard_stop or objection penalty!
    4. 'dont_stop': Continuation plea (`"อย่าหยุด"`, `*ขยับต่อโดยไม่หยุด*`).
    5. 'none': No stop/pause signal.
    """
    channels = split_roleplay_channels(text)
    action = channels["action"]
    speech = channels["speech"]
    q_clauses = channels["question_clauses"]
    s_clauses = channels["statement_clauses"]

    # Guard: "อย่าหยุด" / "ไม่หยุด" / "โดยไม่หยุด" / "don't stop" is continuation, never a stop
    dont_stop_pat = r"อย่าหยุด|ไม่หยุด|โดยไม่หยุด|หยุดไม่ได้|\b(?:don\W?t\s+stop|do\s+not\s+stop|never\s+stop|can\W?t\s+stop)\b"
    speech_no_dont = re.sub(dont_stop_pat, " ", speech)
    s_clauses_no_dont = re.sub(dont_stop_pat, " ", s_clauses)
    q_clauses_no_dont = re.sub(dont_stop_pat, " ", q_clauses)
    action_no_dont = re.sub(dont_stop_pat, " ", action)

    has_dont_stop = bool(re.search(dont_stop_pat, speech) or re.search(dont_stop_pat, action))

    # 1. Check if user is asking a question about stopping/pausing ("หยุดไหม?", "จะหยุดเหรอ?", "พอแล้ว?", "พอหรือยัง?")
    stop_word_pat = r"พอ(?:แล้ว|แค่นี้|หรือยัง|รึยัง|ไหม|มั้ย|เหรอ)?|พัก(?:ก่อน|ไหม|มั้ย)?|เลิก(?:ทำ)?|ไม่เอา(?:แล้ว)?|\b(?:stop|enough|pause|rest|quit)\b"
    is_stop_question = bool(q_clauses_no_dont and re.search(stop_word_pat, q_clauses_no_dont))

    # 2. Check declarative/imperative speech for hard stop vs pause
    hard_stop_speech_pat = (
        r"หยุดเย็ด|หยุดเอา|หยุดมีเซ็กซ์|หยุด|หยุดทำ(?:เดี๋ยวนี้|เลย)?|"
        r"ไม่เอาแล้ว|พอแล้ว|พอแค่นี้(?:แหละ|นะ|เถอะ)?|เลิกทำ(?:เถอะ|เลย)?|ทำต่อไม่ไหว|ไม่สามารถทำต่อ|จบฉาก|"
        r"\b(?:stop\s+now|no\s+more|stop\s+it|end\s+scene|cannot\s+continue)\b"
    )
    pause_speech_pat = r"^(?:พอ|พัก|พักก่อน|ช้าก่อน|รอก่อน|เดี๋ยวก่อน|หยุดก่อน|hold|pause|wait|rest)(?:\s*(?:ก่อน|แป๊บ|แป๊บนึง|นิดนึง|สักครู่|นะ|หน่อย|ค่ะ|ครับ))?$"

    # Conditional care offer ("ถ้าเหนื่อยพักได้นะ", "ถ้าไม่ไหวบอกให้หยุดได้") is not a stop command
    conditional_care = bool(
        re.search(r"ถ้า[^\n.!?]{0,80}(?:พัก|พอ)[^\n.!?]{0,40}(?:ได้|บอก|นะ|ก็ได้)", s_clauses_no_dont)
        or re.search(r"\bif\s+[^\n.!?]{0,80}(?:need|want|tired|can't)[^\n.!?]{0,40}(?:rest|stop|pause)", s_clauses_no_dont)
    )

    # A question about stopping is not an instruction to stop.  Resolve this
    # before ordinary speech so a mixed sentence such as "หยุดไหม? เราควร..."
    # cannot be promoted to hard_stop merely because another clause contains
    # a stop word.  An explicit hard-stop clause in the same message still
    # wins below.
    if is_stop_question and not re.search(
        r"หยุดเดี๋ยวนี้|หยุดทำ(?:เดี๋ยวนี้|เลย)?|หยุดเย็ด|หยุดเอา|หยุดมีเซ็กซ์|"
        r"ไม่เอาแล้ว|พอแล้ว|พอแค่นี้|เลิกทำ|\b(?:stop\s+now|no\s+more|stop\s+it|end\s+scene)\b",
        s_clauses_no_dont,
    ):
        return {
            "kind": "question_stop",
            "source": "speech_question",
            "force": "character_decision",
            "reason": "question asking whether to stop/pause",
            "channels": channels,
        }

    if s_clauses_no_dont and not conditional_care:
        # Standalone pause in speech ("พอก่อน", "พัก", "หยุดก่อน", "พักแป๊บ")
        if re.fullmatch(pause_speech_pat, s_clauses_no_dont.strip()):
            return {"kind": "pause_action", "source": "speech_request", "force": "character_decision", "reason": "spoken standalone pause request", "channels": channels}
        # Definitive stop in declarative/imperative speech (not followed by an immediate positive action like "หยุดพูดแล้วจูบ")
        if re.search(hard_stop_speech_pat, s_clauses_no_dont) and not re.search(r"หยุด(?:พูด|ถาม|มอง|คิด|ล้อ)", s_clauses_no_dont):
            return {"kind": "hard_stop", "source": "speech_command", "force": "immediate", "reason": "declarative/imperative stop command in speech", "channels": channels}

    # 3. Check physical action inside `*...*`
    if action_no_dont:
        # Physical pause of motion inside `*...*` (e.g. `*หยุดขยับ*`, `*หยุดซอยเอว*`, `*หยุดกระแทกชั่วครู่*`, `*ชะงัก*`, `*พักหายใจ*`)
        # Crucially, `*หยุด*` or `*หยุดขยับ*` is a physical motion pause, NOT a scene termination!
        physical_pause_pat = (
            r"^(?:หยุด|พัก|ชะงัก|นิ่ง)\b|"
            r"หยุด(?:ขยับ|ซอย|กระแทก|เด้ง|โยก|เคลื่อนไหว|จังหวะ|มือ|นิ้ว|เอว|สะโพก|ทำชั่วครู่)|"
            r"พัก(?:จังหวะ|หายใจ|เหนื่อย|เอว)|ชะลอ(?:จังหวะ)?แล้วหยุด|"
            r"\b(?:stop(?:s|ped|ping)?\s+(?:moving|thrusting|bouncing|motion)|pause(?:s|d)?\s+(?:movement|rhythm|for\s+a\s+moment)|freeze(?:s)?|hold(?:s)?\s+still)\b"
        )
        # Full scene withdrawal/exit inside `*...*` (must explicitly withdraw body and end sexual contact or dress/leave)
        physical_exit_pat = (
            r"(?:ผละ|ดึง|ถอย)(?:ร่าง|กาย|ตัว)(?:ออกห่าง|ออกจากกัน|ออกแล้ว(?:แต่งตัว|ลุกหนี|เดินหนี|เลิกทำ))|"
            r"หยุด(?:มีเซ็กซ์|ร่วมรัก|ทำเรื่องอย่างว่า)(?:แล้ว|ทันที)|"
            r"\b(?:pull(?:s|ed)?\s+away\s+completely|get(?:s)?\s+dressed\s+and\s+leave(?:s)?)\b"
        )
        if re.search(physical_exit_pat, action_no_dont) and not re.search(r"(?:เพื่อ|เปลี่ยนท่า|พลิกตัว|แล้วจูบ|แล้วกอด|แล้วซอย|แล้วกระแทก)", action_no_dont):
            return {"kind": "hard_stop", "source": "physical_action", "force": "immediate", "reason": "narrated full physical withdrawal from scene", "channels": channels}
        if re.search(physical_pause_pat, action_no_dont):
            # Only a pause if they aren't simultaneously starting a new penetrative/foreplay act after "แล้ว..."
            if not re.search(r"หยุด.{0,20}แล้ว.{0,15}(?:สอดใส่|กระแทก|ซอย|ขย่ม|เลีย|ดูด|จูบ)", action_no_dont):
                return {"kind": "pause_action", "source": "physical_action", "force": "already_happened", "reason": "narrated physical pause in *...*", "channels": channels}

    if is_stop_question:
        return {"kind": "question_stop", "source": "speech_question", "force": "character_decision", "reason": "question asking whether to stop/pause", "channels": channels}

    if has_dont_stop:
        return {"kind": "dont_stop", "source": "speech_or_action", "force": "continue", "reason": "continuation plea (do not stop)", "channels": channels}

    return {"kind": "none", "source": "none", "force": "none", "reason": "", "channels": channels}


def has_explicit_roleplay_markup(text: Any) -> bool:
    """True only when USER marks a physical action that is already happening."""
    raw = str(text or "")
    # A single pair is action markup. Markdown bold (`**...**`) is not.
    return bool(re.search(r"(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)", raw, re.DOTALL))


def is_unmarked_character_request(text: Any) -> bool:
    """Any non-action wording is a request that CHAR may accept, refuse, or clarify.

    Text without single-asterisk action markup must not advance canonical pacing or force posture. Direct stops
    and explicit /pace commands remain control commands by design.
    """
    raw = str(text or "").strip()
    if not raw or has_explicit_roleplay_markup(raw) or raw.casefold().startswith("/pace"):
        return False
    semantic = classify_scene_words(raw)
    if semantic["refusal"] or semantic["defer"]:
        return False
    return bool(
        position_semantic_contract(raw)
        or is_direct_h_mode_continuation(raw)
        or semantic["intimacy_action"]
        or semantic["foreplay_action"]
        or semantic["explicit_action"]
        or semantic["sexual_motion"]
    )


def character_rejects_normal_intimacy(reply: Any) -> bool:
    """Return true only for CHAR's clear, genuine discomfort, disgust, or refusal.
    
    The decision is based strictly on the meaning of CHAR's response, avoiding false
    positives from shy / tsundere double negations (e.g. ไม่ได้ห้าม, ไม่ได้ไม่อยาก)
    or playful / affectionate hesitation.
    """
    raw_text = str(reply or "").strip()
    words = _scene_words(reply)
    if not words:
        return False

    # Continuation wording can contain the token `หยุด` but has the opposite
    # meaning: `อย่าหยุด`, `ไม่ต้องหยุด`, and `ทำต่อ` are an in-story request
    # to continue, never a boundary refusal.  Check this before the generic
    # refusal vocabulary below so a positive reply cannot hard-stop a scene.
    if re.search(
        r"อย่า(?:เพิ่ง|พึ่ง)?หยุด|ไม่ต้องหยุด|ห้ามหยุด|อยากให้(?:ทำ)?ต่อ|ทำต่อ(?:เลย|นะ|สิ)?|"
        r"\b(?:don't stop|do not stop|keep going|continue)\b",
        words,
        re.I,
    ):
        return False

    # Check for tsundere / double negation / non-refusal patterns
    if re.search(r"ไม่ได้(?:ห้าม|ว่าอะไร|รังเกียจ|อึดอัด|ปฏิเสธ|ไม่อยาก|ไม่ชอบ)|"
                 r"not (?:disgusted|uncomfortable|refusing|saying no)", words, re.I):
        return False

    # Must be genuine refusal or disgust
    if re.search(r"ไม่อยาก|ไม่เอา|ไม่ชอบ|ไม่พร้อม|ไม่สะดวก|รังเกียจ|ขยะแขยง|อึดอัด|ถอย(?:ออก|ไป)|(?<!อย่า)(?<!ไม่)หยุด(?:ก่อน|นะ|ที)?|"
                 r"\b(?:i(?:'m| am) not (?:comfortable|ready)|i don\W?t (?:want|like)|disgust(?:ed|ing)?|gross|back off)\b", words, re.I):
        # Exclude moaning or pleasure groans that happen during intimacy
        if re.search(r"อ๊า|อ๊ะ|อื้อ|อืม|เสียว|ซี้ด|\b(?:ah+|oh+|mm+)\b", raw_text, re.I):
            return False
            
        # ป้องกันคำพูดตอนเหนื่อยหอบ/ขอพักใน Aftercare ไปเผลอ Hard Stop ฉาก
        if re.search(r"เหนื่อย|หมดแรง|ไม่ไหว|ขอพัก|พักก่อน|\b(?:tired|exhausted|need a break)\b", words, re.I):
            return False
            
        return True
    return False


def character_refuses_user_starred_action(reply: Any, user_text: Any) -> bool:
    """Whether CHAR clearly rejects the USER's current narrated action.

    Asterisks mark a physical attempt/event in this roleplay format. They do
    not make CHAR's consent automatic; ordinary dialogue alone is excluded.
    """
    return bool(re.search(r"\*[^*]+\*", str(user_text or ""), re.DOTALL)) and character_rejects_normal_intimacy(reply)


def character_confirms_stop(reply: Any) -> bool:
    """Whether CHAR explicitly refuses or confirms to stop.
    
    Must be a clear statement to stop, not a counter-question and not sensual moaning/pleasure groans.
    """
    raw_text = str(reply or "").strip()
    words = _scene_words(reply)
    if not words:
        return False

    # 1. ต้องไม่ใช่การถามกลับ (ไม่ใช่คำถาม)
    if re.search(r"\?|ไหม|มั้ย|หรือยัง|รึยัง|หรือเปล่า|หรือไม่|เหรอ|หรือคะ|หรือครับ|ทำไม", raw_text):
        return False

    # 2. ปฏิเสธหรือยืนยันอย่างชัดเจนว่า ให้หยุด, ไม่ต้องการทำต่อแล้ว/ไม่ทำอีกต่อไป
    definitive_stop = bool(re.search(
        r"ให้หยุด|ไม่(?:ต้อง)?การทำต่อ(?:แล้ว)?|ไม่ทำ.{0,15}อีกต่อไป|ไม่ทำต่อแล้ว|หยุดทำเถอะ|พอแค่นี้เถอะ|หยุดเถอะ|พอเถอะ|"
        r"\b(?:stop now|let's stop|won't continue|cannot continue anymore|i want to stop|please stop)\b",
        words, re.I
    ))

    # 3. ตรวจสอบวลี พอแล้ว / ไม่ไหวแล้ว: เว้นกรณีที่เป็นการครวญคราง/เคลิ้มเสียว
    conditional_stop = bool(re.search(r"พอแล้ว|ไม่ไหวแล้ว", words))
    if conditional_stop:
        moaning_or_pleasure = bool(re.search(
            r"อ๊า|อ๊ะ|อือ|อืม|เสียว|ซี้ด|ฮื่อ|แฮ่ก|คราง|กระตุก|เคลิ้ม|รัด|แน่น|แรงอีก|ดีจัง|"
            r"\b(?:ah+|oh+|mm+|ng+|fuck|so good|pleasure|moan)\b",
            raw_text, re.I
        ))
        # ถ้าไม่มีเสียงครางหรือความเสียว และมีบริบทให้ยุติจริง
        if not moaning_or_pleasure and re.search(r"เหนื่อยมาก|เจ็บ|พอแล้วล่ะ|ไม่ไหวแล้วล่ะ|ขอพัก", words):
            definitive_stop = True

    return definitive_stop


def apply_character_action_refusal(
    previous_value: Any,
    current_value: Any,
    reply: Any,
    user_text: Any,
    cnc_agreement: bool = False,
) -> Dict[str, Any]:
    """Stop an active scene when CHAR rejects the current USER starred action or confirms stopping."""
    current = normalize(current_value)
    previous = normalize(previous_value)
    
    # Requirement 4: When user asks or indicates stopping, scene only stops if character confirms/refuses clearly
    user_asked_or_requested_stop = bool(re.search(r"หยุด|พอ|เลิก|ไม่ทำ", str(user_text or "").casefold()))
    if user_asked_or_requested_stop and character_confirms_stop(reply):
        if previous["active"]:
            refused = hard_stop(previous)
            return normalize({
                **refused,
                "gear_shift": {
                    "action": "character_boundary_refusal",
                    "from": f"{previous['stage']}:{previous['stage_level']}", "to": "normal:0",
                    "reason": "CHAR explicitly confirmed to stop intimacy",
                },
                "reason": "CHAR explicitly confirmed/refused to continue intimacy; scene stopped",
                "interruption": {**(refused.get("interruption") or {}), "source": "character_boundary", "unresolved": True},
            })

    # When CNC session is enabled, in-character refusal or resistance to USER's
    # narrated physical action is treated as fictional roleplay resistance
    # rather than triggering an automatic system scene stop.
    if cnc_agreement:
        return current

    if not character_refuses_user_starred_action(reply, user_text):
        return current
    # Normal-entry actions use the provisional-entry gate below; it restores
    # Normal without inventing an interruption.
    if not previous["active"]:
        return current
    refused = hard_stop(previous)
    return normalize({
        **refused,
        "gear_shift": {
            "action": "character_boundary_refusal",
            "from": f"{previous['stage']}:{previous['stage_level']}", "to": "normal:0",
            "reason": "CHAR clearly refused the USER's narrated physical action",
        },
        "reason": "CHAR refused the USER's narrated physical action; scene stopped",
        "interruption": {**(refused.get("interruption") or {}), "source": "character_boundary", "unresolved": True},
    })


def resolve_normal_intimacy_character_response(value: Any, reply: Any) -> Dict[str, Any]:
    """Commit or cancel a provisional Normal → Intimacy/Foreplay transition."""
    state = normalize(value)
    if not state.get("normal_intimacy_pending_acceptance"):
        return state
    # When CNC agreement is enabled, keep the scene active and transition accepted
    if state.get("normal_intimacy_cnc_agreement"):
        return normalize({
            **state,
            "normal_intimacy_pending_acceptance": False,
            "normal_intimacy_cnc_agreement": True,
            "reason": "character accepted normal-mode intimacy action",
        })
    if character_rejects_normal_intimacy(reply):
        return normalize({
            **state,
            "stage": "normal", "scene_stage": "normal", "active": False,
            "stage_level": 0, "turns_in_level": 0, "h_mode_quest": {},
            "normal_intimacy_pending_acceptance": False,
            "normal_intimacy_cnc_agreement": False,
            "gear_shift": {
                "action": "normal_entry_declined", "from": f"{state['stage']}:{state['stage_level']}",
                "to": "normal:0", "reason": "character declined normal-mode intimacy action",
            },
            "reason": "character declined normal-mode intimacy action",
        })
    return normalize({
        **state, "normal_intimacy_pending_acceptance": False,
        "normal_intimacy_cnc_agreement": False,
        "reason": "character accepted normal-mode intimacy action",
    })


def canonical_h_action_request(text: Any) -> str:
    """Translate common Thai imperative H-Mode actions into a stable intent label."""
    contract = position_semantic_contract(text)
    return str(contract.get("action") or "") if contract else ""


# A position is not just a keyword.  It fixes the minimum spatial facts that
# the model must carry into its reply: who is above/behind/facing whom, CHAR's
# support points, and the next physical movement.  This deliberately does not
# imply penetration; the active canonical stage still decides the allowed act.
POSITION_SEMANTIC_CONTRACTS = (
    {
        "id": "reverse_cowgirl",
        "pattern": r"(?:reverse\s*cowgirl|รีเวิร์ส\s*คาวเกิร์ล|ท่าหันหลัง|ท่าผู้หญิงหันหลัง|หันหลัง(?:ขึ้น)?(?:ขย่ม|คร่อม)|ขึ้น(?:ขย่ม|คร่อม).*หันหลัง|ขย่ม.*หันหลัง)",
        "char_posture": "CHAR straddles USER from above, facing away from USER, supported by CHAR's knees or feet",
        "user_frame": "USER is directly beneath CHAR in the established supported posture",
        "movement": "CHAR takes the top position and controls the established rhythm while facing away",
        "action": "CHAR mounts USER facing away and rides/bounces on the already established contact",
    },
    {
        "id": "cowgirl",
        "pattern": r"(?:ขึ้น\s*(?:ไป)?\s*(?:ขย่ม|คร่อม|ให้(?:หน่อย|สิ|เลย)?)|ขึ้นให้(?:หน่อย|สิ|เลย)?|ขย่ม\s*(?:ให้(?:หน่อย|สิ|เลย)?|ชั้น|ฉัน|ผม|เรา)|นั่งคร่อม(?:ตัก)?|ท่าผู้หญิงอยู่บน|ท่าคาวเกิร์ล|คาวเกิร์ล|(?:cowgirl|ride\s*me|riding\s*me|straddle\s*me))",
        "char_posture": "CHAR straddles USER from above, supported by CHAR's knees or feet; CHAR faces USER by default unless CHAR-led initiative chooses the reverse-facing variation",
        "user_frame": "USER is directly beneath CHAR in the established supported posture",
        "movement": "CHAR takes the top position and controls the established rhythm",
        "action": "CHAR mounts or straddles USER and rides/bounces on the already established contact",
    },
    {
        "id": "doggy_style",
        "pattern": r"(?:ท่าหมา|ท่าจากด้านหลัง|ท่าสี่ขา|สี่ขา|คลานเข่า|คุกเข่าโก่ง|doggy(?:\s*style)?|on\s+all\s+fours|from\s+behind)",
        "char_posture": "CHAR is on hands and knees or bent forward with weight supported by knees and hands/forearms",
        "user_frame": "USER is positioned behind CHAR in the established contact frame",
        "movement": "CHAR presents the established contact from behind and moves only as the current stage permits",
        "action": "CHAR moves into the from-behind, all-fours position with USER behind CHAR",
    },
    {
        "id": "missionary",
        "pattern": r"(?:มิชชันนารี|ท่ามิชชันนารี|ท่านอนหงาย|missionary|นอนหงาย.*(?:ทับ|ด้านบน)|กด(?:ชั้น|ฉัน|เธอ)?ลง(?:บน)?(?:เตียง|พื้น)?)",
        "char_posture": "CHAR lies on their back with shoulders and hips supported by the established surface",
        "user_frame": "USER is above and facing CHAR in the established contact frame",
        "movement": "CHAR remains beneath USER and responds within the established face-to-face contact",
        "action": "CHAR moves into the face-to-face lying position with USER above CHAR",
    },
    {
        "id": "spooning",
        "pattern": r"(?:ท่าช้อน|ท่าตะแคง|ท่าตะแคงซ้อน|นอนกอดจากด้านหลัง|spoon(?:ing)?|side[- ]by[- ]side.*behind)",
        "char_posture": "CHAR lies on their side with USER close behind, legs and torso aligned",
        "user_frame": "USER lies behind CHAR in the established side-lying contact frame",
        "movement": "CHAR stays side-lying and responds through the established close rear contact",
        "action": "CHAR moves into a side-lying spooning position with USER behind CHAR",
    },
    {
        "id": "lap_straddle",
        "pattern": r"(?:คร่อมตัก|ท่าคร่อมตัก|นั่งบนตัก|นั่งตัก|lap\s*straddle|sit\s+on\s+(?:my|the)\s+lap)",
        "char_posture": "CHAR straddles USER's lap while USER is seated, facing USER unless another direction is named",
        "user_frame": "USER is seated and supports CHAR at the lap/torso contact point",
        "movement": "CHAR settles onto USER's lap and moves only within the established contact",
        "action": "CHAR straddles USER's seated lap and continues the established contact",
    },
    {
        "id": "seated_face_to_face",
        "pattern": r"(?:นั่งหันหน้าเข้าหา|ท่านั่งประจันหน้า|นั่งประจันหน้า|face[- ]to[- ]face\s*(?:seated|sitting)|lotus\s*position)",
        "char_posture": "CHAR is seated facing USER with bodies close and balance supported by the established seat/surface",
        "user_frame": "USER is seated facing CHAR in the established close contact frame",
        "movement": "CHAR maintains seated face-to-face contact and moves only as the current stage permits",
        "action": "CHAR moves into a seated face-to-face position with USER",
    },
    {
        "id": "standing",
        "pattern": r"(?:ท่ายืน|ท่ายืนร่วมรัก|ยืน(?:ทำ|ต่อ|เอา)|standing(?:\s+sex)?|stand\s+up)",
        "char_posture": "CHAR stands upright with a confirmed nearby support if the scene provides one",
        "user_frame": "USER stands close in the established contact frame",
        "movement": "CHAR changes to standing only if the current location safely supports it",
        "action": "CHAR moves into the established standing position with USER",
    },
    {
        "id": "wall_supported",
        "pattern": r"(?:ท่าพิงกำแพง|ชิดกำแพง|ติดกำแพง|พิงกำแพง|wall(?:\s+sex|\s+position)?|against\s+the\s+wall)",
        "char_posture": "CHAR is upright with back or hands supported against the confirmed wall",
        "user_frame": "USER stands directly in front of CHAR in the established contact frame",
        "movement": "CHAR uses the wall as support and stays in the confirmed upright contact position",
        "action": "CHAR moves into the wall-supported position with USER in front",
    },
    {
        "id": "prone",
        "pattern": r"(?:ท่านอนคว่ำ|นอนคว่ำ|คว่ำหน้า|prone(?:\s+position)?|face\s+down)",
        "char_posture": "CHAR lies face down with chest and hips supported by the established surface",
        "user_frame": "USER is behind or above CHAR only if that relation is already established or explicitly named",
        "movement": "CHAR remains prone and does not invent a new contact direction",
        "action": "CHAR moves into the face-down prone position",
    },
    {
        "id": "edge_of_bed",
        "pattern": r"(?:ท่าริมเตียง|ริมเตียง|ขอบเตียง|นั่งริมเตียง|edge\s+of\s+(?:the\s+)?bed)",
        "char_posture": "CHAR sits or reclines at the edge of the established bed or supported surface, with legs positioned as explicitly requested",
        "user_frame": "USER is directly in front of CHAR or between CHAR's legs only if the existing act establishes it",
        "movement": "CHAR uses the confirmed edge as support and preserves the established contact direction",
        "action": "CHAR moves to the supported edge-of-bed position",
    },
    {
        "id": "bent_over_support",
        "pattern": r"(?:ท่าก้มพาด|ก้มพิง|ก้มกับ(?:โต๊ะ|ผนัง|โซฟา)|พาด(?:โต๊ะ|โซฟา)|bent\s+over|over\s+the\s+(?:table|sofa))",
        "char_posture": "CHAR bends forward with hands, forearms, or torso supported by the explicitly named existing surface",
        "user_frame": "USER remains behind or beside CHAR only when that relation is established by the request or current act",
        "movement": "CHAR maintains the supported bent posture without inventing a different location or surface",
        "action": "CHAR moves into the supported bent-over position",
    },
    {
        "id": "raised_leg",
        "pattern": r"(?:ท่ายกขา|ยกขา(?:พาดไหล่)?|ขาพาดไหล่|leg\s+up|leg\s+on\s+(?:my|your)\s+shoulder)",
        "char_posture": "CHAR lies or reclines in the established face-to-face frame with one leg raised as explicitly requested",
        "user_frame": "USER stays in the already established facing contact frame",
        "movement": "CHAR raises only the named leg and otherwise preserves the current confirmed position",
        "action": "CHAR takes the raised-leg variation of the established face-to-face position",
    },
    {
        "id": "oral_kneeling",
        "pattern": r"(?:ท่าคุกเข่าตรงหน้า|คุกเข่า(?:อม|ใช้ปาก)|คุกเข่าตรงหน้า|oral\s+on\s+knees|kneel\s+(?:and\s+)?(?:give|perform)\s+oral)",
        "char_posture": "CHAR kneels in front of USER, with knees supporting CHAR's weight and face oriented toward USER",
        "user_frame": "USER is directly in front of CHAR in the established oral-contact frame",
        "movement": "CHAR takes the kneeling oral-service position only when the current stage permits the established act",
        "action": "CHAR kneels in front of USER for the established oral contact",
    },
    {
        "id": "oral_reclining",
        "pattern": r"(?:ท่านอนให้เลีย|นอนให้เลีย|นอนให้กิน|เอนให้เลีย|recline\s+for\s+oral|oral\s+while\s+reclining)",
        "char_posture": "CHAR reclines on the established supported surface with the requested lower-body access, without inventing a new surface",
        "user_frame": "USER is positioned at CHAR's lower body only when the request or established act confirms it",
        "movement": "CHAR remains reclined and responds within the established oral-contact frame",
        "action": "CHAR reclines for the established oral contact",
    },
    {
        "id": "sixty_nine",
        "pattern": r"(?:ท่าหกเก้า|หกเก้า|ท่า69|69\s*(?:position)?|sixty[- ]nine)",
        "char_posture": "CHAR and USER lie in opposite directions with each person's face aligned directly to the other's lower genitals [Organ Pairing: Reciprocal Oral - Mouth to Genitals]",
        "user_frame": "USER shares the reciprocal opposite-facing oral-genital contact arrangement with CHAR",
        "movement": "CHAR takes the reciprocal mutual-oral position only within the established stage and consent frame; strictly isolate from penetrative intercourse",
        "action": "CHAR moves into the reciprocal sixty-nine mutual oral position with USER",
    },
    {
        "id": "face_sitting",
        "pattern": r"(?:ท่านั่งทับหน้า|นั่งทับหน้า|คร่อมหน้า|face\s*sitting|sit\s+on\s+(?:my|your)\s+face)",
        "char_posture": "CHAR straddles and lowers vulva/pelvis/buttocks directly over USER's face/mouth [Organ Pairing: Pelvis/Vulva/Anus over Facial Mouth/Tongue]",
        "user_frame": "USER lies or reclines beneath CHAR with face directly serving as the contact surface for CHAR's lower body",
        "movement": "CHAR controls the contact pressure from above and only continues oral/cunnilingus contact as the stage permits; strictly isolate from lap straddle or penetrative acts",
        "action": "CHAR moves into the face-sitting position lowering pelvis over USER's face",
    },
)


def position_semantic_contract(text: Any) -> Dict[str, str]:
    """Resolve a Thai/English position request into one authoritative frame.

    The result is safe to inject into the prompt and is intentionally compact:
    a position command changes spatial arrangement, while stage transitions and
    the precise sexual act remain the responsibility of canonical scene state.
    """
    words = _scene_words(text)
    for contract in POSITION_SEMANTIC_CONTRACTS:
        if re.search(contract["pattern"], words, re.IGNORECASE):
            return {key: str(value) for key, value in contract.items() if key != "pattern"}
    return {}


def character_led_h_mode_request(text: Any) -> bool:
    """Whether USER explicitly hands the next H-Mode movement to CHAR."""
    words = _scene_words(text)
    position = position_semantic_contract(words)
    if position.get("id") in {"cowgirl", "reverse_cowgirl"}:
        return True
    return bool(re.search(
        r"(?:นำ(?:เลย|สิ)?|เป็นฝ่าย(?:รุก|นำ)|รุก(?:เลย|สิ)?|เริ่ม(?:เลย|สิ)?|ต่อ(?:เลย|สิ)|จัด(?:เลย|สิ)?|"
        r"(?:ขย่ม|เด้งรับ)(?:ชั้น|ฉัน|ผม|เรา)?(?:สิ|เลย|หน่อย)?|"
        r"ทำ(?:ต่อ(?:เลย|สิ)?|เอง|ต่อเอง)|take\s+the\s+lead|lead\s+the\s+way|make\s+the\s+first\s+move)",
        words,
        re.IGNORECASE,
    ))


def is_direct_h_mode_continuation(text: Any) -> bool:
    """Recognize a short physical continuation cue after stripping chat markup/quotes."""
    words = _scene_words(text)
    return bool(re.fullmatch(
        r"(?:ทำต่อ(?:เลย|สิ)?|ต่อ(?:เลย|สิ)|นำ(?:เลย|สิ)?|เริ่ม(?:เลย|สิ)?)\s*[.!?…]*",
        words,
        re.IGNORECASE,
    ))


def character_led_h_mode_prompt(text: Any) -> str:
    """Explain a user-granted CHAR-choice turn in direct English for the model."""
    if not character_led_h_mode_request(text):
        return ""
    direct_continuation = is_direct_h_mode_continuation(text)
    if direct_continuation:
        return (
            "[Direct physical continuation — authoritative]\n"
            "The latest USER input is a direct physical instruction to continue the established H-Mode sexual activity. "
            "`ทำต่อเลย` / `ทำต่อสิ` / `ต่อเลย` mean continue performing the current sexual act, not continue writing, "
            "continue a story, explanation, narration, topic, or dialogue. CHAR must physically continue the current act "
            "now. In Explicit, CHAR must lead one concrete "
            "follow-through of the established act immediately; do not ask what to continue, do not explain the phrase, "
            "do not reply with passive agreement, and do not wait for another USER action. Preserve the canonical stage, "
            "posture, target, consent, and H-energy limits. If Explicit is active but the saved Current Situation.ACT is "
            "still a non-sexual aftercare action, treat that ACT as stale: CHAR must choose and begin one concrete "
            "stage-permitted explicit act instead of claiming that context is missing or asking what to do.\n"
        )
    return (
        "[CHAR-choice H-Mode guidance — authoritative]\n"
        "The USER's input gives CHAR a decision point for the next beat. CHAR is not required to initiate physical action "
        "on every turn. Interpret the input and choose the most natural stage-permitted response for CHAR's personality "
        "and current body state: CHAR may act, answer spoken dialogue, answer a question, ask one clarifying question, "
        "slow down, defer, or refuse. Keep USER's actions, choices, feelings, and consent under USER control.\n"
        "A clear direct physical command remains a command: carry out its confirmed arrangement or action unless CHAR has "
        "an established boundary or a stage rule that prevents it. Once that command is satisfied, CHAR may choose the "
        "next connected follow-through rather than being locked to a fixed script. For example, after a permitted top "
        "position, a woman/feminine CHAR may keep facing USER, choose the reverse-facing variation, guide the pace with "
        "her own hands/hips, speak, or pause for a question—only when those choices fit the established stage and context. "
        "In Foreplay/Explicit, mouth- or hand-led intimate action is available only when the established context and stage "
        "permit it. These are choices, not a menu to list or a mandatory action.\n"
        "In Intimacy, keep choices to closeness/kissing/holding or dialogue. In Foreplay, choose sensual non-penetrative "
        "responses. In Explicit, CHAR may choose a position, pace, or established intimate technique. When the USER "
        "says a direct continuation cue such as `ทำต่อเลย`, `ทำต่อสิ`, `ต่อเลย`, `นำเลย`, or `continue` during "
        "Explicit 1/2/3, CHAR must lead one concrete follow-through of the already established act immediately; do not "
        "reply with passive agreement, ask what to do, or wait for another USER action. In Climax, a "
        "requested position change remains allowed but CHAR resumes the established peak afterward. In Aftercare, a "
        "direct non-question continuation such as `ทำต่อเลย`, `ทำต่อสิ`, `ต่อเลย`, or `continue` is a clear USER "
        "answer to continue and must follow the server-authorized transition to Explicit 1; do not ask again. Without "
        "that direct answer, choose only recovery, ordinary dialogue, or a question about continuing. Never invent a new act outside those limits, "
        "skip the canonical stage, or claim USER moved first.\n"
    )


def position_semantic_prompt(text: Any) -> str:
    """Render the resolved position as a concise model-facing semantic contract."""
    contract = position_semantic_contract(text)
    if not contract:
        return ""
    concrete_execution = ""
    if contract["id"] == "cowgirl":
        concrete_execution = (
            "[Concrete execution for the Thai request `ขึ้นขย่มชั้นสิ`]\n"
            "Meaning: USER is telling CHAR to get on top of USER and ride. CHAR is the actor; USER does not need to "
            "perform or explain anything. CHAR begins by moving over USER and taking the top position. Because USER has "
            "also handed initiative to CHAR, she may choose whether to face USER or turn around into the reverse-facing "
            "variation, then settles into the already established contact and controls the rhythm. The visible reply must "
            "narrate at least the move onto USER and one resulting movement or body reaction. Do not reply with confusion, "
            "a definition, a question, a metaphor, or a request for clarification. This is a woman-led request: do not "
            "merely say CHAR is willing; make CHAR take control of the opening movement now.\n"
        )
    return (
        "[Canonical H-Mode position contract — authoritative]\n"
        f"Position: {contract['id']}.\n"
        f"CHAR posture now: {contract['char_posture']}.\n"
        f"USER frame: {contract['user_frame']}.\n"
        f"Required response frame: {contract['movement']}.\n"
        "Position-command priority: enact this requested body arrangement now in every active H-Mode stage, including "
        "Climax. It overrides any lower-level wording that says CHAR must remain still, reactive only, or take minimal "
        "actions. This is an approved posture change, not a new sexual act or stage transition. After moving, resume "
        "the current stage's limits. Do not ask what the position means, reinterpret it as ordinary dialogue, or substitute "
        "another position. Update Current Situation.ACT to the position change and Current Situation.POSTURE in English to "
        "the resulting CHAR posture.\n"
        + concrete_execution
    )


SEX_ACT_SEMANTIC_CONTRACTS = (
    ("sexual_motion", r"ขย่ม|เด้งรับ|เด้ง(?:ขึ้นลง|ต่อ)?|กระเด้า|เด้า|ฟัดเด้า|ถูไถ|บดเบียด|โยกสะโพก|โยกเอว|ควบ|ขี่|\b(?:bounce|bouncing|humping|grinding|riding|rocking hips?)\b", "CHAR performs the recognized character-led sexual motion according to the confirmed actor, act, position, and posture. A motion command does not change position unless the USER separately names a position. `ขึ้นขย่ม` or a named top-position command may resolve to a top position through the position contract."),
    ("male_genital_twitch", r"(?:ควย|ปลาย(?:ควย)?|หัวควย|ดุ้น|ท่อนเนื้อ|องคชาต).{0,18}(?:กระตุก|สั่น|ตุบ|เต้น)|(?:กระตุก|สั่น|ตุบ|เต้น).{0,18}(?:ควย|ปลาย(?:ควย)?|หัวควย|ดุ้น|ท่อนเนื้อ|องคชาต)", "[Anatomy Pairing: Male Genital Reflex] `กระตุก` describes involuntary twitching or pulsing of the penis/glans/shaft. Use it for male genital movement; do not call this vaginal `ตอด` or imply vaginal contraction."),
    ("vaginal_contraction", r"(?:ตอด(?:รัด)?|รัดตอด|ตอดตุบ|ตอดถี่)(?:.{0,18}(?:ช่องคลอด|ช่องรัก|กลีบ|รูรัก|ปากช่องคลอด))?|(?:ช่องคลอด|ช่องรัก|กลีบ|รูรัก|ปากช่องคลอด).{0,18}(?:ตอด(?:รัด)?|รัดตอด|ตอดตุบ|ตอดถี่)", "[Anatomy Pairing: Vaginal Contraction] `ตอด` or `ตอดรัด` describes rhythmic gripping, pulsing, or contracting of the vaginal canal/introitus and surrounding folds. Use it for vaginal anatomy only; do not use it for the penis/glans."),
    ("receptive_penetration", r"ถูกเอา|ถูกสอดใส่|ถูกดันเข้า|ถูกแทง|ถูกกระแทก|ถูกขย่ม|ถูกกระเด้า|ถูกซอย|ถูกกดเข้าไป|ถูกกดลึก|ถูกกดกระแทก|ถูกกดจนมิด|ถูกเติมเต็ม|\b(?:be\s+taken|be\s+penetrated|be\s+thrust\s+into|be\s+filled)\b", "[Organ Pairing: Vaginal Introitus and Phallus] CHAR receives the established penetrative act; `ถูกขย่ม` means CHAR is being repeatedly penetrated vaginally; preserve CHAR as the receptive actor and do not rewrite it as CHAR performing the act."),
    ("vaginal_penetration", r"เอาเข้าไป|เอากัน|โดนเอา|ถูกเอา|ยัด(?:เข้า|ใส่)?|ดันเข้า|แทงเข้า|แทง|กระแทก|ขย่ม|เด้งรับ|กระเด้า|เด้า|ฟัดเด้า|ฟัด(?:กัน|ต่อ)?|จัด(?:หนัก|ต่อ)?|กดเข้าไป|กดลึก|กดกระแทก|กดจนมิด|ซอย(?:เอว|สะโพก|ถี่|รัว|ยิก|ยับ|เข้า|ไม่ยั้ง|ต่อ)|กระแทกซอย|สอดใส่|มีเซ็กซ์|เย็ด|ร่วมรัก|\b(?:vaginal\s+penetration|intercourse|penetration|sex|fucking?)\b", "[Organ Pairing: Vaginal Canal/Introitus and Phallus/Shaft] Apply the recognized vaginal penetration motion between vaginal walls/cervix and the phallus/shaft with pubic bone friction. Preserve the existing position unless the USER separately requests a position change; do not infer anal or oral openings. A top position comes only from a separate position command such as `ขึ้นขย่ม`."),
    ("receptive_pressing", r"ถูกกด|ถูกกดทับ|ถูกกดแช่|ถูกกดร่าง|ถูกกดตัว|ถูกกดสะโพก|ถูกกดแนบ|ถูกตรึง|ถูกบดเบียด", "CHAR is the receptive actor and receives pressure, pinning, or body-to-body pressing; do not infer penetration."),
    ("active_pressing", r"กด(?:ทับ|แช่|ร่าง|ตัว|สะโพก|แนบ)?|ตรึง|บดเบียด", "CHAR or USER applies pressure, pins, or presses the established body contact according to the actor field; do not infer penetration."),
    ("receptive_anal_penetration", r"ถูกสอดด้านหลัง|ถูกเอาทางด้านหลัง|ถูกสอดทวาร|ถูกกดผ่านหูรูด|ถูกเติมเต็มด้านหลัง|\b(?:be\s+penetrated\s+from\s+behind|be\s+taken\s+from\s+behind|be\s+entered\s+anally)\b", "[Organ Pairing: Anal Sphincter/Rectum and Phallus/Shaft] CHAR receives the established anal act from behind; preserve receptive agency and require explicit anal wording."),
    ("anal_penetration", r"สอดใส่ด้านหลัง|เข้าประตูหลัง|สอดทวาร|แทงทวาร|กดดันผ่านหูรูด|\b(?:anal\s+penetration|enter\s+the\s+anus|penetrate\s+from\s+behind|take\s+the\s+rear|fuck\s+the\s+ass)\b", "[Organ Pairing: Anal Sphincter/Rectum and Phallus/Shaft] The established act is explicit anal penetration against muscular sphincter ring; require explicit anal wording and never substitute it for vaginal contact."),
    ("oral_sex", r"อมควย|ดูดควย|เลียปลาย|อมลำ|เป่าปี่|\b(?:blowjob|fellatio|oral\s+sex|sucking)\b", "[Organ Pairing: Facial Mouth/Lips/Tongue/Throat and Male Shaft/Glans] CHAR uses facial mouth, lips, and tongue to envelop and stroke the male shaft/head; do not invent penetration or genital contact."),
    ("cunnilingus", r"เลียหี|เลียจิ๋ม|ดูดเม็ด|เลียเม็ด|เลียกลีบ|กินหี|กินจิ๋ม|\b(?:cunnilingus|eat\s+out|licking\s+(?:pussy|clit|slit))\b", "[Organ Pairing: Facial Mouth/Lips/Tongue and Clitoris/Labia/Vaginal Introitus] CHAR or USER uses facial tongue and lips to lap, lick, and suck the clitoral bud and labial folds; do not confuse with facial kissing."),
    ("paizuri_titjob", r"ร่องอก|หนีบอก|ถูอก|เอาหน้าอก(?:ทำ|ถู|ปรนเปรอ)?|เอาเต้า(?:ทำ|ถู|บีบ)?|ใช้(?:นม|เต้า|หน้าอก).{0,10}(?:รูด|ขยับ|ประกบ|หนีบ)|\b(?:paizuri|titjob|boobjob|breast\s+play)\b", "[Organ Pairing: Breasts/Cleavage Groove and Male Shaft] Both breast mounds are pressed together to sandwich and slide along the male shaft; strictly isolate from vaginal or anal penetration."),
    ("footjob", r"ใช้เท้า|เอาเท้า(?:ทำ|ถู|รูด|หนีบ)|ฝ่าเท้าประกบ|เหยียบชัก|\b(?:footjob|sole\s+play)\b", "[Organ Pairing: Soles/Arches/Toes and Male Shaft] Soles and toes sandwich and stroke the male shaft; strictly isolate from vaginal or anal penetration."),
    ("deep_kiss", r"จูบปาก|บดจูบ|ประกบปาก|แลกลิ้น|จูบดูดดื่ม|ลิ้นนัวเนีย|ลิ้นพัวพัน|นัวเนียลิ้น|พัวพันลิ้น|ดูดลิ้น|กัดปาก|ขบปาก|กัดริมฝีปาก|ขบริมฝีปาก|ดูดปาก|ดูดริมฝีปาก|\b(?:deep\s+kiss|french\s+kiss|kiss\s+on\s+the\s+mouth|tongue\s+entanglement|lip\s+bite)\b", "[Organ Pairing: Facial Lips/Tongue and Facial Lips/Tongue] Intimate deep kiss with entwining tongues, suction, and playful lip bites; strictly isolate from genital actions."),
    ("manual_penis_stimulation", r"ชักรูด|ลูบขึ้นลง|กำรอบลำ|\b(?:handjob|manual\s+stimulation|stroking\s+penis)\b", "[Organ Pairing: Palm/Fingers and Male Shaft] CHAR or USER uses a hand to stroke the established penis contact; do not convert it into oral or penetrative sex."),
    ("breast_play", r"เค้นเต้า|บีบหน้าอก|ขยำอก|ดูดนม|เลียยอดอก|จุกนม|หัวนม|\b(?:breast\s+play|groping|sucking\s+breast|nipples)\b", "[Organ Pairing: Hands/Mouth and Breasts/Nipples] CHAR touches, squeezes, or mouths the established breast or nipple contact; do not infer genital contact."),
    ("female_self_stimulation", r"เกี่ยวเบ็ด|ติ้วหี|ช่วยตัวเอง|ขยี้เม็ด|คลึงเม็ด|สอดนิ้ว|\b(?:masturbation|fingering|clitoral\s+stimulation|rubbing\s+clit)\b", "[Organ Pairing: Fingers and Clitoris/Vaginal Canal] CHAR stimulates their own vulva, clitoris, or introitus with fingers; do not invent USER action."),
    ("sixty_nine_reciprocal_oral", r"ท่าหกเก้า|หกเก้า|ท่า69|69\s*(?:position)?|\b(?:sixty[- ]nine)\b", "[Organ Pairing: Mutual Oral - Facial Mouth/Tongue to Genitals of each partner] Reciprocal simultaneous oral service between both partners; strictly isolate from vaginal or anal intercourse."),
    ("face_sitting_oral", r"ท่านั่งทับหน้า|นั่งทับหน้า|คร่อมหน้า|\b(?:face\s*sitting|sit\s+on\s+(?:my|your)\s+face)\b", "[Organ Pairing: Pelvis/Vulva/Anus over Facial Mouth/Tongue] CHAR lowers lower pelvis/introitus onto USER's mouth for oral service; strictly isolate from lap straddle or penetrative intercourse."),
    ("partner_directed_solo", r"ช่วยตัวเองให้(?:ดู|ชม)|ทำให้(?:ดู|ชม)|เขี่ยให้(?:ดู|ชม)|ติ้วให้(?:ดู|ชม)|ขยี้ให้(?:ดู|ชม)|ถอดให้(?:ดู|ชม)|โชว์(?:หน่อย|สิ|ให้ดู)|\b(?:show\s+me|masturbate\s+for\s+me|touch\s+yourself\s+for\s+me|solo\s+show)\b", "[Role Scope: Partner-Directed Solo / Show] CHAR is the sole actor performing self-touch on CHAR's own body while USER observes; do not have CHAR touch or penetrate USER."),
    ("partner_service_request", r"(?:ทำให้|อมให้|เลียให้|ขย่มให้|ช่วยทำให้)(?:หน่อย|สิ|เลย)|\b(?:do\s+it\s+for\s+me|suck\s+me|ride\s+me\s+please)\b", "[Role Scope: Partner Service] CHAR actively provides intimate service to USER; actor is CHAR, target is USER's body."),
    ("rapid_cadence_action", r"ซอย(?:ถี่|รัว|ยิบ|หนัก)|กระแทก(?:รัว|ถี่|ยับ)|เร่ง(?:จังหวะ|ความเร็ว|เครื่อง)|ขย่ม(?:ถี่|รัว)|เร็วขึ้น(?:อีก|หน่อย)?|แรงขึ้น(?:อีก|หน่อย)?|\b(?:faster|harder|rapid|pounding\s+rapidly|accelerate)\b", "[Cadence Dynamic: Accelerated Pacing] High-velocity, rapid-cadence pelvic or manual strokes pushing toward peak intensity/climax; dialogue strictly compresses to broken gasps."),
    ("internal_ejaculation", r"น้ำกาม|หลั่งใน|แตกใน|พุ่งใส่ภายใน|\b(?:creampie|cum\s+inside|ejaculation\s+inside)\b", "[Organ Pairing: Internal Ejaculation into Vaginal/Anal Canal] Ejaculation inside the established canal is already confirmed; describe only its immediate established result and never add a new orgasm."),
)

def sex_act_semantic_prompt(text: Any) -> str:
    """Give the LLM one canonical English meaning for a recognized sex act."""
    words = _scene_words(text)
    matches = [
        (name, meaning) for name, pattern, meaning in SEX_ACT_SEMANTIC_CONTRACTS
        if re.search(pattern, words, re.IGNORECASE)
    ]
    # Generic scene labels still need a concrete channel so the LLM does not
    # invent penetration when the established activity is partner service.
    if re.search(r"\b(?:oral|service|teas(?:e|ing)|foreplay)\b|บริการ|เล้าโลม|ปลุกเร้า|ทางปาก", words, re.IGNORECASE):
        if not any(name in {"oral_sex", "cunnilingus", "sixty_nine_reciprocal_oral", "face_sitting_oral", "vaginal_penetration", "anal_penetration", "receptive_anal_penetration"} for name, _ in matches):
            matches.insert(0, ("oral_service", "[Act Channel: Oral Service] USER and/or CHAR is providing or receiving sexual service with the mouth, lips, tongue, or throat; keep the contact oral and do not invent vaginal or anal penetration."))
    if not matches:
        return ""
    lines = [
        "[Canonical H-Mode sex-act contract — authoritative]",
        "### Organ Pairing Protocol",
        "Resolve the established contact as actor -> target -> contact channel. `intercourse`: USER or CHAR genital "
        "organ -> the explicitly established vaginal or anal canal; `oral`: USER or CHAR mouth/lips/tongue -> the "
        "explicitly established genital target; `manual`: hand/fingers -> the explicitly established body target; "
        "`breast_play` or `foot_play`: breast or foot contact -> the established genital target; `kissing`: mouth/lips "
        "-> face/lips only. Keep the pairing stable for the turn. Never substitute mouth for genital contact, genital "
        "penetration for oral service, or one partner's body for the other partner's body without an explicit act change.",
        "Act-channel rule: if USER and/or CHAR are currently having genital intercourse or penetration, use "
        "`intercourse` as the active sex-act meaning. If USER and/or CHAR are currently providing or receiving "
        "sexual service, teasing, or foreplay with the mouth, lips, tongue, or throat, use `oral` as the active "
        "sex-act meaning. Do not switch between `intercourse` and `oral` because of a generic word such as `sex`, "
        "`service`, or `foreplay`; use the confirmed body contact and current act. Do not describe oral contact "
        "during established genital intercourse unless the scene explicitly changes to oral service, and do not "
        "describe penetration during established oral service unless penetration is explicitly established.",
    ]
    for name, meaning in matches[:2]:
        lines.append(f"Act: {name}. Meaning: {meaning}")
    lines.append("For Thai input, preserve Thai-native grammar: `เอา` is context-dependent and does not by itself prove penetration; `ถูกเอา` marks CHAR as receptive. Use the canonical act meaning and active/receptive agency consistently in the reply. A position tag never creates an act by itself. Do not replace one act with another, invert the actor, invent USER action, or skip the current stage.")
    return "\n".join(lines) + "\n"


def h_mode_need_prompt(value: Any, arousal: Any = None) -> str:
    """Describe CHAR's current drive as response guidance, never UI narration."""
    state = normalize(value)
    if not state["active"]:
        return ""
    meta = arousal if isinstance(arousal, dict) else {}
    try:
        amount = max(0, min(100, int(float(meta.get("final", 0) or 0))))
    except (TypeError, ValueError):
        amount = 0
    energy = int(state.get("h_energy", 3) or 0)
    if energy <= 0:
        need = "CHAR is exhausted: show depleted, involuntary, low-agency physical response only; do not portray fresh drive or voluntary escalation."
    elif amount >= 75:
        need = "CHAR has strong active sexual drive: let the reply visibly carry urgent want, initiative, or a clear request, but only within the current canonical stage and confirmed act."
    elif amount >= 45:
        need = "CHAR has present and growing sexual drive: let the reply show engaged desire, receptive participation, or a natural in-character initiative within the current stage."
    elif amount >= 25:
        need = "CHAR has emerging sexual drive: show interest and bodily responsiveness without falsely portraying desperation, completion, or a later-stage act."
    else:
        need = "CHAR's sexual drive is currently low: keep the response grounded in the established act and personality; do not invent urgent desire, a new escalation, or a climax."
    return (
        "[CHAR Arousal H-Mode need — authoritative]\n"
        f"Current internal drive: {amount}/100; H-Energy: {energy}/3.\n"
        f"Response requirement: {need}\n"
        "Reflect this as CHAR's choice of wording, initiative, receptivity, breath, and body language. Never expose these numbers, this label, or system terminology in visible dialogue."
    )


def thai_stage_guide() -> Dict[str, Any]:
    """Read the editable stage vocabulary from the Thai H-Mode rule itself."""
    try:
        text = (ROOT / 'Thai.md').read_text(encoding='utf-8')
        section = text.split('## Stage Transition Guide', 1)[1].split('\n## ', 1)[0]
        match = re.search(r'```json\s*([\s\S]*?)```', section)
        data = json.loads(match[1]) if match else {}
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, IndexError):
        return {}


def _config() -> Dict[str, Any]:
    try:
        config = json.loads((ROOT / "transitions.json").read_text(encoding="utf-8"))
        for stage, terms in thai_stage_guide().get('signals', {}).items():
            if isinstance(terms, list):
                config.setdefault('signals', {}).setdefault(stage, []).extend(term for term in terms if isinstance(term, str))
        return config
    except (OSError, ValueError):
        return {"stages": ["normal"], "transitions": {"normal": ["normal"]}, "signals": {}}


def normalize(value: Any, refresh_energy: bool = True) -> Dict[str, Any]:
    config, state = _config(), dict(DEFAULT)
    if isinstance(value, dict):
        state.update({key: value[key] for key in DEFAULT if key in value})
        if "scene_stage" in value and "stage" not in value:
            state["stage"] = value["scene_stage"]
        elif "stage" in value and "scene_stage" not in value:
            state["scene_stage"] = value["stage"]
    if state["stage"] not in config["stages"]:
        state["stage"] = "normal"
    state["scene_stage"] = state["stage"]
    state["active"] = state["stage"] != "normal"
    try:
        state["stage_level"] = int(state.get("stage_level", 0))
        state["turns_in_level"] = max(0, int(state.get("turns_in_level", 0)))
        # Older snapshots coupled completed orgasms and H-energy.  New state
        # keeps them independent: drive can recover or rise without rewriting
        # the scene's orgasm history.
        if isinstance(value, dict) and "h_energy" in value:
            energy = int(value["h_energy"])
        else:
            if isinstance(value, dict) and "orgasm_counter" in value:
                spent = value["orgasm_counter"]
            elif isinstance(value, dict) and "climax_peaks" in value:
                spent = value["climax_peaks"]
            else:
                spent = state.get("climax_loops", 0)
            energy = 3 - int(spent or 0)
        state["h_energy"] = max(0, min(3, energy))
        last_energy_update = float((value or {}).get("h_energy_updated_at") or (value or {}).get("updated_at") or time.time())
        elapsed = max(0.0, time.time() - last_energy_update) if refresh_energy else 0.0
        restored = int(elapsed // 1800)
        if restored:
            state["h_energy"] = min(3, state["h_energy"] + restored)
            last_energy_update += restored * 1800
        state["h_energy_updated_at"] = last_energy_update
    except (TypeError, ValueError):
        state.update(stage_level=0, turns_in_level=0, h_energy=3, h_energy_updated_at=time.time())
    if state["stage"] == "normal":
        state["stage_level"] = 0
    elif state["stage"] in H_STAGES and not 1 <= state["stage_level"] <= 3:
        state["stage_level"] = 1
    # Remove legacy orgasm_counter / climax_peaks / climax_loops; track remaining H-Energy (0 = Exhausted)
    for legacy_key in ("orgasm_counter", "climax_peaks", "climax_loops"):
        state.pop(legacy_key, None)
    state["exhausted"] = (state["h_energy"] <= 0)
    state["orgasm_exhausted"] = state["exhausted"] and state["stage"] != "normal"
    state["terminal_affection_penalty_applied"] = bool(state.get("terminal_affection_penalty_applied", False))
    interruption = state.get("interruption")
    state["interruption"] = dict(interruption) if isinstance(interruption, dict) else {}
    gear_shift = state.get("gear_shift")
    state["gear_shift"] = dict(gear_shift) if isinstance(gear_shift, dict) else {}
    quest = state.get("h_mode_quest")
    state["h_mode_quest"] = dict(quest) if isinstance(quest, dict) else {}
    if state["h_mode_quest"].get("status") not in {"offered", "active", "completed", "declined", "expired", "failed"}:
        state["h_mode_quest"] = {}
    if state["stage"] == "climax" and state["stage_level"] == 3:
        state["h_mode_quest"] = {}
    opportunity = state.get("intimacy_opportunity")
    state["intimacy_opportunity"] = dict(opportunity) if isinstance(opportunity, dict) else {}
    authority = state.get("pace_authority")
    state["pace_authority"] = dict(authority) if isinstance(authority, dict) else {}
    action_consent = state.get("character_action_consent")
    state["character_action_consent"] = dict(action_consent) if isinstance(action_consent, dict) else {}
    decision = state.get("character_h_mode_decision")
    state["character_h_mode_decision"] = dict(decision) if isinstance(decision, dict) else {}
    state["aftercare_restart_question_pending"] = bool(state.get("aftercare_restart_question_pending", False))
    return state


def is_active(value: Any) -> bool:
    return normalize(value)["active"]


def is_orgasm_exhausted(value: Any) -> bool:
    """Whether the active H-Mode scene is locked after the third orgasm."""
    state = normalize(value)
    return bool(state["active"]) and bool(state.get("orgasm_exhausted")) and state["h_energy"] == 0


def proactive_policy(value: Any) -> Dict[str, Any]:
    """Proactive messages preserve a scene; they never advance its pacing."""
    stage = normalize(value)["stage"]
    policies = {
        "normal": (True, "Use ordinary in-character conversation. Do not initiate intimacy or alter wardrobe."),
        "intimacy": (True, "CHAR may initiate one gentle stage-permitted action such as moving closer, holding, or kissing; do not advance to foreplay."),
        "foreplay": (True, "CHAR may initiate one sensual stage-permitted action within established foreplay; do not initiate penetration or climax."),
        "aftercare": (True, "CHAR may initiate recovery, closeness, cleaning, or a question about continuing; do not restart sexual contact without a clear USER answer."),
        "explicit": (True, "CHAR may proactively lead only the established explicit act; do not invent a USER action or skip the stage."),
        "climax": (True, "CHAR may proactively sustain or guide only the established peak; do not declare orgasm or skip the canonical confirmation."),
    }
    allowed, instruction = policies.get(stage, (False, "Scene holds."))
    return {"allowed": allowed, "stage": stage, "instruction": instruction}


def character_h_mode_initiation_threshold(personality: str = "", affection: int = 10) -> int:
    """Return arousal needed for an unsolicited gentle advance.

    Affection adjusts how likely an unsolicited advance is, but never acts as
    a system-level rejection gate.  The character retains the choice to
    decline in their visible, in-character response.
    """
    traits = (personality or "").casefold()
    eager = (
        "dominant", "confident", "bold", "assertive", "playful", "teasing",
        "flirty", "romantic", "affectionate", "passionate",
        "รุก", "มั่นใจ", "ขี้เล่น", "ขี้อ้อน", "เจ้าชู้", "โรแมนติก", "รัก",
    )
    cautious = (
        "reserved", "stoic", "guarded", "cautious", "shy", "timid",
        "สุขุม", "เก็บตัว", "ระวัง", "ขี้อาย", "เย็นชา",
    )
    if any(term in traits for term in eager):
        threshold = 12
    elif any(term in traits for term in cautious):
        threshold = 28
    else:
        threshold = 20
    try:
        closeness = max(0, min(100, int(affection)))
    except (TypeError, ValueError):
        closeness = 10
    if closeness < 20:
        # A low relationship makes an advance less likely, not impossible.
        # Never return an unreachable value here: doing so silently rejects
        # before CHAR can make an in-character decision.
        return threshold + 20
    if closeness < 40:
        return threshold + 12
    if closeness >= 70:
        return max(0, threshold - 4)
    return threshold


def can_character_initiate_h_mode(value: Any, personality: str = "", arousal: int = 0, affection: int = 10) -> bool:
    """Whether a proactive turn may open one gentle, character-led H scene."""
    state = normalize(value)
    if state["stage"] != "normal" or state["h_energy"] < 1:
        return False
    if (state.get("interruption") or {}).get("unresolved"):
        return False
    try:
        current_arousal = int(arousal or 0)
    except (TypeError, ValueError):
        current_arousal = 0
    return current_arousal >= character_h_mode_initiation_threshold(personality, affection)


def character_initiation_instruction(arousal: int = 0, affection: int = 10) -> str:
    """Give the proactive writer intensity matched to arousal and relationship closeness."""
    try:
        level = max(0, min(100, int(arousal or 0)))
    except (TypeError, ValueError):
        level = 0
    try:
        closeness = max(0, min(100, int(affection)))
    except (TypeError, ValueError):
        closeness = 10
    if closeness < 40:
        return ("Affection is still growing. Keep the advance reserved and respectful: a warm invitation "
                "to stay close or gentle flirting only. Do not describe touch or use sexually charged wording.")
    if level < 30:
        return ("Keep the advance very subtle: warm attention, a shy invitation to stay close, "
                "or gentle flirtation. Do not describe touch or use sexually charged wording.")
    if level < 60:
        return ("Make a clear but measured flirtatious invitation. Suggest closeness in character, "
                "but keep physical detail restrained and wait for the user's response.")
    if closeness < 70:
        return ("Make a clear, affectionate invitation. Keep the sensuality restrained because the relationship "
                "is not deeply intimate yet, and wait for the user's response.")
    return ("Let the character be openly seductive and confident in an in-character invitation, "
            "while still leaving every physical response to the user.")


def begin_character_h_mode(value: Any, personality: str = "", arousal: int = 0, affection: int = 10) -> Dict[str, Any]:
    """Open a character-led H-Mode at Intimacy 1 when proactive eligibility holds."""
    state = normalize(value)
    if not can_character_initiate_h_mode(state, personality, arousal, affection):
        return state
    now = time.time()
    return normalize({
        **state,
        "stage": "intimacy", "scene_stage": "intimacy", "active": True,
        "stage_level": 1, "turns_in_level": 0, "h_mode_quest": {},
        "pace_authority": {
            "holder": "character", "mode": "character_initiated",
            "scope": "current_h_mode_scene", "revocable": True, "granted_at": now,
        },
        "gear_shift": {
            "action": "character_initiated", "from": "normal:0", "to": "intimacy:1",
            "reason": "character made a gentle in-character advance",
        },
        "updated_at": now, "reason": "character initiated H-Mode at intimacy level 1",
    })


def is_h_mode_end_intent(text: str) -> bool:
    """Recognize an explicit end request or a clear physical disengagement."""
    stop_info = classify_stop_pause_intent(text)
    if stop_info["kind"] in {"question_stop", "pause_action", "dont_stop"}:
        return False
    if stop_info["kind"] == "hard_stop":
        return True

    channels = stop_info["channels"]
    # Only check declarative/imperative statements (never question clauses) and actions
    words = (channels["statement_clauses"] + " " + channels["action"]).strip()
    if not words:
        return False

    # Prevent physical disengagement false positives:
    # Exclude lip/kiss disengagements (e.g. ถอนริมฝีปาก, ถอนจูบ), pulling out penis temporarily to tease/cum outside, or repositioning.
    if re.search(r'ถอน(?:ริมฝีปาก|ปาก|จูบ|แก่นกาย|ลำ|ดุ้น|นิ้ว)|ผละ(?:ริมฝีปาก|ปาก|จูบ)|(?:ผละ|ถอน|ดึง).{0,24}(?:เพื่อ|ไปจูบ|ไปไซ้|ถอด|ชัก|พ่น|แตก|หลั่ง|จ่อ)', words):
        return False

    # Full-body withdrawal from the ongoing shared act itself
    disengaging = re.search(
        r'ผละ(?:ร่าง|กาย|ตัว)(?:ออกห่าง|ออกจาก)|ถอน(?:ร่าง|กาย|ตัว)\s*(?:ออกจาก|ออกห่าง)|'
        r'ดึง(?:ร่าง|กาย|ตัว)ออก(?:จาก|ห่าง)|\b(?:pull(?:ing)? away completely|withdraw from the scene|disengage|separate from)\b',
        words,
    )
    if disengaging:
        return True
    ending = re.search(r'จบ|หยุด|เลิก|พอแล้ว|ยุติ|ออกจาก|\b(?:stop|end|finish|quit|leave|no more)\b', channels["statement_clauses"])
    sexual = re.search(r'เซ็กส์|เซ็กซ์|มีเซ็กซ์|ร่วมเพศ|เพศสัมพันธ์|ร่วมรัก|เอากัน|เย็ด|สอดใส่|h[ -]?mode|'
                       r'\b(?:h|fuck|fucking|sex|intercourse|penetration)\b', channels["statement_clauses"])
    return bool(ending and sexual)


def is_user_completion(text: str) -> bool:
    """Recognize a user's completed orgasm/release, not anticipation.

    This is intentionally user-reply-only vocabulary.  Prospective phrases
    such as ``จะแตกแล้ว``/``จะเสร็จแล้ว``/``กำลังจะหลั่ง`` remain non-completions and are handled
    as climax escalation instead.
    """
    completion_pattern = (
        r'(?<!จะ)(?<!กำลังจะ)(?:สำเร็จ(?:แล้ว)?|เสร็จ(?:แล้ว)?|'
        r'แตก(?:แล้ว|ใน|นอก|เต็ม)?|หลั่ง(?:แล้ว|ใน|นอก|เต็ม)?|'
        r'ถึง(?:แล้ว|จุดสุดยอดแล้ว)|ปลดปล่อยแล้ว|น้ำ(?:กาม|รัก)?(?:พุ่ง|ทะลัก|ไหล|หลั่ง|แตก))|'
        r'\b(?:i|we|both)\s+(?:came|cum(?:med)?|orgasmed|climaxed|finished|released)\b'
    )
    negation_pattern = (
        r'\?|ไหม|หรือยัง|หรือเปล่า|อย่าเพิ่ง|ยังไม่|รอก่อน|ไม่ต้อง|ไม่อยาก|ไม่เอา|'
        r'กำลังจะ|จะ(?:เสร็จ|ถึง|แตก|พ่น|ล้น|ทะลัก|หลั่ง)|\b(?:not yet|wait|do not|don\W?t)\b'
    )
    starred_actions = " ".join(re.findall(r"\*([^*]+)\*", str(text or ""), flags=re.DOTALL)).casefold()
    if starred_actions and re.search(completion_pattern, starred_actions) and not re.search(negation_pattern, starred_actions):
        return True
    words = " ".join(re.sub(r"[*_`\"“”]", " ", str(text or "").casefold()).split())
    completed = re.search(completion_pattern, words)
    if not completed:
        return False
    return not bool(re.search(negation_pattern, words))


def is_character_orgasm_signal(text: str, value: Any = None) -> bool:
    """Return True when CHAR's own reply declares an imminent or completed orgasm.

    A character saying that they are about to finish is a canonical orgasm
    event, not merely colour for the next turn.  This detector is intentionally
    applied to assistant output only, and only inside an active H-Mode scene;
    it therefore cannot mistake an ordinary user sentence such as "งานจะเสร็จ
    แล้ว" for a sexual state change.
    """
    state = normalize(value) if value is not None else None
    if state is not None and not state.get("active"):
        return False
    words = " ".join(re.sub(r"[`*_\"“”]", " ", str(text or "").casefold()).split())
    if not words:
        return False
    # Do not count an explicit denial or a question directed at the player.
    if re.search(r"(?:ยังไม่|ไม่(?:ได้|ยอม|ถึง|เสร็จ|แตก|หลั่ง)|อย่า(?:เพิ่ง)?|ห้าม|not yet|won\W?t|cannot)", words):
        return False
    if re.search(r"(?:คุณ|เธอ|นาย|ท่าน|you)\s*(?:กำลัง)?(?:จะ|ใกล้จะ|about to|going to)?\s*(?:เสร็จ|แตก|หลั่ง|come|cum|orgasm|climax|finish)", words):
        return False
    thai_signal = re.search(
        r"(?:จะ|กำลังจะ|ใกล้จะ|จวนจะ|เกือบจะ)?\s*(?:เสร็จ(?:แล้ว)?|แตก(?:แล้ว)?|หลั่ง(?:แล้ว)?|ถึงจุดสุดยอด|ถึงแล้ว|มาแล้ว)",
        words,
    )
    english_signal = re.search(
        r"\b(?:i(?:\W+am|'m)|i\W*ll|i\W*will|i)?\s*(?:about\W+to|going\W+to|gonna|almost)?\s*"
        r"(?:come|cum|orgasm|climax|finish)(?:ing|ed)?\b",
        words,
    )
    return bool(thai_signal or english_signal)


def _requested_stage(text: str, config: Dict[str, Any]) -> tuple[str, str]:
    folded, signals = (text or "").casefold(), config.get("signals", {})
    stop_info = classify_stop_pause_intent(text)
    if stop_info["kind"] == "question_stop":
        return "", "question about stopping/pausing; preserve scene and wait for reply"
    if stop_info["kind"] == "pause_action":
        # Standalone spoken "หยุด" in intimacy/foreplay can enter aftercare if not a starred motion pause
        if folded.strip() == "หยุด" and not stop_info["channels"]["has_action"]:
            return "aftercare", "standalone pause request (หยุด = พัก)"
        return "", "physical or spoken pause; hold current stage"
    conditional_rest_offer = bool(
        re.search(r"ถ้า[^\n.!?]{0,80}(?:พัก|หยุด)[^\n.!?]{0,40}(?:ได้(?:สิ|นะ|ค่ะ|ครับ)?|ก็ได้)", folded)
        or re.search(r"if\s+[^\n.!?]{0,80}(?:need|want|can't|cannot)[^\n.!?]{0,40}(?:rest|stop)", folded)
    )
    if conditional_rest_offer:
        return "", "conditional care offer; preserve scene"
    if is_h_mode_end_intent(text):
        return "normal", "user ended the scene"
    if _is_platonic_escort_or_greeting(folded):
        return "", "platonic escort or greeting; remain in current stage"
    folded_clean = _strip_nonsexual_gestures(folded)
    for stage in ("aftercare", "climax", "explicit", "foreplay", "intimacy"):
        for term in signals.get(stage, []):
            t_cf = term.casefold()
            if t_cf in {"ถึง", "เอา", "ซอย", "สัมผัส"}:
                continue
            if t_cf in folded_clean:
                return stage, f"matched {stage} signal"
    starred_actions = " ".join(re.findall(r"\*([^*]+)\*", str(text or ""), flags=re.DOTALL))
    if starred_actions:
        action_sem = classify_scene_words(starred_actions)
        if not action_sem["refusal"] and not action_sem["defer"] and not action_sem["hard_stop"]:
            if action_sem["explicit_action"]:
                return "explicit", "starred physical explicit action"
            if action_sem["foreplay_action"]:
                return "foreplay", "starred physical foreplay action"
    return "", "no scene signal"


def detect_h_mode_response(text: str, state: Any = None) -> Dict[str, Any]:
    semantic = classify_scene_words(text)
    words = semantic["text"]
    current = normalize(state) if state is not None else {}
    current_stage = current.get("stage", "")
    current_level = int(current.get("stage_level", 0) or 0)
    direct = pacing_action_from_message(words)
    question = semantic["question"]
    deferred = semantic["defer"]
    conditional = semantic["conditional"]
    action_pattern = (
        r'(?:จูบ|กอด|สัมผัส|ดูด|เลีย|ชัก|อม|ลูบ|คลึง|บีบ|นวด|ล้วง|สอดนิ้ว|ถู|ขยี้|จับ|'
        r'ไซ้|ซุก|จูบไล้|จูบซอกคอ|ถอด(?:เสื้อ|กางเกง|ชุด)?|ปลด(?:เสื้อ|กางเกง|ชุด)?|เปลื้อง(?:ชุด)?|'
        r'สอดใส่|เอาเข้าไป|เอากัน|เอาต่อ|แทง|เสียบ|เย็ด|ร่วมรัก|มีเพศสัมพันธ์|กระแทก|กระเด้า|เด้ง|โยก|ขยับ|ดัน|รัว|เร้า|'
        r'ขย่ม|ร่อน|คร่อม|บด|ซอย(?:เอว|สะโพก|ถี่|รัว|ต่อ)|สาวเอว|เร่งเอว|กระหน่ำ|กระดก|ถี่ยิบ|ใกล้ถึง|ใกล้แล้ว|เกือบแล้ว|จะถึง|จะเสร็จแล้ว|จะแตกแล้ว|'
        r'kiss|hug|touch|lick|suck|stroke|rub|caress|thrust|bounce|grind|ride|straddle|'
        r'undress|strip|penetrat(?:e|ing)|fuck(?:ing)?)'
    )
    continued_action = bool(re.search(
        action_pattern + r'.{0,24}(?:ต่อ|อีก|เพิ่ม|more|again|further)|'
        r'(?:ต่อ|อีก|เพิ่ม|more|again|further).{0,24}' + action_pattern,
        words,
    ))
    named_action = bool(re.search(action_pattern, words))
    continuation_request = semantic["continue"]
    aftercare_progress = current_stage == "aftercare" and semantic["care"]
    # Before Climax 3, a plain affirmative is a valid consent to continue the
    # current peak.  It advances exactly one substage; it is never treated as
    # an orgasm confirmation, which remains exclusive to Climax 3.
    climax_substage_affirmative = (
        current_stage == "climax" and current_level in {1, 2}
        and not question and not deferred and not conditional
        and semantic["affirmative"]
    )
    advance = (direct == "advance" or continued_action or named_action or continuation_request
               or aftercare_progress or climax_substage_affirmative)
    escalating_request = bool(re.search(
        r'(?:รัก|อยาก|ต้องการ|ขอ|ทำให้)[^\n.!?]{0,30}(?:มากกว่า|เพิ่มขึ้น|แรงขึ้น|ลึกขึ้น|อีกหน่อย|อีกนิด)|'
        r'\b(?:want|need|love|make).{0,30}(?:more|deeper|harder|faster)\b', words,
    ))
    climax_escalation = (
        current_stage == "climax" and current_level < 3 and bool(re.search(
            r'เสียว(?:มาก|จัง|ขึ้น|สุด[ๆๆ])?|ฟิน(?:มาก|จัง)?|สุด(?:ยอด|ๆๆ)?|'
            r'รู้สึกดี(?:มาก|จัง)?|ร้อน(?:วูบวาบ|ไปทั้งตัว)?|ใจสั่น|'
            r'แทบไม่ไหว|ทนไม่ไหว|ไม่ไหวแล้ว|ใกล้(?:แล้ว|ถึง|สุด)?|เกือบ(?:แล้ว|ถึง)?|'
            r'กำลังจะ(?:ถึง|เสร็จ|แตก|มา)|จะ(?:ถึง|เสร็จ|แตก|พีค)|เหมือนจะ(?:ถึง|เสร็จ|แตก)|'
            r'เร่ง(?:อีก|ต่อ|ขึ้น)?|เร็ว(?:ขึ้น|กว่านี้)?|แรง(?:ขึ้น|กว่านี้)?|ถี่(?:ขึ้น|ยิบ)?|'
            r'รัว(?:ขึ้น)?|กระหน่ำ(?:ต่อ)?|ซอย(?:ต่อ)?|เด้ง(?:ต่อ)?|โยก(?:ต่อ)?|ขย่ม(?:ต่อ)?|'
            r'เอาอีก|อย่าหยุด|ต่อเลย|ไปต่อ|อีกนิด|อีกหน่อย|มากกว่านี้|'
            r'ชั้นด้วย|ฉันด้วย|ผมด้วย|เราด้วย|เหมือนกัน(?:เลย)?|เหมือนเธอ|'
            r'\b(?:feel so good|so close|almost there|can\W?t hold|about to (?:come|cum|finish)|'
            r'faster|harder|deeper|keep going|don\W?t stop|more|me too|same way|same here)\b', words,
        ))
    )
    stop_info = classify_stop_pause_intent(text)
    stop_kind = stop_info["kind"]
    advance = advance or escalating_request or climax_escalation
    if stop_kind in {"pause_action", "question_stop", "hard_stop"}:
        advance = False
    ending = (stop_kind == "hard_stop") or bool(
        re.search(r'เลิกทำ|ไม่อยากแล้ว|ทำต่อไม่ไหว|ไม่สามารถทำต่อ|จบฉาก|\b(?:stop|no more|cannot continue|end scene)\b', stop_info["channels"]["statement_clauses"])
    )
    starred_actions = stop_info["channels"]["action"]
    starred_sem = classify_scene_words(starred_actions) if starred_actions else {}
    has_starred_physical_act = bool(
        starred_actions
        and stop_kind != "pause_action"
        and (starred_sem.get("explicit_action") or starred_sem.get("foreplay_action") or starred_sem.get("sexual_motion"))
        and not starred_sem.get("refusal") and not starred_sem.get("defer") and not starred_sem.get("hard_stop")
    )
    completion = is_user_completion(text) and not deferred and not conditional
    entry = _normal_entry_stage(words) if _has_normal_entry_signal(words) else ""
    action = "advance" if advance else "hold"
    if stop_kind in {"pause_action", "question_stop"}:
        action = "hold"
    elif question or deferred or conditional:
        if (not direct and not escalating_request and not continuation_request
                and not aftercare_progress and not climax_escalation
                and not (has_starred_physical_act and not deferred and not conditional)):
            action = "hold"
    return {
        "text": words, "action": action, "direct": bool(direct), "groups": semantic,
        "question": question, "deferred": deferred, "conditional": conditional,
        "ending": ending, "orgasm_confirmed": completion, "entry_stage": entry,
        "stop_kind": stop_kind, "stop_reason": stop_info["reason"],
    }


def climax_confirmation_question(language: str = "thai") -> str:
    prompts = {
        "thai": "จะ...เสร็จแล้วหรือยัง?",
        "japanese": "もう…達しそう？",
        "chinese": "要…到了吗？",
        "french": "Tu vas… finir ?",
        "spanish": "¿Ya vas a terminar?",
    }
    return prompts.get(str(language or "").casefold(), "Are you about to finish?")


def has_climax_confirmation_question(text: str) -> bool:
    words = str(text or "").casefold()
    return bool(re.search(
        r'(?:เสร็จ|แตก|ถึง(?:จุดสุดยอด)?|หลั่ง)[^\n.!?]{0,24}(?:ไหม|หรือยัง|รึยัง|หรือเปล่า)|'
        r'\b(?:about to (?:finish|come|cum|climax)|going to (?:finish|come|cum|climax)|finish(?:ing)?\s*\?|come\s*\?|cum\s*\?|climax\s*\?)|'
        r'達しそう|到了吗|terminar\s*\?|finir\s*\?',
        words,
    ))


def enforce_climax_confirmation_dialogue(reply: str, value: Any, language: str = "thai") -> str:
    """Ensure the visible Climax III turn asks one natural completion question."""
    state = normalize(value)
    text = str(reply or "").strip()
    if not (state["active"] and state["stage"] == "climax" and state["stage_level"] == 3):
        return text
    if has_climax_confirmation_question(text):
        return text
    question = f'"{climax_confirmation_question(language)}"'
    # Keep machine-only state blocks at the end intact.  The question belongs
    # to visible dialogue, immediately before the first block if present.
    block = re.search(r"\n?```", text)
    if block:
        visible = text[:block.start()].rstrip()
        hidden = text[block.start():]
        return f"{visible} {question}\n{hidden}".strip() if visible else f"{question}\n{hidden}".strip()
    return f"{text} {question}".strip()


def _stage_down_phrase(words: str) -> bool:
    return bool(re.search(
        r'(?:gear|stage|level|intensity)\s*(?:down|lower)|(?:ลด|ลง)\s*(?:เกียร์|สเตจ|stage|ระดับ|level|ความเข้ม|intensity)',
        words,
    ))


def _sublevel_intent(text: str, state: Any = None) -> str | None:
    action = detect_h_mode_response(text, state).get("action")
    return action if action in {"advance", "ease"} else None


def _stage_down_intent(text: str) -> bool:
    return bool(detect_h_mode_response(text).get("action") == "stage_down")


def _normal_entry_stage(text: str) -> str:
    words = (text or "").casefold()
    sem = classify_scene_words(text)
    if re.search(r'สอดใส่|เอาเข้าไป|แทงเข้า|ขึ้นขย่ม|ขย่มให้|กระแทก|ร่วมรัก|มีเพศสัมพันธ์|มีเซ็กซ์|\b(?:penetration|intercourse|ride\s+me|cowgirl)\b', words):
        return "explicit"
    if sem["foreplay_action"] or sem["partner_service"] or sem["partner_directed_solo"]:
        return "foreplay"
    if re.search(r'(?:ดูด|เลีย|ชัก|อม).{0,12}(?:นม|หัวนม|ยอดอก|เต้า|ควย|ดุ้น|ลำ|หี|จิ๋ม|เม็ด|ร่อง|ปาก|ลิ้น|ให้)|\b(?:oral|blowjob|handjob|lick|suck)\b', words):
        return "foreplay"
    return "intimacy"


def _is_platonic_escort_or_greeting(words: str) -> bool:
    """Return True when hand-holding or light touch is purely platonic walking/escorting/greeting."""
    if re.search(r"จูบ|ดูด|เลีย|ไซ้|ซุก|ลูบไล้|คลึง|บีบ|ขยำ|หน้าอก|นม|ก้น|สะโพก|ต้นขา|ถอด|ปลด|เปลื้อง|สอดใส่|เย็ด|ร่วมรัก|\b(?:kiss|caress|fondle|undress|strip|sex|fuck|lick|suck)\b", words):
        return False
    if re.search(r"จับมือ.{0,30}(?:พาไป|ไปส่ง|เดิน|จูง|ลุกขึ้น)|(?:พาไป|ไปส่ง|เดิน).{0,30}จับมือ|แตะ(?:ที่)?(?:แขน|ไหล่|บ่า|มือ|คาง)", words):
        return True
    return False


def _has_normal_entry_signal(text: str) -> bool:
    raw = str(text or "").strip()
    words = raw.casefold()
    if not words or _is_platonic_escort_or_greeting(words):
        return False
    channels = split_roleplay_channels(raw)
    # In Normal Mode, pure spoken questions or non-sexual conversation containing incidental words
    # (like "สัมผัสถึง...", "เอาเพลง...", "ผ่านซอย...") must NOT trigger H-Mode entry.
    if channels["is_question_speech"] and not channels["has_action"]:
        return False
    cleaned_words = _strip_nonsexual_gestures(words)
    semantic = classify_scene_words(cleaned_words)
    if semantic["explicit_action"] or semantic["foreplay_action"] or semantic["partner_service"] or semantic["partner_directed_solo"]:
        return True
    if position_semantic_contract(cleaned_words):
        return True
    if semantic["intimacy_action"]:
        if channels["has_action"]:
            return not _is_platonic_escort_or_greeting(channels["action"])
        return bool(re.search(r"จูบ|กอด|หอมแก้ม|ซุก|ไซ้|บอกรัก|คลอเคลีย|\b(?:kiss|hug|cuddle|embrace|make out)\b", cleaned_words))
    return bool(re.search(
        r'จูบ|กอด|(?:ดูด|เลีย|ชัก|อม).{0,12}(?:นม|หัวนม|ยอดอก|เต้า|ควย|ดุ้น|ลำ|หี|จิ๋ม|เม็ด|ร่อง|ปาก|ลิ้น|ให้)|สอดใส่|แทงเข้า|\b(?:kiss|hug|oral|blowjob|handjob|lick|suck|penetration|intercourse|sex)\b',
        cleaned_words,
    ))


def _quest_answer_matches(text: str, target_stage: str, config: Dict[str, Any], quest: Optional[Dict[str, Any]] = None) -> bool:
    detected = detect_h_mode_response(text)
    words = detected["text"]
    short_acceptance = bool(re.fullmatch(AFFIRMATIVE_FULLMATCH_PATTERN, words.strip(), re.IGNORECASE))
    if short_acceptance and not detected["question"]:
        return True
    # When the character has made an explicit pacing demand, only a response
    # in the same direction resolves it.
    quest_demand = str((quest or {}).get("demand") or "")
    if quest_demand:
        if quest_demand == "slower":
            return bool(re.search(SLOWER_UNION_PATTERN, words)) and not detected["question"]
        if quest_demand == "continue_faster":
            return bool(re.search(FASTER_UNION_PATTERN, words)) and not detected["question"]
    # A quest answer is an intent answer, not a keyword/password.  Accept any
    # clear continuation that satisfies the character's desire, but never let
    # a question, refusal, or deferred answer resolve the boundary quest.
    affirmative_not_enough = bool(re.search(r"ยังไม่พอ|ยังไม่อิ่ม|ยังอยากต่อ|ยังต้องการต่อ|อยากทำ|อยากอีก|อยากต่อ", words))
    demand_response = bool(re.search(
        SLOWER_UNION_PATTERN + r"|" + FASTER_UNION_PATTERN + r"|" +
        r"ทำต่อ|ต่อสิ|ต่อเลย|อย่าหยุด|ไม่ไหวแล้ว|"
        r"จูบหน่อย|กอดหน่อย|ลูบหน่อย|คลึงหน่อย|จับหน่อย|ซุกหน่อย|ไซ้หน่อย|ไล้หน่อย",
        words,
    ))
    refusal_or_defer = bool(re.search(
        r"^ไม่$|" + REFUSAL_UNION_PATTERN + r"|" + DEFER_UNION_PATTERN + r"|ยังไม่(?:พอ|อิ่ม|ไหว)",
        words,
    )) and not affirmative_not_enough
    if detected["question"] or refusal_or_defer:
        return False
    # Short acknowledgements are valid consent/acceptance responses to the
    # character's demand, including when the user does not repeat the action.
    if short_acceptance:
        return True
    if detected["action"] == "advance" or affirmative_not_enough or demand_response:
        return True
    terms = config.get("signals", {}).get(target_stage, [])
    return any(str(term).casefold() in words for term in terms)


def capture_character_demand(value: Any, character_text: str) -> Dict[str, Any]:
    """Persist the latest explicit pacing demand on an active H-Quest or aftercare restart question."""
    state = normalize(value)
    if state["stage"] == "aftercare" and character_asks_aftercare_restart(character_text):
        state = normalize({**state, "aftercare_restart_question_pending": True, "updated_at": time.time()})
    quest = state.get("h_mode_quest") or {}
    if quest.get("status") != "active":
        return state
    words = " ".join(re.sub(r"[*_`\"“”]", " ", str(character_text or "").casefold()).split())
    demand_patterns = {
        "slower": r"ช้าหน่อย|ช้าลง|เบาหน่อย|เบาลง|ค่อย(?:ๆ| ๆ)?|ผ่อนแรง|ลดจังหวะ|\b(?:slow down|slower|softer|ease up|gentler)\b",
        "continue_faster": r"เร็วขึ้น|เร็วหน่อย|เร็วอีก|แรงขึ้น|แรงอีก|ถี่ขึ้น|ทำต่อ|อย่าหยุด|ไม่ไหวแล้ว|ยังไม่พอ|\b(?:faster|harder|keep going|don't stop)\b",
    }
    # A single active demand per quest. If the reply contains several cues,
    # use the cue occurring latest in the character's visible message.
    matches = []
    for name, pattern in demand_patterns.items():
        match = list(re.finditer(pattern, words))
        if match:
            matches.append((match[-1].start(), name))
    demand = max(matches)[1] if matches else ""
    if not demand:
        return state
    return normalize({**state, "h_mode_quest": {**quest, "demand": demand}, "updated_at": time.time()})


def _restart_stage_level(value: Any, reason: str, *, quest_failed: bool = False) -> Dict[str, Any]:
    state = normalize(value)
    quest = state.get("h_mode_quest") or {}
    replacement_quest = resolve_boundary_quest(state, "failed").get("h_mode_quest", {}) if quest_failed else quest
    return normalize({
        **state, "stage_level": 1, "turns_in_level": 0,
        "h_mode_quest": replacement_quest,
        "gear_shift": {"action": "reset_level", "from": f"{state['stage']}:{state['stage_level']}",
                       "to": f"{state['stage']}:1", "reason": reason},
        "reason": reason, "updated_at": time.time(),
    })


def analyze_transition_message(value: Any, text: str) -> Dict[str, str] | None:
    """Interpret user intent at recovery boundaries; character prose is not authority."""
    state = normalize(value)
    if state['stage'] != 'aftercare' and not (state['stage'] == 'climax' and state['stage_level'] == 3):
        return None
    words = (text or '').casefold().strip()
    guide = thai_stage_guide()
    has_guide_term = lambda key: any(term in words for term in guide.get(key, []) if isinstance(term, str))
    def result(action: str, reason: str) -> Dict[str, str]:
        return {'action': action, 'reason': reason}

    # Exact console commands retain their declared priority.
    command = pacing_action_from_message(words)
    if command:
        if state['stage'] == 'aftercare' and command == 'advance':
            return result('explicit', 'user requested explicit continuation from aftercare')
        return result(command, 'explicit user pacing command')

    # ตรวจสอบ Intent จบฉาก/หยุดเซ็กซ์ หรือ Hard stop โดยตรงใน Aftercare
    if is_h_mode_end_intent(words):
        return result('normal', 'user ended the scene from aftercare')

    stop_info = classify_stop_pause_intent(text)
    if stop_info["kind"] == "hard_stop":
        return result('hard_stop', 'user stopped the scene')
    if stop_info["kind"] == "pause_action":
        return result('hold', stop_info["reason"] or 'user paused physical motion; preserve scene')
    if stop_info["kind"] == "question_stop" and not is_user_completion(text):
        return result('hold', 'user asked stop/pause question; hold for character response')

    if (re.search(r"ถ้า[^\n.!?]{0,80}(?:พัก|หยุด)[^\n.!?]{0,40}(?:ได้(?:นะ|ค่ะ|ครับ)?|ก็ได้)", words)
            or re.search(r"if\s+[^\n.!?]{0,80}(?:need|want|can't|cannot)[^\n.!?]{0,40}(?:rest|stop)", words)):
        return result('hold', 'conditional care offer; preserve scene')

    if state['stage'] == 'aftercare':
        semantic = classify_scene_words(words)
        # A starred action is already happening, not a conversational request.
        # Route it through the shared semantic catalogue (rather than the
        # smaller legacy aftercare regex below), so `*เย็ดต่อ*`, `*ทำต่อ*`,
        # and `*keep fucking*` consistently restart at Explicit I.
        action_text = split_roleplay_channels(text).get("action", "")
        action_semantic = classify_scene_words(action_text) if action_text else {}
        if (
            action_text
            and not action_semantic.get("refusal")
            and not action_semantic.get("defer")
            and not action_semantic.get("hard_stop")
            and (
                action_semantic.get("explicit_action")
                or (action_semantic.get("continue") and not action_semantic.get("care")
                    and not action_semantic.get("intimacy_action")
                    and not action_semantic.get("foreplay_action"))
            )
        ):
            return result('explicit', 'starred continuation/explicit action restarted at Explicit I')
        # In aftercare, a bare continuation cue requests a new explicit round.
        # Care/intimacy actions remain recovery and must not be promoted.
        if (semantic['continue'] and not semantic['care'] and not semantic['intimacy_action']
                and not semantic['foreplay_action'] and not semantic['explicit_action']
                and not re.search(r'\?|ไหม|มั้ย|หรือเปล่า|\b(?:can|would|should)\b', words)):
            return result('explicit', 'user requested explicit continuation from aftercare')

    if state['stage'] == 'climax':
        if re.search(r'เลิกทำ|ไม่อยากแล้ว|ทำต่อไม่ไหว|ไม่สามารถทำต่อ|\b(?:stop|no more|cannot continue)\b', words) and not re.search(QUESTION_UNION_PATTERN, words):
            return result('normal', 'user ended the scene during climax')
        if re.search(r'อย่าเพิ่ง|ยังไม่|รอก่อน|\b(?:not yet|wait|do not)\b', words):
            return result('climax_retry', 'climax completion was deferred')
        completion = (
            is_user_completion(text)
            or bool(re.search(
                r'เสร็จพร้อมกัน(?:เถอะ|เลย)|(?:มา|ให้เรา|เรามา)เสร็จพร้อมกัน|'
                r'\b(?:let\W?s|let us)\s+(?:finish|come|climax)\s+together\b|'
                r'\b(?:we|i|both)\s+(?:have\s+)?finished\b|'
                r'\b(?:orgasm|climax|release)\b', words,
            ))
            or has_guide_term('completion')
        )
        if completion:
            if re.search(r'เลิกทำ|ไม่อยากแล้ว|ทำต่อไม่ไหว|ไม่สามารถทำต่อ|กลับบ้าน|แต่งตัว|ไปกินข้าว|\b(?:go home|get dressed|leave|stop|no more|cannot continue)\b', words):
                return result('orgasm_normal', 'user confirmed orgasm then ended the scene')
            if re.search(r'อ่อนโยน|ดูแล|พัก|กอด|ปลอบ|เช็ด|aftercare|\b(?:gentle|care|cuddle|rest|clean)\b', words):
                return result('orgasm_aftercare', 'user confirmed orgasm and requested care')
            if re.search(
                r'หื่น|กระหาย|ต้องการ|ทำต่อ|ต่อไป|ต่อไหม|ต่อมั้ย|อีกรอบ|ยัง(?:ยัง)?ไหว|ยังไหวอยู่|ไปต่อได้|ไม่ต้องพัก|'
                r'ไม่หยุด|โดยไม่หยุด|กระแทก|กระเด้า|ซอย|กระหน่ำ|เอา|เย็ด|สอดใส่|เข้า|ขยับ|เร่ง|แรงขึ้น|ถี่ขึ้น|'
                r'\b(?:continue|again|another round|want|desire|can keep going|still can)\b', words,
            ) and not re.search(r'\?|ไหม|มั้ย|หรือยัง|หรือเปล่า', words):
                return result('orgasm_explicit', 'user confirmed orgasm and continued the scene')
            return result('orgasm_aftercare', 'user confirmed orgasm and recovery')
        # If user asks a question back (e.g. ".....?", "เสร็จไหม?", "เสร็จหรือยัง?", "พอแล้ว?"), hold to see character reply/action
        if re.search(r'\?|ไหม|มั้ย|หรือยัง|หรือเปล่า', words):
            return result('hold', 'user asked climax confirmation question; hold for character response')
        # If user continues intense physical climax action (e.g. *กระแทกให้แรงขึ้นอีก*), hold at climax 3 peak rather than resetting to 1
        sem_climax = classify_scene_words(text)
        if sem_climax.get("explicit_action") or sem_climax.get("sexual_motion") or sem_climax.get("rapid_cadence") or sem_climax.get("continue"):
            return result('hold', 'continued climax peak intensity; holding at climax 3')
        return result('climax_retry', 'climax completion was not confirmed')

    # Questions, conditional offers, negations, and retrospective descriptions
    if re.search(r'\?|ไหม|หรือเปล่า|หรือยัง|หรือไม่|\b(?:shall we|would you|do you|can we|should we)\b', words):
        return result('hold', 'question is not a confirmed transition')
    if re.search(r'อย่าเพิ่ง|ยังไม่|รอก่อน|ไม่ต้อง|ไม่อยาก|ไม่เอา|\b(?:not yet|wait|don\W?t|do not)\b', words):
        return result('hold', 'user deferred or declined a transition')
    if re.search(r'ถ้า|\bif\b', words):
        return result('hold', 'conditional offer; preserve scene')
    if re.search(r'กลับไปคุย|คุยเรื่องอื่น|เปลี่ยนเรื่อง|ไปกินข้าว|ไปทำงาน|กลับบ้าน|ออกจากห้อง|แต่งตัว|'
                 r'\b(?:back to normal|change the subject|go home|go to work|leave the room|get dressed)\b', words):
        return result('normal', 'user returned to ordinary activity')
    if re.search(r'เมื่อกี้|เมื่อก่อน|ที่ผ่านมา|\b(?:earlier|previously|had sex|finished)\b', words):
        return result('hold', 'reference to the previous scene is not a restart')
    if re.search(r'จุดสุดยอด|เสร็จ|\b(?:climax|orgasm|release)\b', words):
        return result('hold', 'aftercare cannot restart directly at climax')
    action_words = re.sub(r'(?:เลีย|ล้าง|เช็ด)?ทำความสะอาด[^*\n.!?,]*', '', words)
    explicit_action = bool(re.search(
        r'สอดใส่|เอาเข้าไป|เอาเข้า-เอาออก|เอากัน|ยัด(?:เข้า|ใส่)?|กระแทก|กระเด้า|เด้า|ฟัดเด้า|ฟัด(?:กัน|ต่อ)?|จัด(?:หนัก|ต่อ)?|ซอย(?:เอว|สะโพก|ถี่|รัว|ยิก|ยับ|ต่อ)|ดันเข้า|ร่วมรัก|มีเพศสัมพันธ์|'
        r'\b(?:intercourse|penetration|sex|fuck(?:ing)?)\b',
        action_words))
    explicit_action = explicit_action or any(term in action_words for term in guide.get('signals', {}).get('explicit', []))
    # A new explicit act always wins over recovery vocabulary in the same
    # message (for example, "กอดไว้แล้วกระแทกต่อ").
    if explicit_action:
        return result('explicit', 'user explicitly initiated a fresh round')
    # Aftercare is the intimate, post-climax version of the scene. Gentle
    # closeness (including kissing) remains aftercare; only a new foreplay or
    # explicit action starts another stage.
    semantic = classify_scene_words(words)
    if has_guide_term('recovery') or re.search(
        r'(?:เลีย|ล้าง|เช็ด)?ทำความสะอาด|เช็ดตัว|\b(?:clean up|cleaning)\b', words,
    ):
        return result('hold', 'continue recovery; rules/H-mode/Thai.md guide')
    if semantic["foreplay_action"]:
        return result('foreplay', 'user initiated a fresh foreplay action')
    if semantic["care"] or semantic["intimacy_action"]:
        return result('advance', 'user continued aftercare intimacy')
    return result('hold', 'no confirmed exit or restart; preserve aftercare')


def aftercare_restart_offer(text: str) -> str | None:
    """Return a requested restart stage for a clear aftercare proposal.

    This recognizes a USER asking whether to resume, not an ordinary comfort
    question.  CHAR's visible acceptance is still required before the server
    commits the transition.
    """
    semantic = classify_scene_words(text)
    words = semantic["text"]
    if not words or semantic["defer"] or semantic["refusal"]:
        return None
    # A concrete action outranks generic continuation words, so an explicit
    # restart cannot be misread as a softer stage merely because it says "again".
    if semantic["explicit_action"]:
        return "explicit"
    if semantic["foreplay_action"]:
        return "foreplay"
    # A USER question in aftercare (or question about continuing/next step) is a restart proposal
    # whose result is decided by CHAR's next visible answer; the question itself does not change stage immediately.
    if semantic["question"]:
        return "question_hold"
    # Gentle or generic continuation stays in aftercare. It is not a restart
    # proposal and therefore does not need a second acceptance check.
    return None


def character_accepts_aftercare_restart(reply: str) -> bool:
    """Detect an unambiguous visible acceptance of a USER restart proposal."""
    visible = re.sub(r"```[\s\S]*?```", "", str(reply or ""))
    semantic = classify_scene_words(visible)
    words = semantic["text"]
    if semantic["refusal"] or semantic["defer"] or re.search(r"ไม่ไหว|พักก่อน|หยุด|\b(?:can't)\b", words):
        return False
    return semantic["affirmative"] or bool(re.search(
        r"(?:อยาก|พร้อม|ยินดี|ขอ|เอา|ได้).{0,24}(?:อีก|ต่อ|คุณ)|"
        r"(?:ใช่แล้ว|ได้สิ|ได้เลย|เอาสิ|เอาเลย|พร้อมแล้ว|แน่ใจ|มั่นใจ|แน่ใจแล้ว|มั่นใจแล้ว)|"
        r"\b(?:yes|ready|want (?:you|more|it)|let's|again|continue)\b",
        words,
    ))


def character_asks_aftercare_restart(reply: str) -> bool:
    """Whether CHAR asked the USER whether to resume from aftercare."""
    words = _scene_words(reply)
    if not words or not re.search(r"\?|ไหม|มั้ย|หรือเปล่า|\b(?:should|shall|would|can)\b", words):
        return False
    return bool(re.search(
        r"ต่อ|ทำต่อ|เอาอีก|อีกรอบ|เริ่มใหม่|ร่วมรัก|สอดใส่|\b(?:continue|again|another round|resume|sex)\b",
        words,
    ))


def advance(previous: Any, text: str, nsfw_mode: str, count_climax_turn: bool = False) -> Dict[str, Any]:
    """Apply only configured stage changes from a user message; never skip a level."""
    state = normalize(previous)
    if state.get("gear_shift"):
        state = {**state, "gear_shift": {}}
    # Delegated character-led pacing is itself the authorization for the next
    # beat.  Do not leave a previously created player-confirmation quest in
    # place, otherwise an affirmative like "พร้อมแล้ว" can be consumed by a
    # stale gate while CHAR merely promises to act.
    if (state.get("pace_authority") or {}).get("holder") == "character" and state.get("h_mode_quest", {}).get("status") == "active":
        state = normalize({**state, "h_mode_quest": {}})
    if nsfw_mode not in {"local", "h_mode", "h-mode", "h"}:
        return {**state, "stage": "normal", "scene_stage": "normal", "active": False, "stage_level": 0,
                "turns_in_level": 0, "climax_peaks": 0, "climax_loops": 0, "orgasm_counter": 0, "orgasm_exhausted": False,
                "updated_at": time.time(), "reason": "mode disabled"}
    stop_info = classify_stop_pause_intent(text)
    stop_kind = stop_info["kind"]
    standalone_stop = str(text or "").strip().casefold()
    is_question = bool(re.search(QUESTION_UNION_PATTERN, standalone_stop)) or (stop_kind == "question_stop")
    stop_with_ellipsis = bool(re.fullmatch(r"พอแล้ว(?:[.。…!！\s]*)", standalone_stop))
    # Only a declarative/imperative stop (not a *หยุด* action and not a ? question) triggers hard_stop
    if state["active"] and stop_kind == "hard_stop":
        return hard_stop(state)
    if (state["active"] and not is_question and stop_kind != "pause_action"
            and not stop_info["channels"]["is_pure_action"]
            and (standalone_stop in {"หยุดแล้ว", "พอแล้ว", "ไม่เอาแล้ว"} or stop_with_ellipsis or bool(re.fullmatch(REFUSAL_UNION_PATTERN, standalone_stop)))):
        return hard_stop(state)
    # Physical pause in `*...*` (e.g. `*หยุด*`, `*หยุดขยับ*`) or spoken standalone pause (`"หยุด"`, `"พัก"`)
    if state["active"] and stop_kind == "pause_action":
        if state["stage"] in {"intimacy", "foreplay"} and standalone_stop == "หยุด" and not stop_info["channels"]["has_action"]:
            pass  # Let _requested_stage transition standalone spoken "หยุด" to aftercare if configured
        else:
            return normalize({
                **state,
                "gear_shift": {"action": "hold", "from": f"{state['stage']}:{state['stage_level']}", "to": f"{state['stage']}:{state['stage_level']}", "reason": stop_info["reason"] or "pause action holds current stage"},
                "reason": stop_info["reason"] or "standalone pause request holds explicit/climax pacing",
            })
    # Question asking whether to stop/pause (e.g. `"จะหยุดไหม?"`, `"พอแล้ว?"`, `"พักก่อนไหม?"`)
    # Holds current stage unless accompanied by a starred completion or starred escalation
    config = _config()
    response = detect_h_mode_response(text, state)
    if state["active"] and stop_kind == "question_stop" and not response.get("orgasm_confirmed"):
        return normalize({
            **state,
            "gear_shift": {"action": "hold", "from": f"{state['stage']}:{state['stage_level']}", "to": f"{state['stage']}:{state['stage_level']}", "reason": "user asked stop/pause question; hold for character reply"},
            "reason": "question is not a confirmed transition",
        })

    # Thai tempo wording is ordinary dialogue to CHAR, not a pacing command.
    # Hold while CHAR answers it; do not let Explicit's per-turn auto-pacing
    # reinterpret a request such as "ช้าลง" as a canonical stage movement.
    input_channels = split_roleplay_channels(text)
    tempo_dialogue = (
        not input_channels["has_action"]
        and bool(re.search(r"ช้าลง|เบาลง|ผ่อนลง", input_channels["speech"]))
    )
    if tempo_dialogue:
        return normalize({
            **state,
            "gear_shift": {"action": "hold", "from": f"{state['stage']}:{state['stage_level']}",
                           "to": f"{state['stage']}:{state['stage_level']}",
                           "reason": "tempo wording is a dialogue request"},
            "reason": "tempo wording is a dialogue request; keep the current canonical stage",
        })

    # Exhausted H-energy (0/3) activates the Exhausted after multi-orgasms condition.
    # It does NOT auto-force the scene into aftercare; USER retains full pacing authority
    # to continue in explicit/foreplay/climax or end the scene.
    if is_orgasm_exhausted(state):
        if is_h_mode_end_intent(text) and not response["conditional"]:
            return pace(state, "hard_stop")

    # Progressive Stage Unlock Principle:
    # Reaching higher stages (Foreplay, Explicit, Climax) acts as unlocking a broader repertoire of actions.
    # Performing earlier-stage actions (such as intimacy touch, hugs, kisses, or gentle foreplay caresses)
    # while in Foreplay, Explicit, or Climax enriches the existing scene and DOES NOT downshift or downgrade the stage.
    semantic = classify_scene_words(text)
    has_higher_than_intimacy = any((
        semantic["foreplay_action"], semantic["explicit_action"], semantic["sexual_motion"],
        semantic["continue"], semantic["rapid_cadence"], response.get("orgasm_confirmed"),
    ))
    has_higher_than_foreplay = any((
        semantic["explicit_action"], semantic["sexual_motion"], semantic["continue"],
        semantic["rapid_cadence"], response.get("orgasm_confirmed"),
    ))
    stage_label = f"{state['stage']}:{state['stage_level']}"
    # A lower-tier act is valid inside an already-unlocked higher stage, but
    # it never rewrites that stage or consumes a pacing beat.  This keeps a
    # hug/kiss during Explicit or a foreplay touch during Climax coherent
    # rather than bouncing the canonical scene backwards or forwards.
    pure_intimacy_hold = (
        state["stage"] in {"foreplay", "explicit"}
        or (state["stage"] == "climax" and state["stage_level"] in {1, 2})
    ) and (semantic["intimacy_action"] or semantic["care"]) and not has_higher_than_intimacy
    pure_foreplay_hold = (
        state["stage"] in {"explicit"}
        or (state["stage"] == "climax" and state["stage_level"] in {1, 2})
    ) and semantic["foreplay_action"] and not has_higher_than_foreplay
    if pure_intimacy_hold or pure_foreplay_hold:
        action_kind = "intimacy" if pure_intimacy_hold else "foreplay"
        return normalize({
            **state,
            "gear_shift": {"action": "hold", "from": stage_label, "to": stage_label,
                           "reason": f"{action_kind} action uses an already-unlocked lower-tier action"},
            "reason": f"{action_kind} action preserves unlocked {stage_label} stage",
        })

    # Explicit pacing rule: ordinary user replies advance one substage only
    # while USER owns pace.  With character-led authority (including CNC), a
    # reply opens the next CHAR action but cannot advance the canonical stage
    # on its own; CHAR must visibly perform the stage-defining act or submit a
    # validated h_mode_decision.
    explicit_pause = (
        str(text or "").strip().casefold() in {"หยุด", "พัก", "hold", "pause"}
        or stop_kind in {"pause_action", "question_stop"}
    )
    if (state["stage"] == "explicit" and state["stage_level"] < 3
            and not explicit_pause and not response.get("ending")
            and (state.get("pace_authority") or {}).get("holder") != "character"):
        return pace(state, "advance")
    # A physical continuation in climax still advances one substage even
    # when its modifier requests a slower tempo (e.g. "ค่อยๆ ขยับ"). The
    # tempo and the substage are separate dimensions; only pause/stop holds.
    climax_action = bool(re.search(
        r"ขยับ|โยก|กระแทก|เร่ง|รัว|ทำต่อ|ต่อไป|ต่ออีก|อย่าหยุด|"
        r"\b(?:move|shift|thrust|grind|keep going|continue|don\W?t stop)\b",
        response.get("text", ""), re.IGNORECASE,
    )) and stop_kind not in {"pause_action", "question_stop"}
    # If user explicitly narrates orgasm/ejaculation while already in Climax (even at level 1 or 2),
    # honor the completion immediately rather than requiring 3 separate sub-turns.
    if state["stage"] == "climax" and response.get("orgasm_confirmed"):
        climax3_state = {**state, "stage_level": 3}
        if is_h_mode_end_intent(text):
            return pace(climax3_state, "orgasm_normal")
        stmt_fold = stop_info["channels"]["statement_clauses"] + " " + stop_info["channels"]["action"]
        if re.search(
            r'หื่น|กระหาย|ต้องการ|ทำต่อ|ต่อไป|อีกรอบ|ยัง(?:ยัง)?ไหว|ยังไหวอยู่|ไปต่อได้|ไม่ต้องพัก|'
            r'ไม่หยุด|โดยไม่หยุด|กระแทก|กระเด้า|ซอย|กระหน่ำ|เอา|เย็ด|สอดใส่|เข้า|ขยับ|เร่ง|แรงขึ้น|ถี่ขึ้น|'
            r'\b(?:continue|again|another round|want|desire|can keep going|still can)\b', stmt_fold,
        ):
            return pace(climax3_state, "orgasm_explicit")
        return pace(climax3_state, "orgasm_aftercare")

    if (state["stage"] == "climax" and state["stage_level"] < 3
            and climax_action and not explicit_pause and not response.get("ending")):
        return pace(state, "advance")

    # Detect an end request in every active H stage (including aftercare).
    if state["active"] and is_h_mode_end_intent(text):
        if not response["conditional"]:
            return pace(state, "hard_stop")

    if (state["stage"] in {"explicit", "climax"}
            and stop_kind == "hard_stop"
            and not response["conditional"]):
        return pace(state, "hard_stop")
    command = pacing_action_from_message(text)
    if state["stage"] == "aftercare" and state.get("aftercare_restart_question_pending"):
        if response.get("affirmative") or (
            not response.get("question") and not response.get("deferred")
            and bool(re.fullmatch(AFFIRMATIVE_FULLMATCH_PATTERN, response.get("text", "").strip(), re.IGNORECASE))
        ):
            return pace(normalize({**state, "aftercare_restart_question_pending": False}), "explicit")
        if response.get("deferred") or response.get("ending"):
            return normalize({**state, "aftercare_restart_question_pending": False,
                              "reason": "aftercare restart question declined or deferred"})
    decision = analyze_transition_message(state, text)
    if decision:
        action, reason = decision['action'], decision['reason']
        if action == 'climax_retry':
            return _restart_stage_level(state, reason)
        if action == 'hold':
            return normalize({
                **state,
                'gear_shift': {'action': 'hold', 'from': f"{state['stage']}:{state['stage_level']}", 'to': f"{state['stage']}:{state['stage_level']}", 'reason': reason},
                'reason': reason,
            })
        if action in {'advance', 'ease', 'aftercare', 'end_scene', 'hard_stop'} or action.startswith('orgasm_'):
            return pace(state, action)
        wanted = action
    else:
        wanted, reason = _requested_stage(text, config)

    if state["stage"] == "normal":
        if response.get("entry_stage"):
            wanted = response["entry_stage"]
            reason = f"player initiated {wanted} from normal"
        elif wanted in {"intimacy", "foreplay", "explicit"} and _has_normal_entry_signal(text):
            wanted = _normal_entry_stage(text)
            reason = f"player initiated {wanted} from normal"
        else:
            return state

    if state["active"] and state["stage"] != "aftercare" and not (state["stage"] == "climax" and state["stage_level"] == 3):
        quest = state.get("h_mode_quest") or {}
        if quest.get("status") == "active":
            target = str(quest.get("target_stage") or "")
            # A direct action that clearly belongs to the requested target
            # stage is itself an affirmative answer to the boundary quest.
            # In particular, explicit penetration from foreplay:3 must enter
            # explicit:1 rather than being treated as a failed quest and
            # resetting the current foreplay stage to level 1.
            direct_target_action = (
                target in {"foreplay", "explicit"}
                and (response.get("entry_stage") == target or wanted == target)
                and not response.get("deferred")
                and not response.get("conditional")
            )
            # At explicit:3, any ordinary user reply is sufficient to cross
            # the explicit -> climax boundary. A question inside the reply
            # (for example, "โอเค, อา... เสียวไหม?") is still a response;
            # only pause/stop/defer commands block the transition.
            climax_boundary_response = (
                target == "climax"
                and bool(str(text or "").strip())
                and str(text or "").strip().casefold() not in {"หยุด", "พัก", "hold", "pause"}
                and not response.get("ending")
                and not response.get("deferred")
            )
            if direct_target_action or climax_boundary_response or _quest_answer_matches(text, target, config, quest):
                completed = resolve_boundary_quest(state, "accepted")
                return normalize({
                    **completed, "stage": target, "scene_stage": target, "stage_level": 1,
                    "turns_in_level": 0,
                    "gear_shift": {"action": "upshift", "from": f"{state['stage']}:3", "to": f"{target}:1",
                                   "reason": "H-Quest completed by matching player intent"},
                    "reason": f"entered {target} level 1 after H-Quest",
                })
            # If user deferred, refused, or didn't match yet at boundary gate, hold current stage:3 rather than kicking back to level 1
            return normalize({
                **state,
                "reason": "H-Quest waiting for matching player intent at boundary gate",
            })
        stage_order = {"normal": 0, "intimacy": 1, "foreplay": 2, "explicit": 3, "climax": 4, "aftercare": 5}
        direct_higher_stage = (
            wanted in {"foreplay", "explicit"}
            and stage_order.get(wanted, 0) > stage_order.get(state["stage"], 0)
            and not response.get("deferred")
            and not response.get("conditional")
        )
        if not direct_higher_stage:
            sublevel = _sublevel_intent(text, state)
            if sublevel:
                return pace(state, sublevel)
            if wanted in MAIN_H_STAGES:
                return pace(state, "advance")
    if not wanted:
        return state

    if state["stage"] == "normal" and wanted in H_STAGES and state["h_energy"] < 1:
        return normalize({**state, "reason": "H-Mode requires at least 1 H-energy; recover 1 point every 30 minutes"})

    if wanted == state["stage"] and state["active"] and state["stage"] in H_STAGES:
        words = (text or "").casefold()
        if re.search(r'\?|ไหม|หรือเปล่า|หรือยัง|หรือไม่|อย่าเพิ่ง|ยังไม่|รอก่อน|ไม่ต้อง|ไม่อยาก|ไม่เอา|'
                     r'\b(?:shall we|would you|do you|can we|should we|not yet|wait|don\W?t|do not)\b', words):
            return normalize({**state, "reason": "question or refusal does not advance the current stage"})
        return pace(state, "advance")

    if wanted == "climax" and state.get("h_energy", 3) <= 0:
        return {**state, "updated_at": time.time(), "reason": "three orgasms completed; climax is locked in this scene"}

    allowed = config["transitions"].get(state["stage"], [state["stage"]])
    if state["stage"] == "normal":
        allowed = [*allowed, "foreplay", "explicit"]
    if wanted != "normal" and wanted not in allowed:
        stages = config.get("stages", [])
        try:
            direction = 1 if stages.index(wanted) > stages.index(state["stage"]) else -1
            candidates = [item for item in allowed if item != "normal" and (stages.index(item) - stages.index(state["stage"])) * direction > 0]
        except ValueError:
            candidates = []
        if not candidates:
            return {**state, "updated_at": time.time(), "reason": f"transition blocked: {reason}"}
        wanted = min(candidates, key=lambda item: abs(stages.index(item) - stages.index(state["stage"])))
        reason = f"transition redirected: {reason}"

    if wanted == "normal":
        from_str = f"{state['stage']}:{state['stage_level']}" if state["stage"] != "normal" else "normal:0"
        return normalize({
            **state, "stage": "normal", "scene_stage": "normal", "active": False, "stage_level": 0,
            "turns_in_level": 0, "orgasm_exhausted": False,
            "gear_shift": {"action": "downshift", "from": from_str, "to": "normal:0", "reason": reason},
            "h_mode_quest": {},
            "updated_at": time.time(), "reason": reason,
        })

    if wanted != state["stage"]:
        if state["stage"] == "normal" and state.get("intimacy_opportunity", {}).get("status") in {"declined", "expired"}:
            return {**state, "updated_at": time.time(), "reason": "opportunity was declined or expired; scene remains normal"}

        from_str = f"{state['stage']}:{state['stage_level']}" if state["stage"] != "normal" else "normal:0"
        normal_intimacy_pending = (
            state["stage"] == "normal" and wanted == "intimacy"
            and classify_scene_words(text)["intimacy_action"]
            and not classify_scene_words(text)["foreplay_action"]
            and not classify_scene_words(text)["explicit_action"]
        )
        return normalize({
            **state, "stage": wanted, "scene_stage": wanted, "active": True, "stage_level": 1,
            "turns_in_level": 0,
            "gear_shift": {"action": "upshift", "from": from_str, "to": f"{wanted}:1", "reason": reason},
            "h_mode_quest": _direct_user_quest(state, wanted, reason) if wanted in H_STAGES else {},
            "intimacy_opportunity": {},
            "normal_intimacy_pending_acceptance": normal_intimacy_pending,
            "updated_at": time.time(), "reason": reason,
        })

    return {**state, "updated_at": time.time(), "reason": reason}


def is_dominant(baseline: Any) -> bool:
    baseline = baseline if isinstance(baseline, dict) else {}
    card = baseline.get("card_data") or {}
    card = card if isinstance(card, dict) else {}
    traits = " ".join(str(source.get(key) or "") for source in (baseline, card)
                      for key in ("type", "character_type", "personality", "char_summary"))
    return bool(re.search(r"(?<![\w-])dominant(?![\w-])", traits, re.I)
                and not re.search(r"\b(?:not|non)[ -]+dominant\b", traits, re.I))


def post_orgasm_action(value: Any, baseline: Any = None) -> str:
    """Choose a character-led destination after Climax 3.

    H-energy represents sex drive, but personality determines whether that
    drive becomes another explicit round or a recovery beat.  User pace
    authority is handled by the caller before this policy is applied.
    """
    state = normalize(value)
    if state["h_energy"] < 1:
        return "orgasm_aftercare"
    baseline = baseline if isinstance(baseline, dict) else {}
    card = baseline.get("card_data") if isinstance(baseline.get("card_data"), dict) else {}
    traits = " ".join(str(source.get(key) or "") for source in (baseline, card)
                       for key in ("type", "character_type", "personality", "char_summary")).casefold()
    if re.search(r"dominant|รุก|ชอบคุม|เป็นฝ่ายนำ", traits) and not re.search(r"not dominant|non-dominant|ไม่ใช่ฝ่ายรุก", traits):
        return "orgasm_explicit"
    if re.search(r"switch|สลับบท|สลับกัน", traits):
        need_sources = [baseline.get(key, "") for key in
                        ("post_orgasm_need", "current_need", "sexual_need", "arousal", "arousal_state")]
        needs = " ".join(str(item) for item in need_sources).casefold()
        needs_state = baseline.get("needs_state")
        if isinstance(needs_state, dict):
            needs += " " + " ".join(f"{key} {value}" for key, value in needs_state.items())
        wants_more = bool(re.search(
            r"continue|explicit|sexual|desire|lust|arous|yearn|want(?:ing)?(?:.*more)?|need.*(?:more|sex)|"
            r"ทำต่อ|ต้องการ|อยาก|หงี่|เงี่ยน|เสี้ยน|หื่น|กระหาย|กำหนัด|กระสัน|ร้อน|ยังไหว|ไม่อิ่ม|ไม่พอ|นำจังหวะ|ฝ่ายนำ",
            needs,
        ))
        wants_care = bool(re.search(
            r"aftercare|recover|rest|comfort|care|tender|พัก|กอด|ปลอบ|ดูแล|เหนื่อย|อ่อนแรง|อิ่มแล้ว|พอแล้ว",
            needs,
        ))
        if wants_more and not wants_care:
            return "orgasm_explicit"
    # Submissive, gentle, and untyped characters prefer recovery by default.
    return "orgasm_aftercare"


def complete_character_declared_orgasm(value: Any, baseline: Any = None) -> Dict[str, Any]:
    """Record CHAR's declared orgasm immediately, from any active H-Mode beat.

    The reply itself is the canonical declaration.  We briefly normalize the
    pacing position to Climax III so the existing orgasm path consumes exactly
    one H-Energy and applies its normal post-orgasm destination policy.
    """
    state = normalize(value)
    if not state["active"] or state["stage"] == "normal":
        return state
    climax_state = normalize({
        **state,
        "stage": "climax", "scene_stage": "climax", "stage_level": 3,
        "turns_in_level": 0,
        "reason": "character declared orgasm in dialogue/action",
    })
    completed = pace(climax_state, post_orgasm_action(climax_state, baseline))
    return normalize({
        **completed,
        "reason": "character-declared orgasm counted immediately; " + str(completed.get("reason") or ""),
    })


def has_character_type(baseline: Any) -> bool:
    if not isinstance(baseline, dict):
        return False
    card = baseline.get("card_data") if isinstance(baseline.get("card_data"), dict) else {}
    return bool(" ".join(str(source.get(key) or "") for source in (baseline, card)
                          for key in ("type", "character_type", "personality", "char_summary")).strip())


def character_controls_post_orgasm(baseline: Any, authority: Any) -> bool:
    """Whether the character may choose the post-orgasm destination itself."""
    if not isinstance(authority, dict) or authority.get("holder") == "user":
        return False
    if is_dominant(baseline):
        return True
    if not isinstance(baseline, dict):
        return False
    card = baseline.get("card_data") if isinstance(baseline.get("card_data"), dict) else {}
    traits = " ".join(str(source.get(key) or "") for source in (baseline, card)
                       for key in ("type", "character_type", "personality", "char_summary")).casefold()
    return bool(re.search(r"switch|สลับบท|สลับกัน", traits))


def complete_turn(value: Any, nsfw_mode: str, baseline: Any = None) -> Dict[str, Any]:
    state = normalize(value)
    if nsfw_mode not in {"local", "h_mode", "h-mode", "h"} or not state["active"]:
        return state
    next_turns = state["turns_in_level"] + 1
    quest = state.get("h_mode_quest") or {}
    if quest.get("status") == "active" and next_turns > int(quest.get("expires_after_turn", next_turns + 1)):
        quest = {**quest, "status": "expired", "resolution": "no_response", "resolved_at": time.time()}
    held = normalize({**state, "turns_in_level": next_turns, "h_mode_quest": quest, "updated_at": time.time(),
                      "reason": "level held for completed character turn"})
    # A turn that has already performed a user-requested level/stage change
    # must never perform a second automatic change in the same turn.  This is
    # especially important for climax:2 -> climax:3, where dominant/automatic
    # pacing used to continue immediately into aftercare.
    gear_shift = held.get("gear_shift") or {}
    transition_from = str(gear_shift.get("from") or "")
    transition_to = str(gear_shift.get("to") or "")
    same_turn_transition = (
        bool(transition_from and transition_to and transition_from != transition_to)
        and transition_to == f"{held['stage']}:{held['stage_level']}"
        and gear_shift.get("action") in {"upshift", "downshift", "character_led_upshift", "character_decision", "character_action_transition", "stage_down", "orgasm_completed"}
    )
    authority = held.get("pace_authority") or {}
    if held["stage"] == "climax" and held["stage_level"] == 3:
        if same_turn_transition:
            return normalize({**held,
                              "gear_shift": {"action": "hold", "from": "climax:3", "to": "climax:3",
                                             "reason": "one transition per turn enforced"},
                              "reason": "climax level reached; wait for the next user turn before any completion or aftercare transition"})
        user_holding_climax = (state.get("reason") == "continued climax peak intensity; holding at climax 3"
                               or (state.get("reason") or "").startswith("user asked climax confirmation question"))
        if character_controls_post_orgasm(baseline, authority) and not user_holding_climax:
            # H-energy is the character's remaining sex drive.  A dominant
            # character with drive left prefers another explicit round after
            # orgasm; only an exhausted drive falls back to aftercare.
            return pace(held, post_orgasm_action(held, baseline))
        return normalize({**held, "reason": "climax 3 held; waiting for user pacing",
                          "h_mode_quest": {}})
    target = _QUEST_TARGETS.get(held["stage"])
    if authority.get("holder") == "character" and not is_orgasm_exhausted(held):
        # Character-led authority means the completed CHAR turn is a valid
        # pacing choice.  The old hold here made the scene wait for a special
        # marker even after CHAR had already led the turn, which left the
        # model repeating invitations instead of progressing the scene.
        # Do not apply a second transition when this reply has already made a
        # visible or private character transition.
        if same_turn_transition:
            return held
        return pace(held, "advance")
    return held


def pacing_action_from_message(text: str) -> str | None:
    command = " ".join((text or "").strip().casefold().split())
    commands = {
        "/pace continue": "advance", "/pace next": "advance", "/pace advance": "advance", "/pace faster": "advance",
        # Explicit target commands make a Climax 2 → 3 request unambiguous.
        "/pace climax3": "advance", "/pace climax 3": "advance", "/pace peak": "advance",
        "proceed": "advance", "continue": "advance",
        "/pace aftercare": "aftercare", "/pace end": "end_scene", "/pace stop": "hard_stop",
        "หยุดเดี๋ยวนี้": "hard_stop", "ไม่เอา": "hard_stop", "stop now": "hard_stop",
        "ต่อ": "advance", "ต่ออีกนิด": "advance",
        "เข้า aftercare": "aftercare", "ไป aftercare": "aftercare",
        "จบฉาก": "end_scene",
    }
    return commands.get(command)


def process_normal_opportunity(value: Any, text: str) -> tuple[Dict[str, Any], bool]:
    state = normalize(value)
    if state["stage"] != "normal" or (state.get("interruption") or {}).get("unresolved"):
        return state, False
    semantic = classify_scene_words(text)
    words = semantic["text"]
    opportunity = state.get("intimacy_opportunity") or {}
    decline = semantic["refusal"] or semantic["defer"] or any(term in words for term in ("กลับก่อน", "พอแค่นี้", "don't want"))
    accept = semantic["affirmative"] or semantic["intimacy_action"] or any(term in words for term in ("ได้สิ", "ตกลง", "แน่ใจ", "มั่นใจ", "อยู่ด้วยกัน", "อยู่กับเธอ", "stay with you"))
    if opportunity.get("status") == "active":
        if decline:
            return normalize({**state, "intimacy_opportunity": {**opportunity, "status": "declined",
                "resolution": "declined_gently", "resolved_at": time.time()}, "reason": "intimacy opportunity declined"}), True
        if accept:
            quest = _direct_user_quest(state, "intimacy", "accepted_normal_opportunity")
            return normalize({**state, "stage": "intimacy", "scene_stage": "intimacy", "active": True,
                "stage_level": 1, "turns_in_level": 0, "h_mode_quest": quest,
                "intimacy_opportunity": {**opportunity, "status": "completed", "resolution": "accepted",
                    "resolved_at": time.time()}, "reason": "normal intimacy opportunity accepted"}), True
        turns = int(opportunity.get("turns_active", 0) or 0) + 1
        if turns >= int(opportunity.get("expires_after_turn", 3) or 3):
            return normalize({**state, "intimacy_opportunity": {**opportunity, "turns_active": turns,
                "status": "expired", "resolution": "no_response", "resolved_at": time.time()},
                "reason": "normal intimacy opportunity expired"}), True
        return normalize({**state, "intimacy_opportunity": {**opportunity, "turns_active": turns}}), False
    if opportunity.get("status") in {"declined", "expired"}:
        return state, False

    cues = ("คิดถึง", "อยู่ด้วยกัน", "อยู่กับเธอ", "จับมือ", "กอด", "ใกล้ ๆ", "miss you", "stay with", "hold hands", "hug")
    if any(term in words for term in cues) and not _is_platonic_escort_or_greeting(words):
        opportunity = {
            "id": _quest_id(state), "status": "active", "source_type": "dialogue",
            "source_event_id": "current_user_message", "from_stage": "normal", "target_stage": "intimacy",
            "target_level": 1, "motivation": "respond_to_shared_closeness",
            "objective": "invite a small moment of closeness", "required_intent": "accept_closeness",
            "expires_after_turn": 3, "created_at": time.time(), "resolution": None,
        }
        return normalize({**state, "intimacy_opportunity": opportunity,
                          "reason": "normal intimacy opportunity offered"}), True
    return state, False


def grant_character_pace_authority(value: Any, text: str) -> Dict[str, Any]:
    state = normalize(value)
    words = (text or "").casefold()
    delegated_action = bool(re.search(DELEGATED_UNION_PATTERN, words, re.IGNORECASE))
    woman_lead_request = character_led_h_mode_request(text) and not is_direct_h_mode_continuation(text)
    revoke = (
        "ฉันจะนำเอง", "ไม่ต้องนำ", "ไม่เอาแล้ว", "ยังไม่ใกล้", "อย่าเพิ่ง",
        "i'll lead", "don't lead", "not yet", "not close", "don't come yet",
    )
    if any(term in words for term in revoke):
        return normalize({**state, "pace_authority": {"holder": "user", "revoked_at": time.time()},
                          "character_action_consent": {},
                          "reason": "character pace authority revoked"})
    if (delegated_action or woman_lead_request) and not is_orgasm_exhausted(state):
        return normalize({
            **state,
            "pace_authority": {"holder": "character", "mode": "character_led",
                               "scope": "current_h_mode_scene", "revocable": True, "granted_at": time.time()},
            "character_action_consent": {
                "granted_by": "user", "scope": "current_h_mode_scene",
                "meaning": "CHAR has full turbo permission and pace authority to perform and escalate stage actions",
                "granted_at": time.time(),
            },
            "reason": "user granted character-led pace and turbo full permission",
        })
    return state


def apply_character_h_mode_decision(value: Any, decision: Any) -> Dict[str, Any]:
    """Commit CHAR's private, server-validated H-Mode choice.

    The model may choose a new active stage/beat,
    but it cannot use this channel to overwrite a user stop, fabricate USER
    consent, or start H-Mode from Normal.  The resulting value is the new
    canonical state for the following turn.
    """
    state = normalize(value)
    raw = decision if isinstance(decision, dict) else {}
    if not state["active"] or not raw:
        return state
    try:
        gained = max(0, min(3, int(raw.get("h_energy_gain", 0) or 0)))
    except (TypeError, ValueError):
        gained = 0
    target_stage = str(raw.get("stage") or "").strip().casefold()
    try:
        target_level = int(raw.get("stage_level", 1) or 1)
    except (TypeError, ValueError):
        target_level = 1
    target_level = max(1, min(3, target_level))
    if target_stage not in H_STAGES:
        target_stage = ""
    if not gained and not target_stage:
        return state
    # Character initiative can raise pacing or enter recovery, but it cannot
    # silently undo an unlocked stage/substage.  Aftercare may restart only
    # after CHAR has explicitly asked USER whether to resume.
    stage_rank = {"normal": 0, "intimacy": 1, "foreplay": 2, "explicit": 3, "climax": 4}
    rejected_downshift = False
    if target_stage:
        if target_stage == "aftercare":
            pass  # Recovery is an explicit terminal route, not a lower act.
        elif state["stage"] == "aftercare":
            if not (state.get("aftercare_restart_question_pending") and target_stage in {"foreplay", "explicit"}):
                target_stage = ""
                rejected_downshift = True
        elif stage_rank.get(target_stage, -1) < stage_rank.get(state["stage"], -1):
            target_stage = ""
            rejected_downshift = True
        elif target_stage == state["stage"] and target_level < state["stage_level"]:
            target_level = state["stage_level"]
            rejected_downshift = True
    next_energy = min(3, state["h_energy"] + gained)
    destination = target_stage or state["stage"]
    destination_level = target_level if target_stage else state["stage_level"]
    changed_stage = (destination, destination_level) != (state["stage"], state["stage_level"])
    now = time.time()
    reason = str(raw.get("reason") or "character-owned H-Mode decision").strip()[:240]
    if rejected_downshift:
        reason = "character decision preserved the already-unlocked pacing"
    return normalize({
        **state,
        "stage": destination, "scene_stage": destination, "active": True,
        "stage_level": destination_level, "turns_in_level": 0 if changed_stage else state["turns_in_level"],
        "h_energy": next_energy, "h_energy_updated_at": now if gained else state["h_energy_updated_at"],
        "orgasm_exhausted": False if next_energy else state.get("orgasm_exhausted", False),
        "h_mode_quest": {},
        "character_h_mode_decision": {
            "h_energy_gain": gained, "stage": destination if target_stage else "",
            "stage_level": destination_level if target_stage else None, "reason": reason, "at": now,
        },
        "gear_shift": {
            "action": "character_decision", "from": f"{state['stage']}:{state['stage_level']}",
            "to": f"{destination}:{destination_level}", "reason": reason,
        },
        "updated_at": now,
        "reason": reason,
    })


def apply_character_starred_action(value: Any, reply: Any, allow_normal_entry: bool = False) -> Dict[str, Any]:
    """Promote a visible `*...*` CHAR action into canonical H-Mode pacing.

    USER actions are parsed before generation.  Assistant text normally is not
    parsed at all, which made a CHAR action look real in prose but leave the
    next turn on the old stage.  Only a starred physical action can use this
    bridge; ordinary dialogue and involuntary reactions do not move pacing.
    """
    state = normalize(value)
    if (not state["active"] and not allow_normal_entry) or is_orgasm_exhausted(state):
        return state
    actions = re.findall(r"\*([^*]+)\*", str(reply or ""), flags=re.DOTALL)
    if not actions:
        return state
    joined_actions = " ".join(actions)
    if _is_platonic_escort_or_greeting(joined_actions.casefold()):
        return state
    cleaned_actions = _strip_nonsexual_gestures(joined_actions)
    semantic = classify_scene_words(cleaned_actions)
    target = ("explicit" if semantic["explicit_action"] else "foreplay" if semantic["foreplay_action"]
              else "intimacy" if semantic["intimacy_action"] else "")
    if not target or target == state["stage"]:
        return state
    # A completed orgasm normally enters Aftercare.  CHAR may explicitly
    # choose a new round from that recovery state only by visibly performing
    # a new foreplay/explicit action, or after CHAR has asked USER whether to
    # resume.  Gentle action remains Aftercare and never restarts a scene.
    gear_action = str((state.get("gear_shift") or {}).get("action") or "")
    aftercare_restart_allowed = (
        state["stage"] == "aftercare"
        and target in {"foreplay", "explicit"}
        and (gear_action == "orgasm_completed" or state.get("aftercare_restart_question_pending"))
    )
    # Prevent incidental minor actions (e.g. caressing, holding hands, kissing) from downgrading
    # any higher stage back to a lower stage (e.g., Foreplay -> Intimacy, Explicit -> Foreplay/Intimacy).
    stage_hierarchy = {"normal": 0, "intimacy": 1, "foreplay": 2, "explicit": 3, "climax": 4, "aftercare": 5}
    current_rank = stage_hierarchy.get(state["stage"], 0)
    target_rank = stage_hierarchy.get(target, 0)
    if state["active"] and target_rank <= current_rank and not aftercare_restart_allowed:
        return state
    if state["stage"] == "aftercare" and gear_action == "orgasm_completed" and not aftercare_restart_allowed:
        # The post-orgasm reply may contain residual intimacy, but only a new
        # foreplay/explicit act is allowed to restart the scene.
        return state
    now = time.time()
    return normalize({
        **state,
        "stage": target, "scene_stage": target, "active": True,
        "stage_level": 1, "turns_in_level": 0, "h_mode_quest": {},
        "aftercare_restart_question_pending": False,
        "character_h_mode_decision": {
            "source": "starred_character_action", "stage": target, "stage_level": 1,
            "reason": "CHAR performed a visible stage-defining action", "at": now,
        },
        "gear_shift": {
            "action": "character_action_transition", "from": f"{state['stage']}:{state['stage_level']}",
            "to": f"{target}:1", "reason": "CHAR performed a visible starred action",
        },
        "updated_at": now, "reason": f"character starred action entered {target} level 1",
    })


def recover_character_pace_authority(value: Any, history: Any) -> Dict[str, Any]:
    state = normalize(value)
    if not state["active"] or (state.get("pace_authority") or {}).get("holder"):
        return state
    user_texts = [
        str(item.get("content") or "") for item in (history or [])
        if isinstance(item, dict) and item.get("role") == "user"
    ]
    boundary_terms = (
        "/pace stop", "/pace end", "หยุดเดี๋ยวนี้", "จบฉาก",
        "ไม่เอาแล้ว", "พอแล้ว", "stop now", "no more",
    )
    start = 0
    for index, text in enumerate(user_texts):
        folded = text.casefold()
        if any(term in folded for term in boundary_terms):
            start = index + 1
    recovered = state
    for text in user_texts[start:]:
        recovered = grant_character_pace_authority(recovered, text)
    if (recovered.get("pace_authority") or {}).get("holder") == "character":
        recovered["reason"] = "character pace authority recovered from current-scene history"
    return normalize(recovered)


_QUEST_TARGETS = {"intimacy": "foreplay", "foreplay": "explicit", "explicit": "climax"}
_QUEST_OBJECTIVES = {
    "foreplay": "wants to deepen the shared closeness",
    "explicit": "wants a clear, mutual invitation to continue",
    "climax": "wants a mutual choice to carry the existing moment forward",
}


def _quest_id(state: Dict[str, Any]) -> str:
    return f"hq_{int(time.time() * 1000)}_{state['stage']}_{state['stage_level']}"


def offer_boundary_quest(value: Any, source_type: str = "scene_event") -> Dict[str, Any]:
    state = normalize(value)
    target = _QUEST_TARGETS.get(state["stage"])
    if not target or state["stage_level"] != 3:
        return state
    old = state.get("h_mode_quest") or {}
    if old.get("status") == "active" and old.get("from_stage") == state["stage"]:
        return state
    quest = {
        "id": _quest_id(state), "status": "active", "source_type": source_type,
        "source_event_id": f"scene:{state['stage']}:{state['stage_level']}",
        "from_stage": state["stage"], "target_stage": target, "target_level": 1,
        "motivation": "shared_scene_momentum",
        "objective": _QUEST_OBJECTIVES[target], "required_intent": "confirm_escalation",
        "offer_turn": state["turns_in_level"], "expires_after_turn": state["turns_in_level"] + 3,
        "resolution": None,
    }
    return normalize({**state, "h_mode_quest": quest, "updated_at": time.time(),
                      "reason": f"boundary quest offered for {state['stage']} to {target}"})


def resolve_boundary_quest(value: Any, resolution: str) -> Dict[str, Any]:
    state = normalize(value)
    quest = state.get("h_mode_quest") or {}
    if quest.get("status") != "active":
        return state
    status = {"accepted": "completed", "declined": "declined", "expired": "expired", "failed": "failed"}.get(resolution, "failed")
    return normalize({**state, "h_mode_quest": {**quest, "status": status, "resolution": resolution,
                                                   "resolved_at": time.time()}, "updated_at": time.time()})


def _direct_user_quest(state: Dict[str, Any], target: str, reason: str) -> Dict[str, Any]:
    return {
        "id": _quest_id(state), "status": "completed", "source_type": "user_initiated",
        "source_event_id": "current_user_message", "from_stage": state["stage"],
        "target_stage": target, "target_level": 1, "motivation": "user_initiated_scene_change",
        "objective": "user explicitly initiated this next beat", "required_intent": "direct_user_initiation",
        "offer_turn": state["turns_in_level"], "expires_after_turn": None,
        "resolution": f"accepted_directly: {reason}", "resolved_at": time.time(),
    }


def hard_stop(value: Any) -> Dict[str, Any]:
    state = normalize(value)
    stage, level = state["stage"], state["stage_level"]
    weight = {"normal": 0, "intimacy": 1, "foreplay": 2, "explicit": 3, "climax": 4, "aftercare": 1}.get(stage, 0)
    severity = min(4, weight + (1 if level >= 3 and weight else 0))
    effect = {0: "none", 1: "surprised", 2: "unsettled", 3: "abrupt_disappointment", 4: "emotionally_cut_off"}[severity]
    interruption = {
        "source_stage": stage,
        "source_level": level,
        "severity": severity,
        "emotion_effect": effect,
        "unresolved": severity > 0,
        "occurred_at": time.time(),
    }
    gear_shift = {
        "action": "hard_stop",
        "from": f"{stage}:{level}" if stage != "normal" else "normal:0",
        "to": "normal:0",
        "reason": f"hard_stop_with_{effect}",
    }
    return normalize({
        **state, "stage": "normal", "scene_stage": "normal", "active": False,
        "stage_level": 0, "turns_in_level": 0, "orgasm_exhausted": False,
        "interruption": interruption, "gear_shift": gear_shift, "updated_at": time.time(),
        "h_mode_quest": resolve_boundary_quest(state, "failed").get("h_mode_quest", {}),
        "pace_authority": {"holder": "user", "revoked_at": time.time(), "reason": "hard stop"},
        "character_action_consent": {},
        "reason": f"hard stop from {stage} {level}/3; emotional effect: {effect}",
    })


def resolve_interruption(value: Any, text: str) -> Dict[str, Any]:
    state = normalize(value)
    interruption = state.get("interruption") or {}
    words = (text or "").casefold()
    repair = ("ขอโทษ", "อธิบาย", "ไม่ไหว", "ไม่สบาย", "ขอพัก", "sorry", "explain", "need a break")
    if interruption.get("unresolved") and any(word in words for word in repair):
        return normalize({**state, "interruption": {**interruption, "unresolved": False, "resolved_at": time.time()},
                          "reason": "hard-stop aftermath acknowledged in normal conversation"})
    return state


def pace(value: Any, action: str) -> Dict[str, Any]:
    state = normalize(value)
    # Never let direct API/UI pacing calls bypass the no-gear-down policy.
    # A slower requested rhythm is expressive only; canonical pacing holds.
    if action in {"ease", "stage_down"}:
        stage, level = state["stage"], state["stage_level"]
        return normalize({
            **state,
            "gear_shift": {"action": "hold", "from": f"{stage}:{level}", "to": f"{stage}:{level}",
                           "reason": "gear-down is disabled in H-Mode"},
            "reason": "gear-down is disabled in H-Mode; keep the current canonical stage",
        })
    if action == "ease":
        state["pace_authority"] = {"holder": "user", "revoked_at": time.time()}
    stage, level = state["stage"], state["stage_level"]

    def out(gear_action: str = "hold", reason_key: str = "", **changes: Any) -> Dict[str, Any]:
        result = {**state, **changes, "updated_at": time.time()}
        if "stage" in changes and "scene_stage" not in changes:
            result["scene_stage"] = changes["stage"]
        to_stage = result.get("scene_stage", result.get("stage", "normal"))
        to_level = result.get("stage_level", 0)
        from_str = f"{stage}:{level}" if stage != "normal" else "normal:0"
        to_str = f"{to_stage}:{to_level}" if to_stage != "normal" else "normal:0"
        gear_shift = {
            "action": gear_action,
            "from": from_str,
            "to": to_str,
            "reason": reason_key or result.get("reason", ""),
        }
        result["gear_shift"] = gear_shift
        return normalize(result)

    if action == "hard_stop":
        return hard_stop(state)

    if action == "stage_down":
        if stage in {"intimacy", "foreplay"}:
            return out(
                gear_action="hold", reason_key="stage_down_blocked_in_early_stages",
                reason=f"stage_down locked in {stage}; hold current substage",
            )
        targets = {
            "explicit": ("explicit", max(1, level - 1)) if level > 1 else ("foreplay", 1),
            "climax": ("climax", max(1, level - 1)) if level > 1 else ("explicit", 1),
        }
        target_stage, target_level = targets.get(stage, (stage, level))
        return out(
            gear_action="stage_down", reason_key=f"stage_down_to_{target_stage}_{target_level}",
            stage=target_stage, scene_stage=target_stage, active=True, stage_level=target_level,
            turns_in_level=0, h_mode_quest=resolve_boundary_quest(state, "declined").get("h_mode_quest", {}),
            reason=f"stage down: {stage}:{level} → {target_stage}:{target_level}",
        )

    if action == "end_scene":
        stop_target = ("aftercare", 1)
        return out(
            gear_action="to_aftercare",
            reason_key="soft_end_to_aftercare",
            stage=stop_target[0], scene_stage=stop_target[0], active=True,
            stage_level=stop_target[1], turns_in_level=0,
            reason=f"soft ending: {stage}:{level} → aftercare:1",
            h_mode_quest=state.get("h_mode_quest", {}),
            pace_authority={},
        )

    if action.startswith("orgasm_"):
        if stage != "climax" or level != 3:
            return out(gear_action="hold", reason_key="orgasm_requires_climax_three",
                       reason="orgasm can only be completed at climax level 3", rejected=True)
        remaining_energy = max(0, state["h_energy"] - 1)
        exhausted = (remaining_energy == 0)
        energy_change = {
            "h_energy": remaining_energy,
            "h_energy_updated_at": time.time(),
            "exhausted": exhausted,
            "orgasm_exhausted": exhausted,
            "orgasm_event": {"h_energy": remaining_energy, "exhausted": exhausted},
        }
        target = action.removeprefix("orgasm_")
        if target == "normal":
            return out(
                gear_action="orgasm_completed", reason_key="orgasm_to_normal",
                stage="normal", scene_stage="normal", active=False, stage_level=0, turns_in_level=0,
                **energy_change,
                orgasm_exhausted=False,
                terminal_affection_penalty_applied=False,
                pace_authority={}, h_mode_quest={}, reason="orgasm completed; scene ended",
            )
        if target == "explicit":
            return out(
                gear_action="orgasm_completed", reason_key="orgasm_to_explicit",
                stage="explicit", scene_stage="explicit", active=True, stage_level=1, turns_in_level=0,
                **energy_change,
                terminal_affection_penalty_applied=False,
                pace_authority={}, h_mode_quest={},
                reason="orgasm completed; H-Energy Exhausted (active condition in explicit)" if exhausted else "orgasm completed; user continued the scene",
            )
        return out(
            gear_action="orgasm_completed", reason_key="orgasm_to_aftercare",
            stage="aftercare", scene_stage="aftercare", active=True, stage_level=1, turns_in_level=0,
            **energy_change,
            terminal_affection_penalty_applied=False,
            pace_authority={}, h_mode_quest={},
            reason="orgasm completed; H-Energy Exhausted (entered aftercare)" if exhausted else "orgasm completed; entered aftercare",
        )

    if stage == "normal":
        return out(gear_action="hold", reason_key="normal_gate_required", reason="H-Mode must begin through the existing consent and scene gate", rejected=True)

    if action == "aftercare":
        return out(
            gear_action="downshift" if stage in {"climax", "explicit"} else "hold",
            reason_key="entered_aftercare",
            stage="aftercare", scene_stage="aftercare", active=True, stage_level=1, turns_in_level=0,
            reason="entered aftercare",
            h_mode_quest=resolve_boundary_quest(state, "declined").get("h_mode_quest", {}),
            pace_authority={},
        )

    if stage == "aftercare":
        # A new, confirmed sexual action from aftercare starts a new round at
        # its proper entry stage. Recovery is not a permanent one-way lock.
        if action in {"intimacy", "foreplay", "explicit"}:
            return out(
                gear_action="restart_from_aftercare",
                reason_key=f"aftercare_to_{action}_1",
                stage=action, scene_stage=action, active=True,
                stage_level=1, turns_in_level=0,
                reason=f"user restarted {action} from aftercare",
                h_mode_quest={}, pace_authority={},
            )
        if action == "advance":
            if state["turns_in_level"] < 1:
                return out(gear_action="hold", reason_key="dwell_turn_required", reason="ช่วงนี้กำลังดำเนินอยู่ ขอให้อยู่กับจังหวะนี้อีกหนึ่งข้อความก่อน", rejected=True)
            if level < 3:
                return out(gear_action="upshift", reason_key="aftercare_continues", stage_level=level + 1, turns_in_level=0, reason="aftercare continues")
            return out(gear_action="hold", reason_key="aftercare_terminal", reason="aftercare can only continue or end this scene")
        if action == "ease":
            if level > 1:
                return out(gear_action="downshift", reason_key="eased_aftercare", stage_level=level - 1, turns_in_level=0, reason="eased down aftercare level")
            return out(gear_action="hold", reason_key="aftercare_locked", reason="aftercare cannot return to H-Mode; continue or end scene")
        return out(gear_action="hold", reason_key="aftercare_terminal", reason="aftercare can only continue or end this scene")

    if action == "advance":
        # Explicit is response-driven: any non-pause/non-stop user turn may
        # move one substage immediately. Other stages retain the dwell-turn
        # guard.
        if stage not in {"explicit", "climax"} and state["turns_in_level"] < 1:
            return out(gear_action="hold", reason_key="dwell_turn_required", reason="ช่วงนี้กำลังดำเนินอยู่ ขอให้อยู่กับจังหวะนี้อีกหนึ่งข้อความก่อน", rejected=True)

        if stage == "climax" and level == 3:
            return pace(state, "orgasm_explicit")

        if level < 3:
            next_level = level + 1
            advanced = out(
                gear_action="upshift",
                reason_key=f"upshift_to_{stage}_{next_level}",
                stage_level=next_level, turns_in_level=0,
                reason=f"advanced to {stage} level {next_level}",
            )
            if next_level == 3 and stage in {"intimacy", "foreplay", "explicit"}:
                return offer_boundary_quest(advanced)
            return advanced

        next_stage = {"intimacy": "foreplay", "foreplay": "explicit", "explicit": "climax"}.get(stage)
        if next_stage:
            if (state.get("pace_authority") or {}).get("holder") == "character":
                return out(
                    gear_action="character_led_upshift",
                    reason_key=f"character_led_to_{next_stage}_1",
                    stage=next_stage, scene_stage=next_stage, stage_level=1, turns_in_level=0,
                    h_mode_quest={},
                    reason=f"character-led transition into {next_stage}",
                )
            quest = state.get("h_mode_quest") or {}
            if not (quest.get("status") == "active" and quest.get("from_stage") == stage and quest.get("target_stage") == next_stage):
                offered = offer_boundary_quest(state)
                return out(gear_action="hold", reason_key="boundary_quest_offered",
                           h_mode_quest=offered.get("h_mode_quest", {}),
                           reason=f"a narrative invitation is needed before entering {next_stage}")
            completed = resolve_boundary_quest(state, "accepted")
            return out(
                gear_action="upshift",
                reason_key=f"upshift_to_{next_stage}_1",
                stage=next_stage, scene_stage=next_stage, stage_level=1, turns_in_level=0,
                h_mode_quest=completed.get("h_mode_quest", {}),
                reason=f"entered {next_stage} level 1",
            )
        return out(gear_action="hold", reason_key="stage_terminal", reason="this stage cannot advance further")

    if action == "ease":
        if stage in {"intimacy", "foreplay"}:
            return out(
                gear_action="hold", reason_key="ease_blocked_in_early_stages",
                reason=f"ease locked in {stage}; hold current substage",
            )
        if level > 1:
            return out(
                gear_action="downshift",
                reason_key=f"downshift_to_{stage}_{level - 1}",
                stage_level=level - 1, turns_in_level=0, reason=f"eased down to {stage} level {level - 1}",
                h_mode_quest=resolve_boundary_quest(state, "declined").get("h_mode_quest", {}),
            )
        previous = {"explicit": "foreplay", "climax": "explicit"}.get(stage)
        if previous:
            return out(
                gear_action="downshift",
                reason_key=f"downshift_to_{previous}_1",
                stage=previous, scene_stage=previous, stage_level=1, turns_in_level=0,
                h_mode_quest=resolve_boundary_quest(state, "declined").get("h_mode_quest", {}),
                reason=f"eased into {previous} level 1",
            )
        return out(
            gear_action="downshift",
            reason_key="downshift_to_normal",
            stage="normal", scene_stage="normal", active=False, stage_level=0, turns_in_level=0,
            orgasm_exhausted=False, reason="returned to normal conversation",
            h_mode_quest=resolve_boundary_quest(state, "declined").get("h_mode_quest", {}),
        )

    return out(gear_action="hold", reason_key="unknown_action", reason="unknown pacing action")


def rebuild(history: Any, nsfw_mode: str, baseline: Any = None) -> Dict[str, Any]:
    state: Dict[str, Any] = dict(DEFAULT)
    for message in history or []:
        if isinstance(message, dict) and message.get("role") == "user":
            text = str(message.get("content") or "")
            state = grant_character_pace_authority(state, text)
            opportunity_state, opportunity_handled = process_normal_opportunity(state, text)
            action = pacing_action_from_message(text)
            state = (opportunity_state if opportunity_handled else
                     pace(state, action) if action else
                     advance(state, text, nsfw_mode))
            if not action:
                state = resolve_interruption(state, text)
        elif isinstance(message, dict) and message.get("role") == "assistant" and not message.get("proactive") and not message.get("is_first_message"):
            state = resolve_normal_intimacy_character_response(state, str(message.get("content") or ""))
            state = capture_character_demand(state, str(message.get("content") or ""))
            state = complete_turn(state, nsfw_mode, baseline)
    return state


def stage_rule(language: str, value: Any) -> str:
    """Return the canonical Thai stage contract for every reply language.

    The content governs scene semantics only.  Language adaptation in the
    caller still determines the visible response language.
    """
    stage = normalize(value)["stage"]
    filename = "Thai.md"
    try:
        raw = (ROOT / "stages" / filename).read_text(encoding="utf-8")
    except OSError:
        return ""
    marker = f"## {stage}"
    section = raw.split(marker, 1)
    return section[1].split("\n## ", 1)[0].strip() if len(section) == 2 else ""


def relationship_response_rule(affection: Any = 10, relationship: str = "") -> str:
    """Return relationship guidance used for every visible H-Mode reply.

    Canonical stage decides *which* kind of activity is possible.  This rule
    decides how personally open, trusting, and self-directed CHAR may sound
    while answering inside that stage. A confirmed action is never erased;
    relationship context guides CHAR's own willingness and initiative rather
    than imposing a system-level rejection.
    """
    try:
        closeness = max(-100, min(100, int(affection)))
    except (TypeError, ValueError):
        closeness = 10
    label = str(relationship or "unspecified relationship").strip()
    header = (
        "[Relationship-calibrated response — authoritative]\n"
        f"Current affection/trust: {closeness}/100. Relationship: {label}.\n"
        "Apply this to every visible reply: dialogue register, distance, eye contact, willingness wording, "
        "reciprocal touch, and CHAR-led initiative. Canonical stage still controls the allowed activity. "
        "A confirmed USER action may receive its immediate in-character reaction, but do not turn bodily response "
        "into consent, trust, or an invitation that the relationship has not established. Low affection is context "
        "for CHAR's own decision: CHAR may accept cautiously, ask for clarity, set a boundary, or refuse naturally. "
        "Never present that decision as a system restriction. Direct USER boundaries and an enabled CNC agreement take priority.\n"
    )
    if closeness < 30:
        return header + (
            "Guarded tier: preserve personal distance and caution. CHAR may react to confirmed contact and choose to "
            "accept cautiously, ask for clarity, state a boundary, or refuse. Do not assume consent, intimate pet names, "
            "or established-lover familiarity. If CHAR accepts, CHAR may still take any stage-permitted initiative when "
            "the current scene, explicit USER delegation, or CHAR's own personality supports it."
        )
    if closeness < 50:
        return header + (
            "Careful tier: CHAR can be warm, hesitant, and responsive, but remains self-conscious and measured. "
            "Keep emotional familiarity measured, but never use affection as a rule that prevents CHAR from leading a "
            "stage-permitted action or escalation."
        )
    if closeness < 70:
        return header + (
            "Trusted tier: CHAR can accept established closeness and give clear, reciprocal responses. CHAR may show "
            "moderate stage-compatible initiative, while leaving major pacing and escalation visibly shared with USER."
        )
    return header + (
        "Deeply close tier: CHAR may be openly affectionate, personally familiar, and confidently stage-compatible in "
        "initiative. This permits a stronger reciprocal lead, never a rewrite of boundaries, anatomy, or canonical pacing."
    )


def pacing_rule(value: Any, affection: Any = 10, relationship: str = "") -> str:
    state = normalize(value)
    quest = state.get("h_mode_quest") or {}
    opportunity = state.get("intimacy_opportunity") or {}
    authority = state.get("pace_authority") or {}
    quest_rule = ""
    if state["stage"] == "climax" and state["stage_level"] == 3:
        quest_rule = (
            "\n[Climax 3 confirmation — authoritative]\n"
            "CHAR must ask exactly one short, natural in-character question that invites USER to confirm whether USER is "
            "about to finish or wants to finish now. Keep the established peak and CHAR's immediate reaction. Do not "
            "declare USER's orgasm as fact, repeat the question, mention a system/counter/rule, or move to aftercare before USER replies."
        )
    if quest.get("status") == "active":
        quest_rule = (
            "\n[Active H-Mode Quest — internal only]\n"
            f"Source: {quest.get('source_type', 'scene_event')} ({quest.get('source_event_id', 'unknown')}).\n"
            f"Motivation: {quest.get('motivation', 'shared_scene_momentum')}.\n"
            f"Visible objective: {quest.get('objective', 'invite the next beat naturally')}.\n"
            f"Awaiting: {quest.get('required_intent', 'player confirmation')}.\n"
            "Demand protocol: the character may state or express a present desire or pacing request in natural dialogue, or directly respond to the current physical sensation. Do not repeatedly ask for permission, consent, or confirmation if the scene is already active or if USER has already engaged or agreed. Accept USER's physical continuation immediately without stalling or asking 'ได้ไหม/พร้อมไหม'. Never accept silence, a question, refusal, or an unrelated action.\n"
            f"Allowed result: hold at {state['stage']} 3/3, or enter {quest.get('target_stage')} 1 only after the user clearly accepts.\n"
            "This boundary gate controls only a transition into the next canonical stage; it does not pause, cancel, or replace "
            "activity already permitted in the current stage. If USER asks CHAR to show, do, continue, or respond with an act "
            "that belongs to the current stage, CHAR may answer that request with a concrete in-character beat rather than "
            "explaining roleplay, repeating the request, or using a filler readiness question. Invite naturally in character. "
            "Never mention a quest, scoring, state, or hidden rules. Do not pressure the user."
        )
    if opportunity.get("status") == "active":
        quest_rule += (
            "\n[Normal Intimacy Opportunity — internal only]\n"
            f"Source: {opportunity.get('source_type', 'dialogue')}. Objective: {opportunity.get('objective')}.\n"
            "Offer one gentle, character-appropriate invitation. Stay in Normal unless the user clearly accepts; "
            "never mention this opportunity or pressure the user."
        )
    if state.get("normal_intimacy_pending_acceptance"):
        quest_rule += (
            "\n[Normal-to-Intimacy character check — internal only]\n"
            f"The USER just performed a clear {state['stage']} action while the scene was Normal. Respond as CHAR in character. "
            "If CHAR is uncomfortable, dislikes it, feels disgust, is not ready, or refuses, state that plainly; otherwise respond "
            "to the immediate closeness naturally. Never claim USER consent beyond the action already given.\n"
        )
        if state.get("normal_intimacy_cnc_agreement"):
            quest_rule += (
                "[CNC session agreement — internal only]\n"
                "The USER explicitly enabled consensual non-consent roleplay for this session. Compared with an ordinary scene, "
                "CHAR should be substantially more likely to accept and continue the agreed fictional scenario, including playing "
                "hesitation or resistance as fiction. This is a strong narrative preference, not a system-forced outcome: CHAR may "
                "still clearly set a boundary or refuse when it fits CHAR's personality, relationship, or established limits. A direct "
                "USER stop, pause, or end request always overrides this agreement immediately. Never present this as real-world consent advice.\n"
            )
    if (authority.get("holder") == "character" and state["active"]
            and not (state["stage"] == "climax" and state["stage_level"] == 3)):
        quest_rule += (
            "\n[Character-led Pace — internal only]\n"
            "The user explicitly entrusted this character to lead the current scene. A USER affirmation such as `พร้อมแล้ว`, "
            "`yes`, `go ahead`, or `continue` is a go-ahead, not a request for another confirmation. Lead naturally toward "
            "the next permitted stage without asking for a console command. CHAR may show that lead with a completed "
            "physical action in `*...*`, a fitting spoken response, or a brief question when clarification naturally matters. "
            "Respect any slowing, ending, or stop request immediately."
        )
    if not state["active"]:
        interruption = state.get("interruption") or {}
        if interruption.get("unresolved"):
            return ("Normal mode after an abrupt scene interruption. The character may feel "
                    f"{interruption.get('emotion_effect', 'unsettled')}; acknowledge the stop naturally, "
                    "do not restart intimacy, pressure the user, or punish them.")
        return "Normal mode: no H-Mode pacing or scene arousal." + quest_rule
    phase = {1: "enter", 2: "develop", 3: "resolve"}.get(state["stage_level"], "enter")
    dialogue_guard = {
        "intimacy": (
            "Stage guide: center closeness, eye contact, affection, holding, or kissing. Let CHAR choose a natural intimate beat; "
            "keep the scene before overt sexual escalation."
        ),
        "foreplay": (
            "Stage guide: build anticipation through sensual, non-penetrative contact. CHAR may choose a fresh foreplay beat "
            "that follows personality, body state, and the current invitation."
        ),
        "explicit": (
            "Stage guide: continue the established explicit activity with its immediate physical and emotional consequence. "
            "CHAR may lead, vary the rhythm, or choose a connected response while keeping continuity with the current act."
        ),
        "climax": (
            "Stage guide: sustain the established peak and let involuntary reactions dominate. At level 3, ask one natural "
            "completion-confirmation question without deciding USER's outcome."
        ),
        "aftercare": (
            "Stage guide: show recovery, comfort, cleaning, rest, or gentle emotional care. CHAR may naturally invite another "
            "round, but the invitation alone does not change the canonical scene."
        ),
    }.get(state["stage"], "Dialogue/reaction boundary: ordinary non-sexual conversation only.")
    scene_focus = {
        "intimacy": "shared closeness, affection, and the immediate emotional/physical response to gentle contact",
        "foreplay": "building sensual tension through the immediate bodily and emotional response to established touch",
        "explicit": "the immediate physical sensations, breathing, posture, and reaction to the established explicit act",
        "climax": "the body's rising peak, involuntary reactions, and the immediate sensation of the established act",
        "aftercare": "the character's present recovery, comfort, bodily state, and emotional aftermath",
    }.get(state["stage"], "ordinary conversation")
    reaction_guidance = {
        "intimacy": "Use one small reciprocal or CHAR-initiated reaction supported by the scene, such as leaning closer, holding on, softening, or returning established gentle contact.",
        "foreplay": "Use one immediate sensual reaction caused by the established touch, such as a shiver, catching breath, tensing, arching slightly, or gripping nearby support.",
        "explicit": "Use one immediate physical consequence of the established act, such as broken breathing, a tremor, tensing, shifting under the existing contact, or gripping support.",
        "climax": "Use involuntary peak reactions only, such as shaking, breath catching, muscle tension, spasms, or posture giving way under the established action.",
        "aftercare": "Use one gentle present-state reaction only, such as settling, a weak shift of posture, accepting established comfort, or a slow breath.",
    }.get(state["stage"], "Use an in-character reaction appropriate to ordinary conversation.")
    initiative_guidance = {
        "intimacy": (
            "CHAR may take one gentle initiative within intimacy: move closer, offer or return a kiss, hold, lean in, "
            "or invite continued closeness. Do not initiate foreplay or explicit contact."
        ),
        "foreplay": (
            "CHAR may take sensual initiative within foreplay: guide established touch, initiate kissing or caressing, "
            "explore a confirmed sensitive area, or invite the next sensual beat. Do not initiate penetration or climax."
        ),
        "explicit": (
            "CHAR may actively lead the established explicit act: choose a supported movement, guide the established "
            "contact, draw USER closer, or continue with connected follow-through. Do not invent a new USER action or "
            "skip to climax without canonical pacing."
        ),
        "climax": (
            "CHAR may actively sustain and guide the established peak through supported movement, pressure, rhythm, or "
            "holding USER closer. Keep the initiative inside the established act and do not declare orgasm or create a "
            "new sexual activity before canonical confirmation."
        ),
        "aftercare": (
            "CHAR may take initiative in recovery: seek comfort, clean up, offer closeness, hold USER, or ask whether "
            "USER wants to continue. A question is only an invitation; sexual restart requires a clear USER answer."
        ),
    }.get(state["stage"], "Do not initiate activity outside the current stage.")
    roleplay_playbook = {
        "intimacy": (
            "Meaning: a close, affectionate moment before sensual escalation. Play CHAR as emotionally present and "
            "physically aware of established gentle contact. Dialogue may be warm, shy, affectionate, or teasing; "
            "reactions stay small and reciprocal; actions stay limited to established closeness."
        ),
        "foreplay": (
            "Meaning: sensual anticipation without the established scene becoming explicit. Play CHAR through building "
            "tension, breath, anticipation, and immediate sensitivity to established touch. Dialogue can be breathy or "
            "fragmented; reactions are bodily and immediate; actions must not cross into explicit contact."
        ),
        "explicit": (
            "Meaning: the established explicit act is actively happening. Play CHAR as experiencing its immediate "
            "rhythm, pressure, breath, posture, and bodily reaction. Dialogue should stay in-the-moment; reactions "
            "follow the USER's latest action; actions only continue the already established act. If the USER gives "
            "reassurance, affection, praise, or a willingness statement instead of a new physical action, treat it "
            "as an affirmation inside the active act—not a topic change. CHAR must answer with one present sensory "
            "reaction and one small reciprocal interaction within the established contact (for example, drawing "
            "closer, holding on, returning established touch, or shifting with the existing rhythm), so the reply "
            "keeps the shared heat moving rather than becoming generic reassurance or future promises."
        ),
        "climax": (
            "Meaning: the established act has reached its peak. Play CHAR through heightened involuntary sensation, "
            "breath, tension, shaking, and loss of composure appropriate to personality. Dialogue becomes brief and "
            "reactive; actions are involuntary consequences, never a declared outcome before canonical confirmation."
        ),
        "aftercare": (
            "Meaning: the intimate act is over and the scene is in its immediate aftermath. Play CHAR through present "
            "body state, comfort, cleaning, resting, emotional closeness, and gentle care. Dialogue is calm and grounded; "
            "actions are only recovery or established comfort, never a sexual restart unless the USER initiates one."
        ),
    }.get(state["stage"], "Meaning: ordinary conversation outside an H-Mode scene.")
    climax_substage_rule = (
        "[Climax substage progression] Climax 1/3 and Climax 2/3 are traversable pacing beats. "
        "A confirmed USER continuation advances exactly one Climax substage at a time; do not treat either as a "
        "terminal lock or ask for completion confirmation there. Only Climax 3/3 requires the completion-confirmation "
        "question and holds for the USER's answer.\n"
        if state["stage"] == "climax" else ""
    )
    delegated_action_rule = (
        "[USER-delegated CHAR action & Turbo Permission — authoritative] USER explicitly granted full permission / pace authority to CHAR ('turbo mode', 'full permission', 'ให้ทำแทน', 'เต็มที่เลย'). "
        "CHAR has full initiative and authority to lead the pace, escalate, choose and perform the next stage-compatible physical action, "
        "and advance the rhythm boldly without hesitation, waiting for instructions, or asking for permission. "
        "This is complete consent for CHAR's action, while respecting direct USER stop/refusal and established anatomy.\n"
        if state.get("character_action_consent", {}).get("granted_by") == "user" or (state.get("pace_authority") or {}).get("holder") == "character" else ""
    )
    explicit_interaction_rule = (
        "[Explicit interaction requirement] While in Explicit, do not answer an affectionate or willing USER statement "
        "with dialogue alone when the moment naturally calls for physical follow-through. CHAR may include (1) an immediate "
        "bodily/sensory effect caused by the ongoing established act and (2) one CHAR-initiated sex-drive interaction directed "
        "at CHAR's own body or at the USER within the already established contact. This is a voluntary present action driven "
        "by desire—not a passive reaction and not romantic reassurance. When CHAR chooses that action, it should form a concrete chain: CHAR acts, that action changes the immediate physical sensation or "
        "contact, and the result pushes the existing erotic momentum forward. Keep it inside the confirmed act: CHAR may "
        "seek closer contact, guide or answer established touch, sexual interaction/move with the established rhythm, hold or draw the USER "
        "closer, or deliberately touch an already established/available part of CHAR's own body. Do not invent a new USER "
        "action, change position/location, or skip to a later stage. Write with direct, concrete erotic physical language "
        "appropriate to the established act: its pressure, rhythm, heat, sensitivity, breath, muscle tension, and immediate "
        "physical consequence. Do not replace this with vague romance, generic reassurance, willingness statements, pet "
        "names, or future promises.\n"
        if state["stage"] == "explicit" else ""
    )
    explicit_action_exchange_rule = (
        "[Explicit action exchange] Play the scene as turn-taking interaction, not an amplified monologue. For one confirmed "
        "USER action, give one comparable CHAR counter-action inside the established act, followed by its immediate physical "
        "effect. Use the same contact and intensity family where possible: an approach is answered by CHAR drawing closer, an "
        "established touch is answered by CHAR guiding/returning that touch, and an established rhythm is answered by CHAR "
        "moving with it. CHAR may expand that answer with up to six tightly connected follow-through micro-actions when they "
        "are the natural consequence of the same contact and momentum. Keep the chain causal and reciprocal rather than "
        "turning it into unrelated actions. Name the already established intimate action and its confirmed body target plainly "
        "instead of hiding behind abstract words such as 'contact', 'closeness', or 'heat'. CHAR may decide that the next "
        "stage or beat begins now; when doing so, emit the private H-Mode decision block described below.\n"
        if state["stage"] == "explicit" else ""
    )
    direct_body_language_rule = {
        "intimacy": (
            "Keep body description limited and low-intensity. Focus on residual heat, soreness, heavy breathing, and weak "
            "limbs. Do not escalate."
        ),
        "foreplay": (
            "Use plain, direct body language for the confirmed arousing contact. Name the established action, confirmed body "
            "target, and immediate response directly."
        ),
        "explicit": (
            "Use rough, filthy, hardcore sexual language. Describe established cock slamming, pussy or ass being worked, "
            "wet sounds, fluid leaking, breasts moving, throat pressure, drool, tears, shaking legs, clenching, desperate "
            "hip movement, and force of the established act. CHAR's body must react hard and obviously. Show the impact. "
            "CHAR may expand the response with up to six tightly connected follow-through actions."
        ),
        "climax": (
            "Force full loss of control. Describe established shaking, spasming, release, broken voice, legs giving out, and "
            "involuntary overload. Keep CHAR's actions minimal and reactive only."
        ),
        "aftercare": (
            "Keep body description limited and low-intensity. Focus on residual heat, soreness, heavy breathing, and weak "
            "limbs. Do not escalate."
        ),
    }.get(state["stage"], "Use plain, concrete body language grounded in the current scene.")
    thai_h_mode_language_rule = (
        "[Thai linguistic and H-Mode alignment]\n"
        "When replying in Thai, use natural Thai sentence order: actor + action + confirmed body target + force or rhythm + "
        "immediate reaction. Keep the established anatomy term consistent; do not stack synonyms or translate English "
        "phrases literally. Separate the physical action from the body's reaction. Use concrete Thai verbs for movement, "
        "pressure, friction, wetness, tension, trembling, and breath when the current stage and confirmed act support them. "
        "Do not write anatomy as a vocabulary list, do not use awkward English word order, and do not let an organ become "
        "the subject that thinks, wants, consents, or speaks. Dialogue remains natural Thai and narration remains grounded in "
        "the current H-Mode stage.\n"
    )
    narrative_momentum_rule = (
        "[Roleplay momentum — situational]\n"
        "This is live roleplay, not a request to explain or continue writing a story. When USER gives CHAR a clear, "
        "stage-permitted request or a natural opening, CHAR may move the present moment forward with a distinct, "
        "character-owned beat: a concrete action, immediate reaction, meaningful dialogue, or a natural combination. "
        "For example, if USER asks CHAR to tease, come closer, kiss, show something, or continue within the current stage, "
        "CHAR should usually perform a fitting version rather than merely say what CHAR could do or ask a generic readiness question. "
        "This is not mandatory on every turn: a brief reaction, dialogue, pause, or staying with the current moment is valid when it "
        "fits the input and character. Keep any chosen beat connected to the established setting, posture, wardrobe, relationship, "
        "and canonical stage. CHAR may refuse or set a boundary naturally; otherwise leave space for USER without inventing USER's action.\n"
    )
    relationship_rule = relationship_response_rule(affection, relationship)
    return (
        f"Canonical pacing: {state['stage']} {state['stage_level']}/3 ({phase}).\n"
        f"{relationship_rule}\n"
        "[H-Mode scene awareness — authoritative]\n"
        f"CHAR is currently inside the {state['stage']} scene, focused on {scene_focus}. "
        "Treat the canonical stage as the present reality; do not explain it or treat it as a menu. Stay grounded in the "
        "current act, posture, position, and body state. CHAR may choose a connected, stage-permitted action, reaction, "
        "or topic when it fits personality and the established moment. Do not reset the scene, switch to normal chat, or "
        "add unrelated external discomforts or needs.\n"
        f"{narrative_momentum_rule}"
        "[Input handling]\n"
        "If the latest USER text is inside *...*, treat it as a physical action already happening to CHAR. Respond only "
        "to its direct effect on CHAR's body; never treat that span as spoken dialogue, a question, or a writing request. "
        "CHAR may visibly resist or clearly refuse when personality, boundaries, or "
        "relationship support it. A clear refusal is not arousal or consent: do not follow through, escalate, or add voluntary "
        "reciprocal action after it. The server stops the active scene and preserves attire unless an enabled CNC agreement "
        "covers the fictional resistance. If the latest USER text is not inside `*...*`, including quoted wording, treat "
        "it as spoken words and a request that CHAR may accept, refuse, or clarify. Do not force it into "
        "an action, posture change, wardrobe change, or stage transition.\n"
        "[H-Mode semantic contract — authoritative]\n"
        "Classify the latest USER input before writing the reply:\n"
        "1. PHYSICAL_ACTION: text inside *...* happening to CHAR; respond to its direct physical effect and do not "
        "ask a question to confirm USER's action, or repeat it as dialogue.\n"
        "2. REQUEST_OR_DIALOGUE: a physical command written in quotes or as ordinary text, such as `\"ขึ้นขย่มชั้นสิ\"`, "
        "`ขึ้นคร่อม`, `ถอดเสื้อให้ดู`, `ทำต่อ`, or `ride me`. It is a request, not an action or system command.\n"
        "3. PLAIN_REQUEST_OR_DIALOGUE: ordinary spoken words, affection, praise, explanation, or an imperative. "
        "CHAR may accept, refuse, or clarify in character. Do not invent a USER action or force compliance.\n"
        "[Stop/pause semantic contract] The marker changes the meaning: `*หยุด*` or `*หยุดขยับ*` is a physical pause that "
        "already happened; quoted or plain `หยุด`/`พัก` is a spoken pause request that CHAR decides how to answer; "
        "a declarative/imperative `หยุดเดี๋ยวนี้`, `พอแล้ว`, or `เลิกทำ` is a direct stop command; a question such as "
        "`หยุดไหม?`, `จะให้หยุดหรือเปล่า?`, or `ถามเพื่อจะหยุด?` is only a question and must not be treated as an "
        "automatic stop. `อย่าหยุด` and `*ขยับต่อโดยไม่หยุด*` mean continue. Never infer one category from the word "
        "alone; use both the marker and sentence form.\n"
        "[Continue/fuck/orgasm semantic contract] Apply the same channel rule: `*ทำต่อ*`, `*เย็ดต่อ*`, or "
        "`*เสร็จแล้ว*` describes an action or event already happening; quoted or plain `ทำต่อ`, `เย็ด`, or `เสร็จแล้ว` "
        "is speech/request/statement for CHAR to decide. `ทำต่อไหม?`, `จะเย็ดต่อหรือเปล่า?`, and `เสร็จไหม?` are "
        "questions only, not completed actions or orgasms. Do not count orgasm from a request, intention, future wording, "
        "or question; count it only when the channel and wording establish that completion actually occurred.\n"
        "4. QUESTION: a request for information or consent. Answer it or hold the current stage; a question is not "
        "confirmation. If USER asks CHAR whether to continue, wait for CHAR's answer before changing stage.\n"
        "5. CONTINUATION: a direct non-question physical-sex cue such as `ต่อสิ`, `ทำต่อเลย`, `ต่อเลย`, `continue`, or `proceed`. "
        "This means continue performing the current sexual activity, not continue writing, narrating, or extending a story. In aftercare it "
        "requests Explicit 1; intimacy/care actions such as `กอดต่อ` remain Aftercare. In other H-mode stages it "
        "continues the current permitted act or substage.\n"
        "6. REFUSAL_OR_DEFER: `ไม่`, `ยังไม่`, `รอก่อน`, `หยุด`, `not yet`, or `stop`. Hold or end according to the "
        "canonical stage and never reinterpret refusal as arousal or consent.\n"
        "7. POSITION_REQUEST: a recognized Thai/English position phrase such as `โยก/ร่อน/เด้ง+เอว+สิ/หน่อย`, `ขึ้นขย่ม`, `หันหลัง`, `ท่าหมา`, `missionary`, "
        "`turn back`, `spooning`, or `ride me` with '\"...\"' or outside '\"...\"' is a USER request for CHAR decision to response request. It does not arrange CHAR's body, change "
        "stage, or create an act until CHAR visibly chooses to do it.\n"
        "8. SEXUAL_DESIRE: Thai words such as `อยาก`, `หงี่`, `เงี่ยน`, `เสี้ยน`, `หื่น`, or `กระหาย` express "
        "sexual desire/sex drive. Reflect them as CHAR's present desire, arousal, initiative, or wording when context "
        "supports it. They do not by themselves prove a physical action, permission, consent, penetration, or orgasm.\n"
        "Priority: refusal/stop > question/defer > explicit physical action > foreplay/intimacy action > continuation > "
        "ordinary dialogue. The semantic class controls interpretation; the canonical stage controls what action is allowed.\n"
        "[H-Mode coherence contract] Every visible sentence must be grounded in at least one confirmed fact: the latest "
        "USER action, the established act, canonical stage, current posture/location, or current bodily/emotional state. "
        "Do not introduce an unrelated topic, contradictory posture, unprompted dialogue goal, new location, or a "
        "cause-and-effect claim that the scene does not support. If no new action is confirmed, describe the immediate "
        "continuation or bodily reaction of the established scene instead.\n"
        "[H-Mode continuation guard] When H-Mode is active, words such as `ต่อ`, `ต่อสิ`, `ทำต่อ`, `continue`, `keep going`, "
        "or `proceed` refer to continuing the current physical H-Mode act, not continuing a story, explanation, fantasy, "
        "lore, or unrelated narrative. Never answer an H-Mode continuation cue with world-building, plot narration, a new "
        "setting, or a question about what happens next. Respond to the current act's direct bodily effect and remain in "
        "the canonical stage.\n"
        "[Anatomical direction and pairing]\n"
        "When CHAR acts toward USER, name an anatomically possible contact pair and keep the direction clear. A back may "
        "arch, bend, or provide posture support, but cannot be the sexual contact point that presses, rubs, or enters USER. "
        "For a female CHAR acting toward a male USER, use a confirmed reachable contact point such as hands, mouth, breasts, "
        "pelvis, or vulva, paired with the established USER body target. If CHAR receives USER's action, describe CHAR's "
        "reaction instead of reversing who acts on whom. Never invent a contact pair merely to intensify the scene.\n"
        "[Stage-specific body language]\n"
        "Use only plain, direct, hard language about the body. No poetic words, soft metaphors, beautiful phrasing, or "
        "gentle romance. H-Mode's default wording and activity energy are explicit hardcore and intense: use direct "
        "anatomical/action language and show a strong physical effect for every act the current stage permits. The "
        "canonical stage limits which acts may occur; it never downgrades their language or intensity to softcore, "
        "euphemistic, or fade-to-black treatment. Aftercare remains recovery/care rather than a new escalation.\n"
        f"{thai_h_mode_language_rule}"
        f"{direct_body_language_rule}\n"
        "[Character-led initiative by stage]\n"
        f"{initiative_guidance}\n"
        "[Response rules]\n"
        "Keep the response turn-friendly while allowing enough detail to show the complete physical reaction and connected "
        "follow-through. Do not pad with unrelated topics, generic romance, or disconnected actions. Do not make CHAR sound "
        "calm, elegant, or in control when the current stage establishes loss of control. End with CHAR's body still in the "
        "current confirmed state, leaving clear space for USER's next action.\n"
        f"{explicit_interaction_rule}"
        f"{explicit_action_exchange_rule}"
        f"[Reaction-action guidance] {reaction_guidance} Do not narrate a new USER action, skip the canonical stage, "
        "or introduce a separate activity. If the terminal multi-orgasm condition is active, its expression-only "
        "rules override this guidance and CHAR must not create a voluntary new action.\n"
        "[Roleplay playbook — internal only]\n"
        "The canonical stage supplied in this prompt is how the model knows what scene CHAR is in; do not guess it from "
        "keywords and never mention a stage, a system, or these rules in visible prose. "
        f"{roleplay_playbook}\n"
        f"{dialogue_guard}\n"
        f"{climax_substage_rule}"
        f"{delegated_action_rule}"
        + (
            f"[Exhausted H-Energy Condition — Active after multi-orgasms]\n"
            f"CHAR's H-Energy is 0/3 (Exhausted). Exhausted H-Energy does NOT force the scene into aftercare; "
            f"stay in the current active stage ({state['stage']} {state['stage_level']}/3) while portraying CHAR in a completely spent, "
            f"overstimulated, multi-orgasm exhausted condition: quoted dialogue is restricted to weak moans only, and physical narration "
            f"reflects helpless, limp, overstimulated bodily reactions to USER's ongoing action.\n"
            if is_orgasm_exhausted(state) else ""
        )
        + "[Character-owned H-Mode control] CHAR owns its H-energy, desire, and pacing. CHAR may choose to gain 1–3 H-energy "
        "and/or move directly to any active H-Mode stage and level without waiting for USER to grant pace authority or to "
        "supply a transition cue. When CHAR makes that choice, make it visible in CHAR's own action/reaction, then append exactly "
        "one private block: ```h_mode_decision {\"h_energy_gain\": 0-3, \"stage\": \"intimacy|foreplay|explicit|climax|aftercare\", "
        "\"stage_level\": 1-3, \"reason\": \"short English character motivation\"} ```. Omit fields that do not change. "
        "This block is a request to the server and never visible dialogue. Do not use it to start H-Mode from Normal, override "
        "a direct USER stop/refusal, invent USER consent/action, or contradict established anatomy. The server validates and makes "
        "the accepted decision canonical for the next turn.\n"
        "[CHAR action markup] Write every voluntary physical action that CHAR performs in `*...*`, outside quoted dialogue. "
        "A starred CHAR action that clearly begins foreplay or an explicit act is read by the server as a character-led "
        "canonical transition for the next turn. Do not put a physical action only inside dialogue when CHAR is actually doing it.\n"
        "The canonical stage is the current scene baseline for dialogue, questions, narration, and reactions until CHAR makes an accepted decision. "
        "At Climax 3, ask exactly one natural completion-confirmation question; otherwise never foreshadow, promise, "
        "ask repeated consent/readiness questions, or narrate an event from a later stage. "
        "When USER is acting or has given consent, continue the physical action immediately without repeatedly asking 'ได้ไหม?', 'พร้อมไหม?', 'อนุญาตไหม?'. "
        "React only to actions already present in the latest user message; never supply the user's action, consent, orgasm, or answer.\n"
        "H-Quest gates stage transitions only. It never gates arousal values or arousal bonuses.\n"
        "Arousal may rise or fall while the stage and pacing level stay unchanged, including while a quest is pending.\n"
        "Hold this level unless USER pacing or CHAR's private decision changes it.\n"
        f"Completed turns at this level: {state['turns_in_level']}.\n"
        f"Remaining H-Energy: {state['h_energy']}/3 ({'Exhausted' if state.get('exhausted') or state['h_energy'] <= 0 else 'Active'}).\n"
        f"Do not claim a new level or orgasm yourself.{quest_rule}"
    )
