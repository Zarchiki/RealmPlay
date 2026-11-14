"""Deterministic arousal arithmetic; the model supplies only scene contribution."""
import re


LEVELS = {"none": 0, "low": 25, "medium": 50, "high": 75, "overwhelmed": 100}
# Penalty indexed by remaining H-Energy after orgasm completion (max 3 -> drops to 2, 1, 0=Exhausted)
H_ENERGY_CLIMAX_PENALTIES = {2: 25, 1: 50, 0: 100}
CLIMAX_PENALTIES = {1: 25, 2: 50, 3: 100}
STAGE_AROUSAL_BONUSES = {
    "intimacy": 3,
    "foreplay": 4,
    "explicit": 5,
    "climax": 6,
}
NORMAL_CHAT_AROUSAL_BONUS = 2
WARDROBE_REMOVAL_AROUSAL_BONUS = 2
SEXY_GIFT_AROUSAL_BONUS = 2
H_ITEM_USE_AROUSAL_BONUS = 5
BASE_OBJECTION_AROUSAL_PENALTY = 5


def is_objection_present(user_text: str = "", reply: str = "") -> bool:
    """Detect whether user or character explicitly objected, rejected, or demanded to stop.
    Distinguishes declarative stop/refusal from:
    - continuation pleas ("อย่าหยุด", "ไม่หยุด", "อย่านะ...อ๊า")
    - questions ("จะหยุดไหม?", "พอแล้ว?", "ให้หยุดเหรอ?")
    - physical motion pauses inside `*...*` (`*หยุดขยับ*`, `*หยุด*`)
    """
    raw_u = str(user_text or "").strip()
    # Strip `*...*` physical actions when checking for verbal objection unless it's a hostile push-away
    speech_u = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)", " ", raw_u, flags=re.DOTALL).casefold()
    action_u = " ".join(re.findall(r"(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)", raw_u, flags=re.DOTALL)).casefold()

    # Remove "อย่าหยุด" / "ไม่หยุด" / "don't stop"
    dont_stop_pat = r"อย่าหยุด|ไม่หยุด|โดยไม่หยุด|หยุดไม่ได้|\b(?:don\W?t\s+stop|do\s+not\s+stop|never\s+stop)\b"
    speech_u = re.sub(dont_stop_pat, " ", speech_u)
    action_u = re.sub(dont_stop_pat, " ", action_u)

    # Remove question clauses from speech_u so asking "หยุดไหม?" / "พอแล้ว?" never counts as an objection
    q_pat = r"\?|ไหม|มั้ย|หรือยัง|รึยัง|หรือเปล่า|หรือไม่|เหรอ|หรือคะ|หรือครับ|\b(?:shall we|should we|would you|do you want to stop)\b"
    non_question_clauses = [
        cl for cl in re.split(r'[\n"“”]|(?<=[.!?।])\s+', speech_u)
        if cl.strip() and not re.search(q_pat, cl)
    ]
    stmt_u = " ".join(non_question_clauses)

    # Check declarative user objection
    if re.search(r"หยุดเดี๋ยวนี้|หยุดทำ|ไม่เอา(?:แล้ว)?|อย่า(?:ทำ|จับ|แตะ|มายุ่ง)|จบฉาก|พอแล้ว|เลิกทำ|\b(?:stop\s+now|stop\s+it|no\s+more|don't\s+touch|end\s+scene)\b", stmt_u):
        return True
    if re.search(r"ผลักออก|สะบัดออก|ขืนตัวหนี|\b(?:push(?:es|ed)?\s+away|shove(?:s|d)?\s+off)\b", action_u):
        return True

    r = re.sub(dont_stop_pat, " ", (reply or "").casefold())
    if r and re.search(r"ถอยไป|อย่าทำแบบนี้|ไม่เอาค่ะ|ไม่เอาครับ|ปฏิเสธ|ผลักออก|ไม่พร้อม|อย่าจับ|รังเกียจ|\b(?:don't touch|stop it|push away|refuse)\b", r):
        # Guard against pleasurable moans ("อ๊า... อย่าแกล้งสิ")
        if not re.search(r"อ๊า|อ๊ะ|อื้อ|เสียว|ซี้ด", r):
            return True
    return False


