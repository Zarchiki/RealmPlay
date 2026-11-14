"""Relationship-aware Thai forms of address for visible roleplay dialogue."""
from __future__ import annotations

import re
from typing import Any, Dict, Tuple


AFTERCARE_AFFECTION_BONUS = 5
THIRD_ORGASM_AFFECTION_PENALTY = 10
H_MODE_STAGE_AFFECTION_BONUSES = {"intimacy": 1, "foreplay": 1, "explicit": 1}


def affection_value(status: str, default: int = 10) -> int:
    """Read the durable Affection score from a Status snapshot (-100 to 100)."""
    # Supports 'Affection: 23 / 100', 'Affection: (85/100)', 'Affection Level: (13)', '- Affection: -10'
    matches = re.findall(r"(?im)^\s*-?\s*Affection(?:\s*Level)?\s*:\s*\(?(-?\d{1,3})", status or "")
    if not matches:
        return max(-100, min(100, int(default)))
    return max(-100, min(100, int(matches[-1])))


def aftercare_affection(status: str, previous_status: str, stage: str, user_text: str) -> str:
    """Award recovery turns affection from the saved value, once per reply."""
    if stage != 'aftercare' or not (user_text or '').strip():
        return status
    if re.search(r'หยุดเดี๋ยวนี้|ไม่เอาแล้ว|\b(?:stop now|no more)\b|/pace stop', user_text, re.I):
        return status
    pattern = r'(?im)^(\s*-?\s*Affection(?:\s*Level)?\s*:\s*)(-?\d+)'
    previous = re.search(pattern, previous_status or '')
    current = re.search(pattern, status or '')
    source = previous or current
    if not source:
        return status
    value = min(100, max(-100, int(source[2]) + AFTERCARE_AFFECTION_BONUS))
    if current:
        return re.sub(pattern, lambda m: m[1] + str(value), status, count=1)
    return status.rstrip() + f'\n- Affection: {value}/100'


def h_mode_stage_affection(
    status: str, previous_status: str, stage: str, user_text: str, reply: str,
    *, cnc_agreement: bool = False,
) -> str:
    """Award a small mutual-connection bonus in eligible H-Mode stages.

    This is intentionally not a reward for sexual activity by itself. It needs
    a positive stage-relevant USER cue and a CHAR reply without an objection.
    CNC scenes never earn this automatic relationship bonus.
    """
    stage_key = str(stage or "").casefold()
    bonus = H_MODE_STAGE_AFFECTION_BONUSES.get(stage_key, 0)
    if not bonus or cnc_agreement:
        return status
    user_words = str(user_text or "").casefold()
    reply_words = str(reply or "").casefold()
    if not user_words or not reply_words:
        return status
    objection = r"ไม่พร้อม|ไม่เอา|ไม่อยาก|หยุด|ถอย(?:ออก|ไป)?|ปฏิเสธ|รังเกียจ|อึดอัด|\b(?:stop|no|not comfortable|don.t want)\b"
    if re.search(objection, user_words, re.I) or re.search(objection, reply_words, re.I):
        return status
    positive_patterns = {
        "intimacy": r"กอด|จูบ|อ้อน|อิง|พิง|จับมือ|ลูบหัว|บอกรัก|พูดหวาน|ใกล้ชิด|\b(?:hug|kiss|cuddle|hold hands|love)\b",
        "foreplay": r"เล้าโลม|ปลุก(?:อารมณ์|เร้า)|จูบไล้|ลูบไล้|คลอเคลีย|สัมผัส.*(?:หน้าอก|หัวนม|ก้น)|\b(?:foreplay|tease|caress|arouse)\b",
        # Explicit only earns relationship progress when the turn also has a
        # clear voluntary/affectionate signal, not from the act alone.
        "explicit": r"พร้อม|ยินดี|ตกลง|อนุญาต|ยินยอม|ได้สิ|ได้เลย|ขอบคุณ|ชม|น่ารัก|รัก|ไว้ใจ|อ่อนโยน|\b(?:ready|willing|yes|thank|praise|love|trust|gentle)\b",
    }
    if not re.search(positive_patterns[stage_key], user_words, re.I):
        return status
    pattern = r'(?im)^(\s*-?\s*Affection(?:\s*Level)?\s*:\s*)(-?\d+)'
    previous = re.search(pattern, previous_status or "")
    current = re.search(pattern, status or "")
    source = previous or current
    if not source:
        return status
    value = min(100, max(-100, int(source[2]) + bonus))
    if current:
        return re.sub(pattern, lambda match: match[1] + str(value), status, count=1)
    return status.rstrip() + f'\n- Affection: {value}/100'


