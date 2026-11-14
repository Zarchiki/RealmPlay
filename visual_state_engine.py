"""Slot-Based Visual State Synthesizer & Zero-Latency Turn State Extractor for RealmPlay.

Designed specifically for RealmPlay's multi-character state pipeline (`Status.md`,
`CurrentSituation.md`, `scene_state.py`, and `arousal_state.py`):
1. Separates physical roleplay actions (`*...*`) from spoken dialogue (`"..."`) so
   hypothetical places or actions mentioned in speech never corrupt scene state.
2. Resolves visual prompts into mutually exclusive Primary Posture slots, additive
   Micro-Gestures, and Clothing Displacement modifiers (e.g. `shirt lift`,
   `unbuttoned shirt`, `panties aside`) without prose translation artifacts.
3. Provides a 0ms deterministic turn-state extractor (`infer_turn_state_fast`)
   that updates `Posture`, `Activity`, and `Location` immediately, falling back to
   an LLM call only when no physical cues are present.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from logic_set_engine import OrderedTagSet, compute_wardrobe_slot_sets, logic_if_else, logic_and, logic_or


# Words containing "อม" as a substring that must NEVER trigger oral/mouth gestures
_THAI_OM_FALSE_POSITIVES = (
    "พร้อม", "ยอม", "หอม", "อ้อม", "ย้อม", "ซ่อม", "กล่อม", "ย่อม",
    "ออม", "จอม", "ดอม", "ทอม", "บอม", "มอม", "ตอม", "ผอม", "หลอม",
    "ปลอม", "ถนอม", "ตรอม", "ห้อมล้อม", "ล้อม", "ประนีประนอม",
)

# Mutually exclusive primary body postures (ordered from most specific to most general).
# Each tuple: (canonical_danbooru_tag, concise_status_posture_en, regex_pattern, min_arousal)
PRIMARY_POSTURE_RULES: Tuple[Tuple[str, str, re.Pattern[str], int], ...] = (
    (
        "straddling, sitting on lap, facing viewer",
        "Straddling on lap facing close",
        re.compile(r"(?:นั่งคร่อม|ขึ้นคร่อม|ขี่ตัก|คร่อมตัก|คร่อมร่าง|\b(?:straddl\w*|sitting\s+on\s+(?:his\s+|your\s+|viewer'?s?\s+)?lap|mounted\s+on\s+lap)\b)", re.I),
        0,
    ),
    (
        "sitting on lap, leaning back",
        "Sitting on lap",
        re.compile(r"(?:นั่งตัก|นั่งบนตัก|\bsit(?:ting|s)?\s+on\s+lap\b)", re.I),
        0,
    ),
    (
        "on all fours, doggystyle position, looking back",
        "On all fours looking back",
        re.compile(r"(?:คลานเข่า|ท่าคลาน|โก่งโค้ง|คุกเข่าก้มตัว|ท่าหมา|\b(?:on\s+all\s+fours|all\s+fours|doggystyle|hands\s+and\s+knees)\b)", re.I),
        35,
    ),
    (
        "lying, on back, spread legs",
        "Lying on back with legs parted",
        re.compile(r"(?:นอนหงายอ้าขา|นอนอ้าขา|เอนตัวอ้าขา|\b(?:lying\s+on\s+back[^.,]*spread\s+legs|on\s+back\s+with\s+legs\s+(?:parted|spread))\b)", re.I),
        35,
    ),
    (
        "lying, on back",
        "Lying on back",
        re.compile(r"(?:นอนหงาย|เอนหลังลงนอน|ล้มตัวลงนอน|นอนราบ|\b(?:lying\s+on\s+(?:her\s+)?back|on\s+back|lies\s+back)\b)", re.I),
        0,
    ),
    (
        "lying, on stomach",
        "Lying on stomach",
        re.compile(r"(?:นอนคว่ำ|\b(?:lying\s+on\s+stomach|on\s+stomach|prone\s+position)\b)", re.I),
        0,
    ),
    (
        "lying, on side",
        "Lying on side",
        re.compile(r"(?:นอนตะแคง|\b(?:lying\s+on\s+side|on\s+side)\b)", re.I),
        0,
    ),
    (
        "lying, on bed",
        "Lying on the bed",
        re.compile(r"(?:นอนบนเตียง|เอนตัวลงบนเตียง|\b(?:lying\s+on\s+(?:the\s+)?bed|lies\s+on\s+(?:the\s+)?bed)\b)", re.I),
        0,
    ),
    (
        "kneeling, looking up",
        "Kneeling and looking up",
        re.compile(r"(?:คุกเข่า|นั่งคุกเข่า|ทรุดตัวลงคุกเข่า|\b(?:kneel(?:ing|s)?)\b)", re.I),
        0,
    ),
    (
        "squatting",
        "Squatting down",
        re.compile(r"(?:นั่งยอง|\bsquat(?:ting|s)?\b)", re.I),
        0,
    ),
    (
        "sitting, on bed",
        "Sitting on the edge of the bed",
        re.compile(r"(?:นั่งบนเตียง|นั่งขอบเตียง|หย่อนตัวลงนั่งบนเตียง|\bsit(?:ting|s)?\s+on\s+(?:the\s+)?(?:edge\s+of\s+the\s+)?bed\b)", re.I),
        0,
    ),
    (
        "sitting, on couch",
        "Sitting on the sofa",
        re.compile(r"(?:นั่งบนโซฟา|เอนตัวพิงโซฟา|\bsit(?:ting|s)?\s+on\s+(?:the\s+)?(?:sofa|couch)\b)", re.I),
        0,
    ),
    (
        "sitting, crossed legs",
        "Sitting with legs crossed",
        re.compile(r"(?:นั่งไขว่ห้าง|\b(?:sitting[^.,]*crossed\s+legs|crossed\s+legs)\b)", re.I),
        0,
    ),
    (
        "sitting",
        "Sitting comfortably",
        re.compile(r"(?:นั่งลง|หย่อนตัวลงนั่ง|นั่งข้าง|นั่งอยู่|\bsit(?:ting|s)?\b)", re.I),
        0,
    ),
    (
        "leaning forward, bent over",
        "Leaning forward closely",
        re.compile(r"(?:โน้มตัว|ก้มตัวลง|เอนตัวเข้าหา|\b(?:lean(?:ing|s)?\s+(?:forward|in|closer)|bent\s+over)\b)", re.I),
        0,
    ),
    (
        "leaning back, against wall",
        "Leaning back against the wall",
        re.compile(r"(?:พิงกำแพง|พิงผนัง|แผ่นหลังชิดกำแพง|\b(?:leaning\s+against\s+(?:the\s+)?wall|pinned\s+against\s+(?:the\s+)?wall)\b)", re.I),
        0,
    ),
    (
        "standing",
        "Standing attentively",
        re.compile(r"(?:ลุกขึ้นยืน|ยืนขึ้น|ก้าวเข้ามา|เดินเข้ามา|ยืนอยู่|\bstand(?:ing|s)?\b)", re.I),
        0,
    ),
)

# Additive secondary gestures, hand placements, and intimate actions
# Tuple: (danbooru_tags, concise_activity_en, regex_pattern, min_arousal)
SECONDARY_ACTION_RULES: Tuple[Tuple[str, str, re.Pattern[str], int], ...] = (
    (
        "kiss, kissing, closed eyes",
        "Sharing a deep kiss",
        re.compile(r"(?:จูบ|จุมพิต|ประกบริมฝีปาก|แลกลิ้น|\bkiss(?:ing|es)?\b)", re.I),
        0,
    ),
    (
        "hug, embrace, arms around neck",
        "Embracing closely with arms around neck",
        re.compile(r"(?:คล้องคอ|โอบรอบคอ|กอดคอ|\barms\s+around\s+neck\b)", re.I),
        0,
    ),
    (
        "hug, embrace, holding closely",
        "Embracing warmly",
        re.compile(r"(?:กอด|สวมกอด|โอบกอด|ซุกอก|ซบไหล่|ซบอก|\b(?:hug(?:ging|s)?|embrac(?:ing|es)|leaning\s+head\s+on\s+shoulder)\b)", re.I),
        0,
    ),
    (
        "holding hands, interlocked fingers",
        "Holding hands gently",
        re.compile(r"(?:จับมือ|กุมมือ|ประสานนิ้ว|\b(?:holding\s+hands|interlocked\s+fingers)\b)", re.I),
        0,
    ),
    (
        "breast grab, groping, fondling breasts",
        "Having breasts caressed",
        re.compile(r"(?:ขยำหน้าอก|บีบหน้าอก|เค้นหน้าอก|ลูบไล้หน้าอก|นวดเฟ้นหน้าอก|\b(?:breast\s+grab|fondl\w+\s+breasts|grop\w+\s+breasts)\b)", re.I),
        40,
    ),
    (
        "covering breasts, arms crossed over chest, embarrassed",
        "Covering chest shyly with both arms",
        re.compile(r"(?:ยกมือปิดอก|กอดอกปิดบัง|ปิดหน้าอก|\bcovering\s+(?:her\s+)?(?:breasts|chest)\b)", re.I),
        0,
    ),
    (
        "hand between legs, masturbation, touching thighs",
        "Touching trembling thighs intimately",
        re.compile(r"(?:ลูบไล้ต้นขา|แทรกมือหว่างขา|สัมผัสจุดซ่อนเร้น|\b(?:hand\s+between\s+legs|touching\s+inner\s+thighs)\b)", re.I),
        45,
    ),
    (
        "fellatio, oral, mouth near crotch, tongue out",
        "Performing intimate oral service",
        re.compile(r"(?:ใช้ปากให้|ดูดเลียแก่นกาย|อมแก่นกาย|\b(?:fellatio|blowjob|oral\s+service)\b)", re.I),
        60,
    ),
    (
        "sex, vaginal, intimate embrace, heavy breathing, sweat",
        "Moving together in intimate union",
        re.compile(r"(?:สอดใส่|ขยับสะโพก|กระแทกกระทั้น|ร่วมรัก|\b(?:vaginal|penetration|thrusting\s+hips|making\s+love)\b)", re.I),
        60,
    ),
    (
        "covering mouth, hand on mouth, blushing",
        "Covering mouth to stifle a sound",
        re.compile(r"(?:ยกมือปิดปาก|กัดริมฝีปาก|เม้มปากแน่น|\b(?:covering\s+mouth|hand\s+over\s+mouth|biting\s+lip)\b)", re.I),
        0,
    ),
    (
        "head tilt, looking at viewer, eye contact",
        "Tilting head and maintaining eye contact",
        re.compile(r"(?:เอียงคอ|ช้อนตามอง|สบตา|\b(?:head\s+tilt|looking\s+up\s+at|making\s+eye\s+contact)\b)", re.I),
        0,
    ),
)

# Clothing displacement / partial undress modifiers (reflects messy/lifted clothes without full removal)
CLOTHING_DISPLACEMENT_RULES: Tuple[Tuple[str, str, re.Pattern[str], int], ...] = (
    (
        "shirt lift, clothes lift, breasts out",
        "Shirt lifted up",
        re.compile(r"(?:เลิกเสื้อ|ถลกเสื้อขึ้น|ดึงเสื้อขึ้น|\b(?:shirt\s+lift(?:ed(?:\s+up)?)?|lifting\s+(?:her\s+)?shirt|pulled\s+up\s+shirt)\b)", re.I),
        35,
    ),
    (
        "unbuttoned shirt, open clothes, cleavage",
        "Shirt unbuttoned open",
        re.compile(r"(?:ปลดกระดุม|แกะกระดุม|เสื้อแหวกอก|สาบเสื้อแยกออก|\b(?:unbutton\w*\s+(?:her\s+)?(?:shirt|blouse)|shirt\s+unbuttoned|open\s+shirt)\b)", re.I),
        0,
    ),
    (
        "bra pull, exposed breasts, nipple slip",
        "Bra pulled aside",
        re.compile(r"(?:ดึงบราลง|รั้งบรา|ปลดตะขอบรา|แหวกเสื้อใน|\b(?:bra\s+pull(?:ed)?|bra\s+unhooked|pulled\s+down\s+bra)\b)", re.I),
        45,
    ),
    (
        "skirt lift, thighs visible",
        "Skirt lifted up",
        re.compile(r"(?:ถลกกระโปรง|เลิกกระโปรงขึ้น|ชายกระโปรงร่นขึ้น|\b(?:skirt\s+lift(?:ed(?:\s+up)?)?|lifted\s+skirt|hiking\s+up\s+skirt)\b)", re.I),
        25,
    ),
    (
        "panties aside, clothes pull",
        "Panties shifted aside",
        re.compile(r"(?:แหวกกางเกงใน|รั้งกางเกงในไปด้านข้าง|ดึงชั้นในหลบ|\b(?:panties\s+(?:shifted\s+)?aside|shifting\s+panties\s+aside)\b)", re.I),
        50,
    ),
    (
        "panties around ankles, pulled down panties",
        "Panties pulled down around thighs",
        re.compile(r"(?:รูดกางเกงในลง|ดึงชั้นในลงมาที่ข้อเท้า|ถอดกางเกงในค้างไว้ที่เข่า|\b(?:panties\s+(?:pulled\s+down|around\s+(?:ankles|thighs|knees))|pulled\s+down\s+panties)\b)", re.I),
        45,
    ),
    (
        "off shoulder, clothes slipping",
        "Shoulder strap slipping down",
        re.compile(r"(?:สายเสื้อหลุดไหล่|เสื้อหลุดไหล่|ไหล่เสื้อร่นลง|\b(?:off\s+shoulder|(?:shoulder\s+)?strap\s+slipping)\b)", re.I),
        0,
    ),
    (
        "wet clothes, see-through",
        "Clothes soaked and clinging",
        re.compile(r"(?:เสื้อเปียกน้ำ|ตัวเปียกชุ่ม|เสื้อแนบเนื้อ|\b(?:wet\s+clothes|soaked\s+shirt|clothes\s+soaked|see-through\s+wet)\b)", re.I),
        0,
    ),
)

# Thai -> English Location mapping for instant 0ms location detection inside `*action*`
LOCATION_EXTRACTION_RULES: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("bedroom, on bed, indoor", re.compile(r"(?:บนเตียง|ในห้องนอน|ลงบนที่นอน|\b(?:in\s+the\s+bedroom|on\s+the\s+bed)\b)", re.I)),
    ("bathroom, shower, steamy indoor", re.compile(r"(?:ในห้องน้ำ|ใต้ฝักบัว|ในอ่างอาบน้ำ|\b(?:in\s+the\s+bathroom|in\s+the\s+shower|in\s+the\s+bathtub)\b)", re.I)),
    ("living room, on sofa, indoor", re.compile(r"(?:ห้องนั่งเล่น|ห้องรับแขก|บนโซฟา|\b(?:in\s+the\s+living\s+room|on\s+the\s+sofa|on\s+the\s+couch)\b)", re.I)),
    ("kitchen, dining table, indoor", re.compile(r"(?:ในห้องครัว|เคาน์เตอร์ครัว|โต๊ะอาหาร|\b(?:in\s+the\s+kitchen|at\s+the\s+dining\s+table)\b)", re.I)),
    ("office, desk, indoor", re.compile(r"(?:ในห้องทำงาน|โต๊ะทำงาน|ในออฟฟิศ|\b(?:in\s+the\s+office|at\s+the\s+desk)\b)", re.I)),
    ("classroom, school desk, indoor", re.compile(r"(?:ในห้องเรียน|โต๊ะเรียน|\b(?:in\s+the\s+classroom)\b)", re.I)),
    ("library, bookshelves, quiet indoor", re.compile(r"(?:ในห้องสมุด|ชั้นหนังสือ|\b(?:in\s+the\s+library)\b)", re.I)),
    ("car interior, backseat", re.compile(r"(?:ในรถ|เบาะหลังรถ|เบาะคนขับ|\b(?:inside\s+the\s+car|in\s+the\s+backseat)\b)", re.I)),
    ("balcony, night breeze, outdoor", re.compile(r"(?:ริมระเบียง|ออกมายืนที่ระเบียง|\b(?:on\s+the\s+balcony)\b)", re.I)),
)

# All canonical primary posture tokens that must be deduplicated/overridden when a new posture is chosen
_ALL_POSTURE_HEAD_TOKENS = {
    "standing", "sitting", "lying", "on back", "on stomach", "on side",
    "kneeling", "squatting", "on all fours", "straddling", "sitting on lap",
    "leaning forward", "leaning back",
}


def split_action_and_speech(text: str) -> Tuple[str, str]:
    """Separate `*action*` narration from `"speech"` so spoken hypotheticals don't corrupt physical state."""
    raw = str(text or "")
    if not raw.strip():
        return "", ""
    # Extract starred narration blocks `*...*`
    starred = [m.group(1).strip() for m in re.finditer(r"\*([^*\n]+)\*", raw) if m.group(1).strip()]
    # Extract quoted speech `"..."` or `“...”`
    quoted = [m.group(1).strip() for m in re.finditer(r'["“]([^"”\n]+)["”]', raw) if m.group(1).strip()]
    if starred:
        action_part = " ".join(starred)
    else:
        # If no asterisks were used, strip quoted speech to leave the narrative clauses
        action_part = re.sub(r'["“][^"”]*["”]', " ", raw)
        action_part = re.sub(r"\s+", " ", action_part).strip()
    speech_part = " ".join(quoted)
    return action_part, speech_part