def objection_arousal_penalty(affection: int | float | None, base_penalty: int = BASE_OBJECTION_AROUSAL_PENALTY) -> tuple[int, float]:
    """Calculate objection arousal penalty scaled by inverse relationship multiplier.

    Objection Penalty = Base Penalty × Inverse Relationship Multiplier (1 / Rel_Mult)
    - Hostility/Nemesis (Affection <= -70): Rel_Mult x0.0 -> Inverse x2.0 -> Penalty -10
    - Distant/Resentful (Affection < 0): Rel_Mult x0.5 -> Inverse x2.0 -> Penalty -10
    - Neutral/Strangers (Affection < 20): Rel_Mult x0.8 -> Inverse x1.25 -> Penalty -6
    - Friends/Peers (Affection < 45): Rel_Mult x1.0 -> Inverse x1.0 -> Penalty -5
    - Close Confidants (Affection < 70): Rel_Mult x1.2 -> Inverse x0.83 -> Penalty -4
    - Romantic/Lovers (Affection < 85): Rel_Mult x1.35 -> Inverse x0.74 -> Penalty -4
    - Soulmate/Devoted (Affection >= 85): Rel_Mult x1.5 -> Inverse x0.67 -> Penalty -3
    """
    rel_mult = relationship_arousal_multiplier(affection)
    if rel_mult <= 0.0:
        inverse_mult = 2.0
    else:
        inverse_mult = round(1.0 / rel_mult, 2)
    penalty = round(base_penalty * inverse_mult)
    return penalty, inverse_mult


def relationship_arousal_multiplier(affection: int | float) -> float:
    """Calculate dynamic arousal bonus multiplier from relationship Affection (-100 to 100).

    - Extreme hostility / nemesis (-100 to -70): x0.0 (blocks intimacy arousal progression)
    - Distant / resentment (-69 to -1): x0.5 (arousal gain heavily dampened)
    - Neutral / strangers (0 to 19): x0.8 (guarded / cautious)
    - Friendly / peers (20 to 44): x1.0 (baseline standard gain)
    - Close friends / confidants (45 to 69): x1.20 (+20% bonus multiplier from high trust)
    - Lovers / romantic partners (70 to 84): x1.35 (+35% bonus multiplier from passion)
    - Soulmate / deeply devoted (85 to 100): x1.50 (+50% bonus multiplier from profound bond)
    """
    aff = float(affection if affection is not None else 10)
    if aff <= -70:
        return 0.0
    elif aff < 0:
        return 0.5
    elif aff < 20:
        return 0.8
    elif aff < 45:
        return 1.0
    elif aff < 70:
        return 1.20
    elif aff < 85:
        return 1.35
    else:
        return 1.50


def sexy_gift_bonus(item_name: str = "", item_desc: str = "", item_type: str = "", slot: str = "") -> int:
    """Return a small bonus only for an unmistakably sensual wearable gift."""
    text = " ".join(str(value or "") for value in (item_name, item_desc, item_type, slot)).casefold()
    cues = (
        "lingerie", "bunny", "bikini", "bra", "panties", "thong", "garter", "stocking",
        "bodysuit", "latex", "playboy", "ชุดชั้นใน", "บรา", "แพนตี้", "ถุงน่อง", "สายรัดต้นขา",
    )
    return SEXY_GIFT_AROUSAL_BONUS if any(cue in text for cue in cues) else 0


def h_item_use_bonus(item: dict | None) -> int:
    """Return the configured arousal gain when CHAR uses an H-item."""
    if not isinstance(item, dict) or str(item.get("type") or "").casefold() != "h_item":
        return 0
    effects = item.get("effects") if isinstance(item.get("effects"), dict) else {}
    try:
        return max(0, int(effects.get("arousal", H_ITEM_USE_AROUSAL_BONUS)))
    except (TypeError, ValueError):
        return H_ITEM_USE_AROUSAL_BONUS


def keep_pacing_bonus(text: str, stage: str) -> int:
    """Award every user turn that begins in an active H-Mode stage."""
    return STAGE_AROUSAL_BONUSES.get(str(stage or "").casefold(), 0)