def third_orgasm_affection_penalty(status: str, previous_status: str, scene: dict) -> str:
    """Deactivated: Orgasm in H-Mode roleplay does not penalize affection."""
    return status


def apply_relationship_progression(
    status: str,
    user_message: str = "",
    assistant_reply: str = "",
) -> Tuple[str, int, str, str]:
    """Autonomously detect emotional cues, adjust affection (-100 to 100), and elevate/degrade dynamics."""
    status_str = status or ""
    current_aff = affection_value(status_str, default=10)

    # Read current Relationship Dynamic
    rel_match = re.search(r"(?im)^\s*-?\s*Relationship(?:\s*Dynamic)?\s*:\s*([^\r\n]+)", status_str)
    current_rel = rel_match.group(1).strip() if rel_match else "Acquaintance"

    # Read current Relationship Type
    type_match = re.search(r"(?im)^\s*-?\s*Relationship\s*Type\s*:\s*([^\r\n]+)", status_str)
    current_type = type_match.group(1).strip() if type_match else "Peers / Neutral"

    dialogue = f"{user_message}\n{assistant_reply}".casefold()

    delta = 0
    char_reply_folded = str(assistant_reply or "").casefold()

    # Rule: เมื่อตัวละคร กล่าว/กระทำ ยิ้มให้ หรือ เชยชม ขอบคุณ ให้เพิ่ม +2 affection bonus
    char_appreciation_bonus = bool(re.search(
        r"ยิ้มให้|ยิ้มรับ|ส่งยิ้ม|แย้มยิ้ม|ยิ้มหวาน|ยิ้มมุมปาก|ยิ้มบาง|ยิ้มละมุน|"
        r"ขอบคุณ|ขอบใจ|เชยชม|ชื่นชม|ชมเชย|ชมว่า|เอ่ยชม|"
        r"\b(?:smile[sd]?|smiling|thank(?:s|ed|ing)?|grateful|praise[sd]?|praising|compliment(?:ed|ing)?)\b",
        char_reply_folded,
    ))
    if char_appreciation_bonus:
        delta += 2

    # Positive triggers: care, compliment, vulnerability, warmth, comfort, sharing
    if not char_appreciation_bonus and re.search(
        r"ห่วง|ชอบ|น่ารัก|กอด|ลูบหัว|ใจดี|อ่อนโยน|ไว้ใจ|ใกล้ชิด|อบอุ่น|ดีใจ|"
        r"comfort|care|hug|warmth|love|trust|gentle|sweet|precious|kind",
        dialogue,
    ):
        delta += 1

    # Deep emotional milestones / romantic confession
    if re.search(
        r"รักนะ|เป็นแฟนกัน|คนสำคัญ|สัญญาว่าจะอยู่ด้วย|รักเธอ|ชอบที่สุด|"
        r"confess|forever|special to me|my love|sweetheart|i love you",
        dialogue,
    ):
        delta += 3

    # Negative triggers & Affection Deductions:
    # 1. Coldness, annoyance, pushing away (-2)
    if re.search(
        r"รำคาญ|อย่ามายุ่ง|ไม่ว่าง|ไร้สาระ|เงียบไป|ไปไกลๆ|ถอยไป|ห่างๆ หน่อย|"
        r"annoying|bother|leave me|go away|stay away|back off|nonsense",
        dialogue,
    ):
        delta -= 2

    # 2. Harsh rejection, verbal hostility, insulting (-5)
    if re.search(
        r"เกลียด|ไสหัวไป|น่ารังเกียจ|ทุเรศ|ไม่ชอบหน้า|ปากดี|หุบปาก|โง่|ไร้ค่า|"
        r"hate|disgust|repulsive|shut up|idiot|fool|useless|pathetic|despise",
        dialogue,
    ):
        delta -= 5

    # 3. Severe breach of trust, betrayal, physical cruelty, coercion (-10)
    if re.search(
        r"ทรยศ|หักหลัง|หลอกลวง|สารเลว|ตายซะ|ฆ่า|ทำร้าย|บังคับ|ขืนใจ|"
        r"betray|traitor|deceive|scumbag|bastard|die|kill|harm|force|abuse",
        dialogue,
    ):
        delta -= 10

    new_aff = max(-100, min(100, current_aff + delta))

    # Autonomous relationship dynamic mapping based on affection thresholds (-100 to 100)
    new_rel = current_rel
    new_type = current_type

    is_custom_role = bool(re.search(r"master|servant|เจ้านาย|ข้ารับใช้|นายท่าน", f"{current_rel} {current_type}", re.I))
    if not is_custom_role:
        if new_aff <= -70:
            new_rel = "Bitter Nemesis / Deep Hatred"
            new_type = "Nemesis / Hostile"
        elif new_aff <= -30:
            new_rel = "Hostile & Wary / Resentful"
            new_type = "Hostile / Distant"
        elif new_aff < 0:
            new_rel = "Cold & Distant / Cautious"
            new_type = "Estranged / Cold"
        elif new_aff >= 85:
            new_rel = "Deeply Devoted / Soulmate"
            new_type = "Romantic / Devoted"
        elif new_aff >= 70:
            new_rel = "Lover / Romantic Partner"
            new_type = "Romantic / Lovers"
        elif new_aff >= 45:
            new_rel = "Close Confidant / Very Close"
            new_type = "Close Friends / Confidants"
        elif new_aff >= 20:
            new_rel = "Good Friend"
            new_type = "Friends / Peers"
        elif new_aff >= 10 and current_rel.lower() in ("initial meeting", "acquaintance", "cautious distance"):
            new_rel = "Friendly Acquaintance"
            new_type = "Acquaintance / Peers"
        elif new_aff >= 0 and current_rel.lower() in ("initial meeting", "acquaintance"):
            new_rel = "Initial meeting"
            new_type = "Strangers / Neutral"

    lines = status_str.splitlines()
    cleaned_lines = []
    aff_inserted = False
    rel_inserted = False
    type_inserted = False

    for line in lines:
        if re.match(r"^\s*-?\s*Affection(?:\s*Level)?\s*:.*$", line, re.IGNORECASE):
            if not aff_inserted:
                cleaned_lines.append(f"- Affection: {new_aff} / 100")
                aff_inserted = True
            continue
        if re.match(r"^\s*-?\s*Relationship\s*Type\s*:.*$", line, re.IGNORECASE):
            if not type_inserted:
                cleaned_lines.append(f"- Relationship Type: {new_type}")
                type_inserted = True
            continue
        if re.match(r"^\s*-?\s*Relationship(?:\s*Dynamic)?\s*:.*$", line, re.IGNORECASE):
            if not rel_inserted:
                cleaned_lines.append(f"- Relationship: {new_rel}")
                rel_inserted = True
            continue
        cleaned_lines.append(line)

    if not (aff_inserted and type_inserted and rel_inserted):
        # Insert any missing fields under [Relational & Emotional State] or at end
        final_lines = []
        found_section = False
        for line in cleaned_lines:
            final_lines.append(line)
            if "[Relational & Emotional State]" in line:
                found_section = True
                if not aff_inserted:
                    final_lines.append(f"- Affection: {new_aff} / 100")
                    aff_inserted = True
                if not type_inserted:
                    final_lines.append(f"- Relationship Type: {new_type}")
                    type_inserted = True
                if not rel_inserted:
                    final_lines.append(f"- Relationship: {new_rel}")
                    rel_inserted = True
        if not found_section:
            if not aff_inserted:
                final_lines.append(f"- Affection: {new_aff} / 100")
            if not type_inserted:
                final_lines.append(f"- Relationship Type: {new_type}")
            if not rel_inserted:
                final_lines.append(f"- Relationship: {new_rel}")
        cleaned_lines = final_lines

    updated = "\n".join(cleaned_lines)

    return updated, new_aff, new_rel, new_type