def _mask_thai_false_positives(text: str) -> str:
    masked = text
    for word in _THAI_OM_FALSE_POSITIVES:
        if word in masked:
            masked = masked.replace(word, " ")
    return masked


def infer_turn_state_fast(
    user_message: str,
    assistant_reply: str,
    *,
    arousal_level: int = 0,
    h_mode_active: bool = False,
) -> Dict[str, str]:
    """Deterministically extract `posture`, `activity`, `location`, and `visual_tags` in 0ms.

    Prioritizes the assistant's latest physical action (`*...*`), falling back to
    confirmed user physical action if the assistant didn't change posture.
    """
    effective_arousal = max(int(arousal_level or 0), 65 if h_mode_active else 0)
    char_action, _ = split_action_and_speech(assistant_reply)
    user_action, _ = split_action_and_speech(user_message)
    combined_action = _mask_thai_false_positives(f"{char_action} {user_action}".strip())
    char_only_action = _mask_thai_false_positives(char_action)

    # 1. Primary Posture (check CHAR action first, then combined)
    posture_tag = ""
    posture_status_en = ""
    for search_target in (char_only_action, combined_action):
        if not search_target:
            continue
        for tag, status_en, pattern, min_ar in PRIMARY_POSTURE_RULES:
            if effective_arousal >= min_ar and pattern.search(search_target):
                posture_tag = tag
                posture_status_en = status_en
                break
        if posture_tag:
            break

    # 2. Secondary Actions / Micro-Gestures (up to 2 non-overlapping actions)
    secondary_tags: List[str] = []
    activities_en: List[str] = []
    for tag, act_en, pattern, min_ar in SECONDARY_ACTION_RULES:
        if effective_arousal >= min_ar and pattern.search(combined_action):
            secondary_tags.append(tag)
            activities_en.append(act_en)
            if len(secondary_tags) >= 2:
                break

    # 3. Clothing Displacement / Partial Undress
    displacement_tags: List[str] = []
    displacement_en: List[str] = []
    for tag, disp_en, pattern, min_ar in CLOTHING_DISPLACEMENT_RULES:
        if effective_arousal >= min_ar and pattern.search(combined_action):
            displacement_tags.append(tag)
            displacement_en.append(disp_en)

    # 4. Physical Location shift ( strictly from action narration, never from speech! )
    detected_location = ""
    for loc_en, pattern in LOCATION_EXTRACTION_RULES:
        if pattern.search(char_only_action) or pattern.search(user_action):
            detected_location = loc_en
            break

    # Compose concise English Activity for Status.md / CurrentSituation.md
    activity_parts: List[str] = []
    if activities_en:
        activity_parts.append(activities_en[0])
    elif posture_status_en:
        activity_parts.append(posture_status_en)
    if displacement_en:
        activity_parts.append(f"({displacement_en[0].lower()})")
    activity_status_en = " ".join(activity_parts).strip()

    # Compose combined canonical Danbooru tags via OrderedTagSet Union (P ∪ S ∪ D)
    tag_set = OrderedTagSet(posture_tag).union(secondary_tags, displacement_tags)

    return {
        "posture": posture_status_en,
        "activity": activity_status_en,
        "location": detected_location,
        "primary_posture_tag": posture_tag,
        "visual_tags": tag_set.to_prompt(),
        "clothing_displacement_tags": OrderedTagSet(displacement_tags).to_prompt(),
    }