def normal_chat_arousal_bonus(text: str, reply: str = "") -> int:
    """Award Normal Bonus (+2) upon accepted intimacy action or gift in Normal Mode without objection.

    Cues include: praise/compliment (เชยชม/คำพูดชื่นชม), teasing/flirting (หยอกล้อ/จีบ),
    headpats/hair stroke (ลูบหัว/ลูบผม/ลูบไล้), hugs/embraces (กอด/โอบ), kissing/touch, or gifts (ของขวัญ).
    Returns 0 if user asks to stop or if character explicitly objects/refuses.
    """
    words = (text or "").casefold()
    # Thai `อย่าง` begins with the same glyphs as `อย่า`; only treat the
    # latter as a stop/refusal when it is not the start of `อย่าง...`.
    if not words.strip() or re.search(r"หยุด|พักก่อน|ไม่เอา|อย่า(?!ง)|จบฉาก|\b(?:stop|no|don't|dont|end)\b", words):
        return 0

    reply_cf = (reply or "").casefold()
    if reply_cf and re.search(r"ถอยไป|อย่าทำแบบนี้|ไม่เอาค่ะ|ไม่เอาครับ|ปฏิเสธ|ผลักออก|ไม่พร้อม|อย่าจับ|รังเกียจ|\b(?:don't|dont touch|stop it|push away|refuse)\b", reply_cf):
        return 0

    intimacy_cues = (
        "ชม", "สวย", "น่ารัก", "เก่งมาก", "ชอบ", "เชยชม", "คนดี",
        "หยอก", "แหย่", "แกล้ง", "ยั่ว", "จีบ", "กระซิบ",
        "ลูบหัว", "ลูบผม", "ลูบแก้ม", "ลูบไล้", "สัมผัส", "จับมือ",
        "กอด", "โอบ", "ซบ", "ดึงเข้ามากอด", "สวมกอด", "จูบ", "หอมแก้ม",
        "ของขวัญ", "ให้ของขวัญ", "มอบให้", "ยื่นให้",
        "praise", "beautiful", "cute", "compliment", "tease", "flirt",
        "headpat", "pat head", "stroke hair", "caress", "touch", "hold hands",
        "hug", "embrace", "cuddle", "kiss", "gift", "present",
    )
    return NORMAL_CHAT_AROUSAL_BONUS if any(cue in words for cue in intimacy_cues) else 0


def final(base_arousal: float, scene_arousal: float, multiplier: float) -> int:
    return max(0, min(100, round((max(0, base_arousal) + max(0, scene_arousal)) * max(0, multiplier))))


def minimum_arousal(base_arousal: float, multiplier: float) -> int:
    """Return the invariant biological floor: base arousal × multiplier."""
    return max(0, min(100, round(max(0, base_arousal) * max(0, multiplier))))


def level(value: int) -> str:
    return "None" if value <= 0 else "Low" if value < 38 else "Medium" if value < 63 else "High" if value < 88 else "Overwhelmed"


def scene_value(status: str) -> int:
    match = re.search(r"(?im)^\s*-?\s*Arousal\s*:\s*(.+)$", status or "")
    if not match:
        return 0
    text = match.group(1).casefold()
    numeric = re.search(r"\b(\d{1,3})\s*/\s*100\b", text)
    if numeric:
        return max(0, min(100, int(numeric.group(1))))
    return next((value for name, value in LEVELS.items() if name in text), 0)


def climax_penalty(climax_peaks: int = 0, *, h_energy: int | None = None) -> int:
    """Return the scene-arousal reduction for an orgasm event based on remaining H-Energy."""
    if h_energy is not None:
        try:
            rem = max(0, min(3, int(h_energy)))
        except (TypeError, ValueError):
            rem = 2
        return H_ENERGY_CLIMAX_PENALTIES.get(rem, 100 if rem <= 0 else 25)
    try:
        peaks = max(0, int(climax_peaks or 0))
    except (TypeError, ValueError):
        peaks = 0
    return CLIMAX_PENALTIES.get(peaks, 100 if peaks >= 3 else 0)