def thai_address(state: Dict[str, Any], display_name: str = "") -> Dict[str, str]:
    """Choose pronoun pair prioritizing explicit Memory, Status, Profile, and Character Summary."""
    profile = str(state.get("character_profile") or "")
    status = str(state.get("status") or "")
    memory = str(state.get("memory") or "")
    char_summary = str(state.get("char_summary") or "")
    combined = f"{memory}\n{status}\n{profile}\n{char_summary}".casefold()
    aff = affection_value(status, default=10)

    # 0. Negative Hostility override (-100 to -1)
    if aff <= -70:
        return {"self": "กู", "user": "มึง", "relationship": "nemesis"}
    if aff < 0:
        return {"self": "ชั้น", "user": "นาย", "relationship": "hostile_distant"}

    # 1. Direct memory / status explicit agreement or instruction
    if re.search(r'แทนตัวเองว่าหนู|ให้เรียก(?:ว่า)?พี่|call (?:her|char|me|himself|herself) ["\']?หนู["\']?|use ["\']?พี่["\']?', combined):
        return {"self": "หนู", "user": "พี่", "relationship": "younger_char_to_older_user"}
    if re.search(r"นายท่าน|คุณท่าน|master|mistress", combined):
        return {"self": "ข้าน้อย", "user": "นายท่าน", "relationship": "service"}
    if re.search(r"พี่{{user}}|พี่\s*คุณ|older than user|older sibling", combined):
        return {"self": "พี่", "user": "น้อง", "relationship": "older_character"}
    if re.search(r"น้อง{{user}}|น้อง\s*คุณ|younger than user|younger sibling", combined):
        return {"self": "น้อง", "user": "พี่", "relationship": "younger_character"}

    # 2. Relationship Dynamic & Affection Progression
    is_lover = bool(re.search(r"คนรัก|แฟน|คู่รัก|สามี|ภรรยา|lover|romantic partner|dating|soulmate", combined))
    if is_lover or aff >= 70:
        return {"self": "เค้า", "user": "ตัวเอง", "relationship": "romantic"}

    # 3. Age heuristics from Char_Summary / Profile (under 18 years old speaking to user)
    age_match = re.search(r"##\s*age\s*\n+([^\n#]+)", combined, re.I)
    age = None
    if age_match:
        m_num = re.search(r"\b(\d{1,3})\b", age_match.group(1))
        if m_num:
            age = int(m_num.group(1))
    if age and age < 18:
        return {"self": "หนู", "user": "พี่", "relationship": "younger_char_to_older_user"}

    # 4. Peer progression by Affection
    if aff >= 45 or re.search(r"close confidant|very close|best friend|สนิทมาก", combined):
        return {"self": "เรา", "user": "นาย", "relationship": "close_friends"}
    if aff >= 15 or re.search(r"good friend|friendly acquaintance|เพื่อน", combined):
        return {"self": "เรา", "user": "นาย", "relationship": "friendly"}

    return {"self": "เรา", "user": "คุณ", "relationship": "neutral"}