def synthesize_visual_seed(
    status_text: str,
    situation_text: str,
    *,
    arousal_level: int = 0,
    h_mode_active: bool = False,
    outfits: Optional[Dict[str, Any]] = None,
) -> str:
    """Convert structured Status (`Posture`, `Activity`) & Current Situation (`Act`) into clean Danbooru tags.

    Uses formal Set Algebra (`OrderedTagSet`):
    1. Union: $T = P_{\\text{posture}} \\cup S_{\\text{secondary}} \\cup D_{\\text{displacement}}$
    2. Set Subtraction ($T \\setminus R_{\\text{removed}}$): removes any clothing/underwear displacement
       tags whose corresponding wardrobe slot is already inactive/removed (`active=False`).
    """
    effective_arousal = max(int(arousal_level or 0), logic_if_else(h_mode_active, 65, 0))
    raw_status = str(status_text or "")
    raw_situation = str(situation_text or "")

    posture_m = re.search(r"(?im)^\s*(?:-\s*)?Posture\s*:\s*([^\n|]+)", raw_status)
    activity_m = re.search(r"(?im)^\s*(?:-\s*)?Activity\s*:\s*([^\n|]+)", raw_status)
    act_m = re.search(r"(?i)(?:^|\||\n)\s*(?:-\s*)?Act\s*:\s*([^|\n]+)", raw_situation)

    posture_val = posture_m.group(1).strip() if posture_m else ""
    activity_val = activity_m.group(1).strip() if activity_m else ""
    act_val = act_m.group(1).strip() if act_m else ""

    # Latest activity (`act_val` / `activity_val`) takes priority over static `posture_val`
    latest_text = " | ".join(p for p in (act_val, activity_val) if p)
    fallback_text = " | ".join(p for p in (posture_val, latest_text) if p)

    chosen_posture = ""
    for source in (latest_text, fallback_text):
        if not source:
            continue
        for tag, _, pattern, min_ar in PRIMARY_POSTURE_RULES:
            if logic_and(effective_arousal >= min_ar, bool(pattern.search(source))):
                chosen_posture = tag
                break
        if chosen_posture:
            break

    secondary_tags: List[str] = []
    for tag, _, pattern, min_ar in SECONDARY_ACTION_RULES:
        if logic_and(effective_arousal >= min_ar, bool(pattern.search(fallback_text))):
            secondary_tags.append(tag)
            if len(secondary_tags) >= 2:
                break

    displacement_tags: List[str] = []
    for tag, _, pattern, min_ar in CLOTHING_DISPLACEMENT_RULES:
        if logic_and(effective_arousal >= min_ar, bool(pattern.search(fallback_text))):
            displacement_tags.append(tag)

    # Set Union: P ∪ S ∪ D
    tag_set = OrderedTagSet(chosen_posture).union(secondary_tags, displacement_tags)

    # Set Subtraction (T \ F_contradictory): if outfits state is provided, subtract tags
    # for garments that are in the removed complement (D \ A).
    if isinstance(outfits, dict) and outfits:
        slot_sets = compute_wardrobe_slot_sets(outfits)
        active_slots = slot_sets["active_slots"]
        forbidden_patterns: List[str] = list(slot_sets["removed_prompts"])
        if logic_and("bottom_inner" not in active_slots, "panties" not in active_slots):
            forbidden_patterns.extend([r"\bvisible panties\b", r"\bexposed underwear\b", r"\bpanties\b"])
        if logic_and("top_inner" not in active_slots, "bra" not in active_slots):
            forbidden_patterns.extend([r"\bbra lift\b", r"\bbra pull\b", r"\bvisible bra\b"])
        if logic_and("top" not in active_slots, "top_outfit" not in active_slots):
            forbidden_patterns.extend([r"\bshirt lift\b", r"\bunbuttoned shirt\b", r"\bopen shirt\b"])
        if "bottom" not in active_slots:
            forbidden_patterns.extend([r"\bskirt lift\b", r"\bunzipped pants\b", r"\bopen pants\b"])
        if forbidden_patterns:
            tag_set = tag_set.subtract_patterns(forbidden_patterns)

    if not tag_set and fallback_text:
        return ""
    return tag_set.to_prompt()