def apply(status: str, biorhythm: dict, intimacy_active: bool, climax_peaks: int = 0,
          *, h_energy: int | None = None, pacing_bonus: int = 0, previous_status: str = "",
          previous_climax_peaks: int | None = None, stage: str = "",
          preserve_previous: bool = False, orgasm_completed: bool = False,
          normal_bonus: int = 0, wardrobe_bonus: int = 0,
          gift_bonus: int = 0, item_bonus: int = 0,
          award_h_bonus: bool | None = None,
          affection: int | float | None = None,
          objection: bool = False) -> tuple[str, dict]:
    base = float(biorhythm.get("arousal_base", 0) or 0)
    bio_multiplier = float(biorhythm.get("arousal_multiplier", 1) or 1)
    
    # Calculate effective multiplier combining biological factor and relationship bond
    if affection is None:
        # Extract affection directly from current status snapshot if not explicitly passed
        aff_m = re.search(r"(?im)^\s*-?\s*Affection(?:\s*Level)?\s*:\s*(-?\d{1,3})", status or "")
        affection = int(aff_m.group(1)) if aff_m else 10

    rel_multiplier = relationship_arousal_multiplier(affection)
    effective_multiplier = round(bio_multiplier * rel_multiplier, 3)

    floor = minimum_arousal(base, bio_multiplier)
    # Normal scenes have no scene contribution. The biological baseline may
    # still exist as state, but it must never advance the scene on its own.
    raw_scene = scene_value(status) if intimacy_active else 0
    # Resolve remaining H-Energy (0..3); if not explicitly passed, infer from legacy climax_peaks
    if h_energy is None:
        try:
            rem_energy = max(0, min(3, 3 - int(climax_peaks or 0)))
        except (TypeError, ValueError):
            rem_energy = 3
    else:
        try:
            rem_energy = max(0, min(3, int(h_energy)))
        except (TypeError, ValueError):
            rem_energy = 3
    exhausted = (rem_energy <= 0)
    # A newly emitted orgasm always charges its penalty based on remaining H-Energy:
    # H-Energy 2 -> -25, H-Energy 1 -> -50, H-Energy 0 (Exhausted) -> -100 (resets to biological floor).
    penalty = climax_penalty(climax_peaks, h_energy=rem_energy) if orgasm_completed else 0
    applied_penalty = penalty
    if orgasm_completed and exhausted:
        # Exhausted (H-Energy == 0): apply the full -100, retaining biological floor below.
        applied_penalty = 100
    scene = max(0, raw_scene - applied_penalty)
    value = final(base, scene, bio_multiplier)
    if previous_status and (intimacy_active or orgasm_completed):
        previous_value = scene_value(previous_status)
        if orgasm_completed:
            value = (final(base, 0, bio_multiplier) if exhausted
                     else max(0, round(previous_value - applied_penalty)))
        else:
            value = previous_value
    elif previous_status:
        value = max(scene_value(previous_status), value)
    if preserve_previous and previous_status:
        value = scene_value(previous_status)
    h_bonus_allowed = intimacy_active and (stage != 'aftercare' if award_h_bonus is None else award_h_bonus)
    base_bonus = max(0, int(pacing_bonus)) if h_bonus_allowed else 0
    bonus = round(base_bonus * effective_multiplier)
    if bonus:
        bonus_base_value = value if orgasm_completed else max(value, scene_value(previous_status))
        value = min(100, bonus_base_value + bonus)
    normal_base = max(0, int(normal_bonus)) if not intimacy_active else 0
    normal_award = round(normal_base * effective_multiplier)
    if normal_award:
        value = min(100, max(value, scene_value(previous_status)) + normal_award)
    # Clothing removal bonus affected by relationship receptivity
    wardrobe_base = max(0, int(wardrobe_bonus))
    wardrobe_award = round(wardrobe_base * effective_multiplier)
    if wardrobe_award:
        value = min(100, max(value, scene_value(previous_status)) + wardrobe_award)
    gift_base = max(0, int(gift_bonus))
    gift_award = round(gift_base * effective_multiplier)
    if gift_award:
        value = min(100, max(value, scene_value(previous_status)) + gift_award)
    item_base = max(0, int(item_bonus))
    item_award = round(item_base * effective_multiplier)
    if item_award:
        value = min(100, max(value, scene_value(previous_status)) + item_award)
    # Objection arousal penalty = base penalty × inverse relationship multiplier
    objection_penalty_value = 0
    inverse_rel_multiplier = 1.0
    if objection:
        objection_penalty_value, inverse_rel_multiplier = objection_arousal_penalty(affection)
        value = max(0, value - objection_penalty_value)
    # A completed orgasm with no remaining H-Energy always ends at the
    # biological floor: its -100 penalty wins over bonuses in that same turn.
    if orgasm_completed and exhausted:
        value = floor
    # The -100 exhausted penalty is charged for each completed orgasm while
    # H-Energy is zero. The normal biological minimum still applies.
    value = max(floor, value)
    label = level(value)
    if re.search(r"(?im)^\s*-?\s*Arousal\s*:", status or ""):
        status = re.sub(r"(?im)^(\s*-?\s*Arousal\s*:\s*).+$", rf"\1{label} ({value}/100)", status)
    if exhausted and re.search(r"(?im)^\s*-?\s*Energy\s*:", status or ""):
        status = re.sub(r"(?im)^(\s*-?\s*Energy\s*:\s*).+$", r"\1Exhausted", status)
    return status, {
        "base": base,
        "minimum": floor,
        "raw_scene": raw_scene,
        "scene": scene,
        "h_energy": rem_energy,
        "exhausted": exhausted,
        "climax_penalty": penalty,
        "climax_penalty_applied": applied_penalty,
        "orgasm_completed": orgasm_completed,
        "multiplier": bio_multiplier,
        "relationship_multiplier": rel_multiplier,
        "effective_multiplier": effective_multiplier,
        "affection": affection,
        "pacing_bonus_base": base_bonus,
        "pacing_bonus": bonus,
        "normal_bonus_base": normal_base,
        "normal_bonus": normal_award,
        "wardrobe_bonus_base": wardrobe_base,
        "wardrobe_bonus": wardrobe_award,
        "sexy_gift_bonus_base": gift_base,
        "sexy_gift_bonus": gift_award,
        "h_item_bonus_base": item_base,
        "h_item_bonus": item_award,
        "objection": objection,
        "objection_penalty": objection_penalty_value,
        "inverse_relationship_multiplier": inverse_rel_multiplier,
        "final": value,
        "level": label,
    }