def thai_rule(state: Dict[str, Any], display_name: str = "") -> str:
    pair = thai_address(state, display_name)
    named_user = display_name.strip()
    if pair["user"] == "พี่":
        user_reference = f"พี่{named_user}" if named_user else "พี่"
    elif pair["user"] == "น้อง":
        user_reference = f"น้อง{named_user}" if named_user else "น้อง"
    elif pair["user"] in ("ตัวเอง", "นายท่าน", "คุณท่าน", "มึง"):
        user_reference = pair["user"]
    elif pair["user"] == "นาย":
        user_reference = named_user or "นาย"
    else:
        user_reference = named_user or pair["user"]

    return (
        "[Thai Relationship Address]\n"
        f"- Established relationship register: {pair['relationship']}.\n"
        f"- Use \"{pair['self']}\" as the character's self-reference and address the other person as \"{user_reference}\". Keep this pair stable; do not switch to another first-person register mid-scene.\n"
        "- In visible Thai dialogue and narration, never call the other person \"ผู้ใช้\" or \"user\". "
        "Use the established pronoun, a natural title, or their display name when appropriate.\n"
        "- The relationship profile can override this pair when it explicitly establishes a different title or hierarchy."
    )


def normalize_thai_visible_pronouns(text: str, pair: Dict[str, str]) -> str:
    """Keep generated Thai character speech on its selected relationship register.

    State blocks are intentionally left untouched: they are machine data and may
    contain quoted historical facts. The replacement is limited to standalone
    first-person forms the model commonly switches between mid-scene.
    """
    if not text or not pair.get("self"):
        return text

    pieces = re.split(r"(```[\s\S]*?```)", text)
    # Long forms must be handled first before short forms
    forms = ("ข้าพเจ้า", "กระผม", "ดิฉัน", "ฉัน", "ผม")
    target_self = pair["self"]
    if target_self != "หนู":
        forms = forms + ("หนู",)

    for index in range(0, len(pieces), 2):
        for form in forms:
            pieces[index] = pieces[index].replace(form, target_self)
        # Match standalone 'ข้า' only, do NOT touch 'ข้าง' or words with prefix vowels like 'เข้า'
        if target_self != "ข้า":
            pieces[index] = re.sub(r"(?<![เ\u0E00-\u0E7F])ข้า(?!(?:ศึก|พเจ้า|ราชการ|ทาส|[\u0E00-\u0E7F]))", target_self, pieces[index])
    return "".join(pieces)