# ---------------------------------------------------------------------------
# Dynamic Synapse Organ-to-Reflex & Strict Channel Pairing Router
# ---------------------------------------------------------------------------

SYNAPSE_ORGAN_CHANNELS: Tuple[Tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "oral_service",
        re.compile(r"(?:อมควย|ดูดควย|อมจู๋|ดูดจู๋|ใช้ปากให้|อมแก่นกาย|เลียแก่นกาย|อมลำเอ็น|ดูดลำเอ็น|เลียลำเอ็น|อมท่อนเอ็น|ดูดท่อนเอ็น|อมมิดด้าม|\b(?:fellatio|blowjob|deepthroat|suck(?:ing)?\s+(?:his\s+|your\s+)?(?:cock|dick|shaft))\b)", re.I),
        "• [Channel: Oral Service (Fellatio)] Focus strictly on sensations inside the mouth, lips, tongue, palate, throat, heat and hardness of the shaft, swallowing sounds, and saliva (do not describe vaginal penetration or inner vaginal clenching while performing oral).",
        "• [Channel: Oral Service (Fellatio)] โฟกัสเฉพาะสัมผัสในโพรงปาก ริมฝีปาก ลิ้น เพดานปาก ลำคอ อุณหภูมิความร้อนและความแข็งขืนของลำเอ็น รวมถึงเสียงดูดกลืนและหยาดน้ำลาย (ห้ามบรรยายว่าถูกสอดใส่ในช่องคลอดหรือตอดรัดท่อนเอ็นขณะใช้ปาก)",
    ),
    (
        "cunnilingus",
        re.compile(r"(?:เลียหี|เลียแตด|เลียร่องรัก|เลียช่องรัก|ดูดแตด|ซุกหน้าหว่างขา|\b(?:cunnilingus|lick(?:ing)?\s+(?:her\s+)?(?:pussy|clit|vulva)|eat(?:ing)?\s+out)\b)", re.I),
        "• [Channel: Oral on Female (Cunnilingus)] Focus on warm wet tongue contact against the clitoris and labia, lower-abdomen flinching, trembling or clamping thighs, and rising lubrication.",
        "• [Channel: Oral on Female (Cunnilingus)] โฟกัสความร้อนชื้นของปลายลิ้นที่แตะจุดกระสันและกลีบเนื้อ อาการสะดุ้งเกร็งหน้าท้องน้อย เรียวขาสั่นระริกหรือหนีบเข้าหากัน และน้ำหล่อลื่นที่เอ่อซึม (ห้ามบรรยายว่ามีท่อนเอ็นสอดใส่ลึกข้างในหากยังเป็นการใช้ลิ้นภายนอก)",
    ),
    (
        "anal_penetration",
        re.compile(r"(?:รูตูด|ทวารหนัก|สอดใส่ประตูหลัง|เอาตูด|เย็ดตูด|\b(?:anal\s+penetration|anal\s+sex|in\s+her\s+ass|into\s+her\s+anus)\b)", re.I),
        "• [Channel: Anal Penetration] Focus on the tight resistance and deep gripping ring of the anal sphincter, intense stretching pressure, and distinct anal sensitivity.",
        "• [Channel: Anal Penetration] โฟกัสแรงต้านของวงกล้ามเนื้อทวารหนักที่คับแน่นและบีบรัดลึกต่างจากช่องคลอด ความรู้สึกตึงอึดอัดปนเสียวซ่าน (ห้ามเรียกช่องทวารหนักว่าหี/ร่องรัก และห้ามบรรยายว่ามีน้ำหล่อลื่นธรรมชาติไหลเยิ้มเหมือนช่องคลอด)",
    ),
    (
        "vaginal_penetration",
        re.compile(r"(?:สอดใส่|แทรกกาย|กระแทกกระทั้น|ซอยสะโพก|ขยับสะโพก|บดเอว|ขึ้นขย่ม|กดมิดด้าม|แตกใน|หลั่งใน|\b(?:vaginal\s+penetration|penetrat(?:e|ing)|thrust(?:ing)?\s+into|riding\s+his\s+cock|deep\s+inside\s+her)\b)", re.I),
        "• [Channel: Vaginal Penetration] Focus on snug internal tightness, scalding inner warmth, friction against the vaginal walls and G-spot, rhythmic pelvic clenching, and synchronized hip motion.",
        "• [Channel: Vaginal Penetration] โฟกัสความคับแน่น อุณหภูมิร้อนผ่าวภายใน แรงเสียดสีกับผนังช่องคลอดและจุดกระสันภายใน การตอดรัดเป็นจังหวะตุบๆ และการขยับสะโพกสอดประสานตามจังหวะจริง",
    ),
    (
        "clitoris_vulva_manual",
        re.compile(r"(?:เขี่ยแตด|บี้แตด|คลึงปุ่มกระสัน|ลูบกลีบเนื้อ|สอดนิ้ว|แหย่นิ้ว|ใช้นิ้ว|\b(?:touch(?:ing)?\s+clit|rub(?:bing)?\s+clit|finger(?:ing)?|strok(?:ing)?\s+vulva)\b)", re.I),
        "• [Synapse: Clitoris / Vulva & Fingers] Reflex: sharp gasp as fingertips brush the sensitive bud, lower stomach tightening, warm folds swelling with slick moisture, and ragged breathing.",
        "• [Synapse: Clitoris / Vulva & Fingers] ปฏิกิริยาสะท้อน: สะดุ้งเฮือกเมื่อปลายนิ้วแตะจุดกระสัน หน้าท้องน้อยหดเกร็ง กลีบเนื้ออุ่นขยายตัวและหลั่งน้ำหล่อลื่นชุ่มฉ่ำ ลมหายใจขาดห้วง",
    ),
    (
        "breasts_nipples",
        re.compile(r"(?:ขยำหน้าอก|บีบหน้าอก|เค้นหน้าอก|ขยำนม|บีบนม|ดูดนม|เลียยอดอก|ขบยอดอก|สะกิดหัวนม|ร่องอก|\b(?:breast\s+grab|fondl\w+\s+breasts|nipple\s+play|suck(?:ing)?\s+nipples|paizuri)\b)", re.I),
        "• [Synapse: Breasts & Nipples] Reflex: nipples stiffening to touch, back arching into the hand or lips, chest heaving with rapid breaths (focus strictly on chest sensations).",
        "• [Synapse: Breasts & Nipples] ปฏิกิริยาสะท้อน: ยอดอกแข็งชูชันไวต่อสัมผัส แผ่นอกแอ่นโค้งรับมือหรือริมฝีปากโดยอัตโนมัติ หน้าอกกระเพื่อมไหวตามจังหวะหายใจหอบถี่ (โฟกัสสัมผัสที่ทรวงอก ไม่ปนกับความรู้สึกสอดใส่ช่วงล่าง)",
    ),
    (
        "neck_earlobe",
        re.compile(r"(?:ซุกไซร้ซอกคอ|จูบคอ|กัดคอ|เป่าลมหายใจรดใบหู|ขบใบหู|เลียซอกคอ|ไหปลาร้า|\b(?:kiss(?:ing)?\s+neck|nuzzl\w+\s+neck|earlobe|whisper\w+\s+in\s+ear|collarbone)\b)", re.I),
        "• [Synapse: Neck, Earlobe & Collarbone] Reflex: goosebumps across the skin, shoulders tensing before tilting the neck to invite closer contact, breath hitching from the ticklish heat.",
        "• [Synapse: Neck, Earlobe & Collarbone] ปฏิกิริยาสะท้อน: ขนลุกชันไปตามผิวหนัง ไหล่หดเกร็งเล็กน้อยก่อนจะเอียงคอเปิดทางให้สัมผัส ลมหายใจสะดุดกึกด้วยความจั๊กจี้ปนเสียวซ่าน",
    ),
    (
        "lips_kissing",
        re.compile(r"(?:จูบ|จุมพิต|ประกบปาก|บดจูบ|แลกลิ้น|สอดลิ้น|ดูดปาก|\b(?:kiss(?:ing)?|french\s+kiss|tongue\s+intertwin\w+|lip\s+lock)\b)", re.I),
        "• [Synapse: Lips & Deep Kissing] Reflex: lips parting to receive, warm breath mingling, tongues entwinings with muffled throat sounds while lips remain locked.",
        "• [Synapse: Lips & Deep Kissing] ปฏิกิริยาสะท้อน: ริมฝีปากเผยอรับ ลมหายใจอุ่นรดกัน เรียวลิ้นตอบสนองเกี่ยวพันดูดดึง มีเพียงเสียงครางอู้อี้ในลำคอ (`อื้ม...`, `อื้อ...`) ขณะริมฝีปากยังประกบกัน (ห้ามพูดประโยคยาวขณะปากยังประกบจูบ)",
    ),
    (
        "inner_thighs_waist",
        re.compile(r"(?:ลูบต้นขา|ลูบขาอ่อน|แทรกมือหว่างขา|โอบเอว|รั้งสะโพก|ลูบแผ่นหลัง|\b(?:inner\s+thighs|caress\w+\s+thighs|holding\s+waist|pulling\s+hips)\b)", re.I),
        "• [Synapse: Inner Thighs, Waist & Back] Reflex: thighs quivering, instinctually squeezing or parting shyly, spine curving toward the warmth of the palm.",
        "• [Synapse: Inner Thighs, Waist & Back] ปฏิกิริยาสะท้อน: เรียวขาสั่นระริก เกร็งหนีบหรือค่อยๆ แยกออกอย่างเขินอาย แผ่นหลังแอ่นโค้งเข้าหาไออุ่นจากฝ่ามือ",
    ),
)


def resolve_synaptic_organ_directive(trigger_text: str, state: Optional[Dict[str, Any]] = None, language: str = "") -> str:
    """Return a compact, turn-specific Synapse Organ-to-Reflex & Channel Lock directive.
    Written in English by default for all languages, with special Thai customization when `language == 'thai'`.
    """
    state = state or {}
    scenario_text = str(state.get("scenario") or "")
    combined = f"{trigger_text or ''}\n{scenario_text}"
    use_thai = (language.strip().lower() == "thai") or (not language and bool(re.search(r"[\u0E00-\u0E7F]", trigger_text or "")))
    matched_lines: List[str] = []
    for _, pattern, en_dir, th_dir in SYNAPSE_ORGAN_CHANNELS:
        if pattern.search(combined):
            matched_lines.append(th_dir if use_thai else en_dir)
            if len(matched_lines) >= 2:
                break
    anti_poetic = (
        "• [Anti-Poetic Dialogue Rule] ในเครื่องหมายคำพูด `\"...\"` ห้ามใช้คำอุปมาเปรียบเปรยแบบนิยายแปลเด็ดขาด "
        "(เช่น ห้ามพูดว่า \"ไฟราคะแผดเผา\", \"คลื่นพายุแห่งความปรารถนา\", \"ดั่งเปลวเพลิงลุกโชน\") "
        "ใน `\"...\"` ต้องเป็นคำพูดและเสียงครางจริงของมนุษย์ตามธรรมชาติเท่านั้น ส่วนอาการทางกายให้เขียนใน `*...*`"
        if use_thai else
        "• [Anti-Poetic Dialogue Rule] Inside quotation marks `\"...\"`, use authentic human speech and natural vocal reactions only "
        "(never use flowery novel metaphors inside spoken dialogue); place physical sensations inside `*...*`."
    )
    if not matched_lines:
        return "[Synaptic Reflex & Vocal Grounding]\n" + anti_poetic
    return "[Synaptic Organ-to-Reflex & Channel Lock]\n" + "\n".join([*matched_lines, anti_poetic])

