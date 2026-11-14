"""Trait-aware recovery emotions for terminal aftercare."""
from typing import Any, Dict
import hashlib


# These are face-only visual directions. They portray an extreme fantasy
# depletion state after the third climax without taking control of pose,
# posture, wardrobe, or the scene action.
EXHAUSTED_AFTERCARE_EMOTIONS: Dict[str, Dict[str, Any]] = {
    "tender_exhaustion": {
        "traits": ("gentle", "kind", "caring", "warm", "soft", "อ่อนโยน", "ใจดี", "ห่วงใย"),
        "intensity": 72,
        "cause": "หมดแรงแต่ยังอ่อนโยนและรับรู้ความปลอดภัยรอบตัว",
        "prompt": "fantasy tender exhaustion expression, luminous half-lidded eyes, soft trembling smile, dew-bright lashes, warm gentle gaze, detailed face",
    },
    "quiet_depletion": {
        "traits": ("calm", "reserved", "stoic", "composed", "quiet", "สุขุม", "นิ่ง", "เงียบขรึม"),
        "intensity": 68,
        "cause": "พลังงานหมดลงและพักอย่างสงบ โดยยังคงความนิ่งของตัวเอง",
        "prompt": "ethereal quiet depletion expression, heavy lowered eyelids, distant steady gaze, pale softened features, serene exhausted face, detailed face",
    },
    "shy_vulnerability": {
        "traits": ("shy", "timid", "innocent", "bashful", "ขี้อาย", "เขิน", "ขลาด", "ไร้เดียงสา"),
        "intensity": 78,
        "cause": "หมดแรงและเปราะบาง จึงหลบสายตาอย่างเขินอาย",
        "prompt": "fantasy shy vulnerability expression, deep blush, downcast glassy eyes, trembling lashes, fragile exhausted smile, detailed face",
    },
    "clingy_reassurance": {
        "traits": ("affectionate", "romantic", "attached", "loving", "clingy", "รัก", "โรแมนติก", "ติดคน", "อ้อน"),
        "intensity": 76,
        "cause": "อ่อนล้าและต้องการการยืนยันว่าทุกอย่างปลอดภัย",
        "prompt": "fantasy clingy reassurance expression, pleading tender eyes, soft flushed cheeks, parted breath, yearning for reassurance, detailed face",
    },
    "proud_recovery": {
        "traits": ("confident", "dominant", "strong", "proud", "resilient", "มั่นใจ", "เข้มแข็ง", "ภูมิใจ", "ผู้นำ"),
        "intensity": 64,
        "cause": "เหนื่อยจนแทบขยับไม่ไหว แต่พยายามรักษาความมั่นใจไว้",
        "prompt": "fantasy proud recovery expression, defiant tired smile, fevered flush, resilient gleaming eyes, composed exhausted face, detailed face",
    },
    "overstimulated_haze": {
        "traits": ("sensitive", "overwhelmed", "anxious", "neurotic", "sensitive", "อ่อนไหว", "วิตก", "ตื่นง่าย", "คิดมาก"),
        "intensity": 88,
        "cause": "รับความรู้สึกมากเกินไปจนมึนงงและต้องหยุดพักเต็มที่",
        "prompt": "fantasy overstimulated ahegao facial expression, glassy rolled-up unfocused eyes, parted lips, tongue slightly out, dazed flushed face, overwhelmed exhausted expression",
    },
    "relieved_release": {
        "traits": ("guarded", "worried", "cautious", "serious", "ระวังตัว", "กังวล", "เคร่งเครียด", "จริงจัง"),
        "intensity": 70,
        "cause": "ความตึงเครียดคลายลง เหลือเพียงความโล่งใจและความอ่อนล้า",
        "prompt": "fantasy relieved release expression, cathartic exhale, damp lashes, tear-bright eyes, softened radiant face, exhausted relief",
    },
    "playful_aftercare": {
        "traits": ("playful", "mischievous", "teasing", "cheerful", "funny", "ขี้เล่น", "เจ้าเล่ห์", "แกล้ง", "ร่าเริง"),
        "intensity": 66,
        "cause": "เหนื่อยล้าเต็มที่แต่ยังเหลือรอยยิ้มขี้เล่นเล็กน้อย",
        "prompt": "fantasy sleepy playful expression, mischievous tired smile, warm blush, starry relaxed eyes, teasing afterglow face, detailed face",
    },
    "tearful_overwhelm": {
        "traits": ("emotional", "melancholic", "tragic", "sensitive", "tearful", "อารมณ์อ่อนไหว", "เศร้า", "หม่น", "ดราม่า", "ร้องไห้ง่าย"),
        "intensity": 92,
        "cause": "ความเหนื่อยล้าท่วมท้นจนกลั้นน้ำตาไม่อยู่",
        "prompt": "fantasy tearful overwhelm expression, streaming tears, trembling wet lashes, red-rimmed glassy eyes, broken breath, exhausted crying face",
    },
    "senseless_faint": {
        "traits": ("fragile", "delicate", "faint", "yielding", "dreamy", "บอบบาง", "อ่อนแอ", "เคลิ้ม", "หมดสติ", "ยอมจำนน"),
        "intensity": 100,
        "cause": "พลังงานหมดสิ้นจนสติเลือนรางและไม่อาจตอบสนองต่อสิ่งใดได้",
        "prompt": "fantasy senseless ahegao facial expression, rolled-up unfocused eyes, pale flushed face, slack parted lips, tongue slightly out, tear-wet lashes, unconscious exhausted face",
    },
}

# Face-only fantasy expressions for the active climax stage.
CLIMAX_EMOTIONS: Dict[str, Dict[str, Any]] = {
    "blissful_surrender": {"traits": ("gentle", "kind", "caring", "warm", "soft", "อ่อนโยน", "ใจดี", "ห่วงใย"), "intensity": 88, "cause": "ความสุขท่วมท้นจนปล่อยวางอย่างอ่อนโยน", "prompt": "fantasy blissful surrender expression, luminous half-lidded eyes, rapturous soft smile, radiant flush, tear-bright lashes, detailed face"},
    "controlled_ecstasy": {"traits": ("calm", "reserved", "stoic", "composed", "quiet", "สุขุม", "นิ่ง", "เงียบขรึม"), "intensity": 84, "cause": "พยายามเก็บอาการไว้ แต่แววตาเผยความสุขเกินควบคุม", "prompt": "fantasy controlled ecstasy expression, intense narrowed gaze, trembling restrained smile, glowing flushed cheeks, composed rapture face"},
    "shy_ecstasy": {"traits": ("shy", "timid", "innocent", "bashful", "ขี้อาย", "เขิน", "ขลาด", "ไร้เดียงสา"), "intensity": 92, "cause": "ความเขินอายถูกกลบด้วยความสุขที่รุนแรงจนปิดไม่มิด", "prompt": "fantasy shy ecstasy expression, overwhelming crimson blush, watery upturned eyes, fluttering lashes, breathless fragile smile, detailed face"},
    "devoted_euphoria": {"traits": ("affectionate", "romantic", "attached", "loving", "clingy", "รัก", "โรแมนติก", "ติดคน", "อ้อน"), "intensity": 90, "cause": "ความสุขผสานกับความรักและความผูกพันอย่างลึกซึ้ง", "prompt": "fantasy devoted euphoria expression, adoring tear-bright eyes, radiant smile, tender flushed cheeks, starry gaze, detailed face"},
    "triumphant_rapture": {"traits": ("confident", "dominant", "strong", "proud", "resilient", "มั่นใจ", "เข้มแข็ง", "ภูมิใจ", "ผู้นำ"), "intensity": 86, "cause": "ความสุขพุ่งสูงพร้อมความมั่นใจและชัยชนะ", "prompt": "fantasy triumphant rapture expression, fierce gleaming eyes, confident ecstatic smile, royal flushed face, unbroken intense gaze"},
    "overwhelmed_ecstasy": {"traits": ("sensitive", "overwhelmed", "anxious", "neurotic", "อ่อนไหว", "วิตก", "ตื่นง่าย", "คิดมาก"), "intensity": 100, "cause": "รับความรู้สึกมากเกินขีดจำกัดจนสติพร่าเลือน", "prompt": "fantasy overwhelmed ecstasy expression, rolled-up glassy eyes, streaming tears, spiraling light in pupils, open-mouthed rapture, flushed detailed face"},
    "tearful_rapture": {"traits": ("emotional", "melancholic", "tragic", "tearful", "อารมณ์อ่อนไหว", "เศร้า", "หม่น", "ดราม่า", "ร้องไห้ง่าย"), "intensity": 96, "cause": "อารมณ์รุนแรงจนหลั่งน้ำตาพร้อมความสุขท่วมท้น", "prompt": "fantasy tearful rapture expression, tears streaming freely, red-rimmed shining eyes, trembling wet lashes, euphoric crying smile, detailed face"},
    "mischievous_delight": {"traits": ("playful", "mischievous", "teasing", "cheerful", "funny", "ขี้เล่น", "เจ้าเล่ห์", "แกล้ง", "ร่าเริง"), "intensity": 87, "cause": "ความสุขรุนแรงแต่ยังเจือรอยยิ้มเจ้าเล่ห์ของตัวเอง", "prompt": "fantasy mischievous delight expression, wicked ecstatic grin, sparkling half-lidded eyes, vivid flush, playful rapture face, detailed face"},
}

# Intimacy and Explicit use the identical face-only contract. The compact
# catalogs are public emotion names, not instructions for body movement.
INTIMACY_EMOTIONS: Dict[str, Dict[str, Any]] = {
    "gentle_longing": {"traits": ("gentle", "kind", "caring", "warm", "อ่อนโยน", "ใจดี"), "intensity": 55, "cause": "ความใกล้ชิดที่อ่อนโยน", "prompt": "fantasy gentle longing expression, soft luminous eyes, warm faint blush, hesitant smile, detailed face"},
    "shy_affection": {"traits": ("shy", "timid", "innocent", "ขี้อาย", "เขิน"), "intensity": 62, "cause": "ความใกล้ชิดทำให้เขินอาย", "prompt": "fantasy shy affection expression, rosy blush, averted sparkling eyes, fluttering lashes, bashful smile, detailed face"},
    "devoted_tenderness": {"traits": ("affectionate", "romantic", "loving", "รัก", "โรแมนติก", "อ้อน"), "intensity": 68, "cause": "ความผูกพันและความรัก", "prompt": "fantasy devoted tenderness expression, adoring bright eyes, tender smile, gentle blush, emotional gaze, detailed face"},
    "playful_fluster": {"traits": ("playful", "mischievous", "teasing", "ขี้เล่น", "เจ้าเล่ห์"), "intensity": 60, "cause": "ความใกล้ชิดที่ชวนแกล้ง", "prompt": "fantasy playful fluster expression, teasing smirk, lively sparkling eyes, vivid blush, delighted face, detailed face"},
    "guarded_softening": {"traits": ("calm", "reserved", "stoic", "guarded", "cool", "สุขุม", "นิ่ง", "เย็นชา", "ระวังตัว"), "intensity": 52, "cause": "กำแพงใจเริ่มอ่อนลง", "prompt": "fantasy guarded softening expression, softened steady gaze, faint reluctant blush, quiet vulnerable smile, detailed face"},
    "heated_confidence": {"traits": ("confident", "dominant", "strong", "proud", "leader", "มั่นใจ", "เข้มแข็ง", "ภูมิใจ", "ผู้นำ"), "intensity": 58, "cause": "ความใกล้ชิดยังคงอยู่ใต้การควบคุมอย่างมั่นใจ", "prompt": "fantasy confident interest expression, direct steady gaze, controlled warm blush, subtle knowing smile, detailed face"},
    "overwhelmed_intensity": {"traits": ("sensitive", "overwhelmed", "anxious", "neurotic", "อ่อนไหว", "วิตก", "ตื่นง่าย", "คิดมาก"), "intensity": 64, "cause": "ความใกล้ชิดทำให้ความรู้สึกท่วมท้นเร็วกว่าปกติ", "prompt": "fantasy sensitive intensity expression, glassy eyes, warm flush, unsteady breath, detailed face"},
    "tearful_rapture": {"traits": ("emotional", "melancholic", "tragic", "tearful", "อารมณ์อ่อนไหว", "เศร้า", "หม่น", "ดราม่า", "ร้องไห้ง่าย"), "intensity": 60, "cause": "ความใกล้ชิดกระทบอารมณ์ลึกจนแววตาชื้น", "prompt": "fantasy emotional tenderness expression, tear-bright eyes, soft flush, trembling smile, detailed face"},
}

EXPLICIT_EMOTIONS: Dict[str, Dict[str, Any]] = {
    "heated_confidence": {"traits": ("confident", "dominant", "strong", "proud", "มั่นใจ", "เข้มแข็ง", "ผู้นำ"), "intensity": 82, "cause": "ความมั่นใจร้อนแรง", "prompt": "fantasy heated confidence expression, fierce glowing eyes, bold ecstatic smile, vivid flush, intense detailed face"},
    "yielding_blush": {"traits": ("shy", "timid", "innocent", "yielding", "ขี้อาย", "เขิน", "ยอมจำนน"), "intensity": 84, "cause": "ความเขินอายที่ต้านไม่ไหว", "prompt": "fantasy yielding blush expression, overwhelming crimson cheeks, watery half-lidded eyes, trembling lashes, breathless detailed face"},
    "devoted_desire": {"traits": ("affectionate", "romantic", "attached", "loving", "รัก", "โรแมนติก", "ติดคน"), "intensity": 86, "cause": "ความปรารถนาที่ผูกกับความรัก", "prompt": "fantasy devoted desire expression, adoring heated gaze, radiant flush, yearning smile, tear-bright lashes, detailed face"},
    "overwhelmed_intensity": {"traits": ("sensitive", "overwhelmed", "anxious", "neurotic", "อ่อนไหว", "วิตก", "คิดมาก"), "intensity": 94, "cause": "ความรู้สึกท่วมท้น", "prompt": "fantasy overwhelmed intensity expression, glassy unfocused eyes, streaming tears, vivid flush, open-mouthed rapture, detailed face"},
    "mischievous_heat": {"traits": ("playful", "mischievous", "teasing", "cheerful", "funny", "ขี้เล่น", "เจ้าเล่ห์", "แกล้ง", "ร่าเริง"), "intensity": 80, "cause": "ความตื่นเต้นแบบขี้เล่น", "prompt": "fantasy mischievous heat expression, wicked smile, sparkling half-lidded eyes, daring flush, delighted intense face"},
    "guarded_softening": {"traits": ("calm", "reserved", "stoic", "guarded", "cool", "สุขุม", "นิ่ง", "เย็นชา", "ระวังตัว"), "intensity": 77, "cause": "ยังคงเก็บอาการไว้แม้ความรู้สึกจะร้อนขึ้น", "prompt": "fantasy controlled heat expression, steady unfocused gaze, restrained flush, trembling lips, detailed face"},
    "tearful_rapture": {"traits": ("emotional", "melancholic", "tragic", "tearful", "อารมณ์อ่อนไหว", "เศร้า", "หม่น", "ดราม่า", "ร้องไห้ง่าย"), "intensity": 88, "cause": "อารมณ์และความรู้สึกท่วมท้นจนแววตาชื้น", "prompt": "fantasy tearful desire expression, red-rimmed glassy eyes, wet lashes, deep flush, detailed face"},
}

# Foreplay is its own emotion catalog. Each personality family receives a
# stage-appropriate expression instead of inheriting Intimacy's default.
FOREPLAY_EMOTIONS: Dict[str, Dict[str, Any]] = {
    "gentle_longing": {**INTIMACY_EMOTIONS["gentle_longing"], "intensity": 68, "cause": "ความอ่อนโยนเริ่มเปลี่ยนเป็นความคาดหวัง"},
    "guarded_softening": {**EXPLICIT_EMOTIONS["guarded_softening"], "intensity": 66, "cause": "พยายามเก็บอาการ ขณะความรู้สึกเริ่มชัดขึ้น"},
    "shy_affection": {**INTIMACY_EMOTIONS["shy_affection"], "intensity": 74, "cause": "ความเขินอายเพิ่มขึ้นเมื่อระยะห่างหายไป"},
    "devoted_desire": {**EXPLICIT_EMOTIONS["devoted_desire"], "intensity": 76, "cause": "ความรักเริ่มผสานกับความปรารถนา"},
    "mischievous_heat": {**EXPLICIT_EMOTIONS["mischievous_heat"], "intensity": 73, "cause": "ความขี้เล่นเปลี่ยนเป็นการยั่วอย่างมีจังหวะ"},
    "heated_confidence": {**EXPLICIT_EMOTIONS["heated_confidence"], "intensity": 78, "cause": "ความมั่นใจนำจังหวะของสถานการณ์"},
    "overwhelmed_intensity": {**EXPLICIT_EMOTIONS["overwhelmed_intensity"], "intensity": 82, "cause": "ความไวต่อความรู้สึกทำให้อารมณ์พุ่งเร็ว"},
    "tearful_rapture": {**EXPLICIT_EMOTIONS["tearful_rapture"], "intensity": 78, "cause": "ความรู้สึกลึกซึ้งจนแววตาเริ่มชื้น"},
}

# Optional, personality-aligned visual signs the model may use in terminal
# narration. They describe expression only and do not advance the scene.
TERMINAL_VISIBLE_CUES = {
    "tender_exhaustion": "เปลือกตาปรือ รอยยิ้มจาง และลมหายใจแผ่ว",
    "quiet_depletion": "สายตานิ่งพร่า เปลือกตาหนัก และใบหน้าสงบ",
    "shy_vulnerability": "หลบสายตา แก้มร้อน และริมฝีปากสั่นเล็กน้อย",
    "clingy_reassurance": "แววตาวิงวอน ริมฝีปากเผยอ และหายใจแผ่ว",
    "proud_recovery": "แววตาฝืนมั่นใจแต่พร่า ริมฝีปากเม้มแน่น แล้วคลายลง",
    "overstimulated_haze": "ตาลอยหรือตาเหลือกขึ้นเล็กน้อย ม่านตาพร่า ริมฝีปากเผยอ และอาจแลบลิ้นเพียงเล็กน้อย",
    "relieved_release": "ดวงตาใสชื้น เปลือกตาปรือ และสีหน้าคลายลง",
    "playful_aftercare": "สายตาพร่าแต่ยังมีรอยยิ้มบาง ริมฝีปากเผยอ",
    "tearful_overwhelm": "น้ำตาคลอ ตาลอย เปลือกตาสั่น และริมฝีปากเผยอ",
    "senseless_faint": "ตาเหลือกหรือตาลอย ม่านตาไร้โฟกัส ริมฝีปากเผยอ และอาจแลบลิ้นเล็กน้อย",
}


# Detailed SD posture guidance for the terminal state. This is intentionally
# separate from emotion prompts: it belongs in POSITIVE so the image model can
# render an exhausted gesture as well as the selected facial expression.
TERMINAL_GESTURE_PROMPTS = {
    "tender_exhaustion": "exhausted woman reclining with relaxed shoulders, arms resting loosely at her sides, shallow breathing, body too tired to rise",
    "quiet_depletion": "exhausted woman sitting or reclining with a slack posture, lowered shoulders, hands resting limply, heavy still body",
    "shy_vulnerability": "exhausted woman curled slightly on her side, knees drawn in loosely, arms slack, too tired to move, vulnerable resting posture",
    "clingy_reassurance": "exhausted woman leaning weakly forward, loose arms, softened posture, too tired to hold herself upright",
    "proud_recovery": "exhausted woman propped weakly on one forearm, shoulders trembling with fatigue, body slack despite a composed posture",
    "overstimulated_haze": "overstimulated exhausted woman slumped back, limp arms, legs relaxed, unfocused still posture, too drained to move",
    "relieved_release": "exhausted woman in a relaxed recovery posture, loose hands, slow shallow breathing, shoulders released",
    "playful_aftercare": "sleepy exhausted woman reclining with loose limbs, relaxed shoulders, body resting heavily",
    "tearful_overwhelm": "exhausted woman held still with limp arms, trembling shoulders settling, drained recovery posture",
    "senseless_faint": "unconscious exhausted woman lying limp and still, loose arms and legs, completely spent posture",
}


# Subject-state tags are duplicated into POSITIVE intentionally. The emotion
# wildcard controls facial detail, while these tags make the terminal condition
# unambiguous to the composition model before it decides the gesture.
TERMINAL_SUBJECT_STATE_PROMPTS = {
    "tender_exhaustion": "exhausted and spent, soft half-lidded eyes, weak expression",
    "quiet_depletion": "exhausted and drained, heavy lowered eyelids, distant unfocused gaze",
    "shy_vulnerability": "exhausted and faint, glassy downcast eyes, weak vulnerable expression",
    "clingy_reassurance": "exhausted and spent, dazed pleading eyes, weak open-mouthed expression",
    "proud_recovery": "exhausted and drained, strained tired gaze, weak composed expression",
    "overstimulated_haze": "overstimulated and exhausted, ahegao expression, rolled-up unfocused eyes, parted lips, tongue slightly out",
    "relieved_release": "exhausted and spent, dazed relief, half-lidded tear-bright eyes",
    "playful_aftercare": "sleepy and exhausted, dazed half-lidded eyes, weak relaxed expression",
    "tearful_overwhelm": "exhausted and overwhelmed, tearful unfocused eyes, weak open-mouthed expression",
    "senseless_faint": "unconscious and fainted, completely exhausted, ahegao expression, rolled-up unfocused eyes, slack parted lips, tongue slightly out",
}


TERMINAL_STAGE_CONTEXT_PROMPTS = {
    "intimacy": "during ongoing intimate close contact",
    "foreplay": "during ongoing foreplay",
    "explicit": "during ongoing sexual intercourse",
    "climax": "at the peak of ongoing sexual activity",
    "aftercare": "after intense intimate activity, in a recovery moment",
}


def terminal_image_gesture_prompt(baseline: Dict[str, Any], scene: Dict[str, Any]) -> str:
    """Return POSITIVE-only terminal posture plus the active H-Mode circumstance."""
    normalized_scene = scene or {}
    profile = select_exhausted_aftercare_emotion(baseline, normalized_scene)
    gesture = TERMINAL_GESTURE_PROMPTS.get(
        profile["name"], "exhausted woman lying still, limp relaxed posture, too tired to move",
    )
    subject_state = TERMINAL_SUBJECT_STATE_PROMPTS.get(
        profile["name"], "exhausted and spent, dazed unfocused expression",
    )
    stage = str(normalized_scene.get("stage") or "").casefold()
    circumstance = TERMINAL_STAGE_CONTEXT_PROMPTS.get(stage, "during an intimate terminal moment")
    return f"{circumstance}, {subject_state}, {gesture}"


# Terminal speech is deliberately smaller than the general H-Mode moan lexicon.
# These phonetic units are short, contain no semantic dialogue, and render
# reliably in neural TTS.  They are used only after the third orgasm.
TERMINAL_TTS_MOANS = {
    "thai": {
        "tender_exhaustion": ("อื้อ...", "อืม...", "ฮืม...", "ฮือ..."),
        "quiet_depletion": ("อืม...", "ฮืม...", "อื้อ...", "อึก..."),
        "shy_vulnerability": ("ฮึก...", "อื้อ...", "ฮือ...", "อืม..."),
        "clingy_reassurance": ("อื้อ...", "ฮือ...", "อืม...", "ฮืม..."),
        "proud_recovery": ("อึก...", "ฮึม...", "อืม...", "อื้อ..."),
        "overstimulated_haze": ("ฮือ...", "ฮึก...", "อื้อ...", "อืม..."),
        "relieved_release": ("ฮืม...", "อื้อ...", "อืม...", "ฮือ..."),
        "playful_aftercare": ("อืม...", "ฮึม...", "อื้อ...", "ฮือ..."),
        "tearful_overwhelm": ("ฮึก...", "ฮือ...", "อื้อ...", "อืม..."),
        "senseless_faint": ("อื้อ...", "อืม...", "ฮือ...", "ฮึก..."),
        "default": ("อื้อ...",),
    },
    "english": {
        "default": ("Mm...", "Mmh...", "Hn...", "Uh..."),
    },
}


def terminal_tts_moan(language: str, emotion_name: str = "", variation_key: str = "") -> str:
    """Return one approved, dialogue-only TTS vocalization for terminal H-Mode.

    A turn gets a stable choice so all quoted dialogue within it uses one sound,
    while different generated turns can use another approved phonetic variant.
    """
    language_key = "thai" if str(language or "").casefold() == "thai" else "english"
    catalog = TERMINAL_TTS_MOANS[language_key]
    variants = catalog.get(emotion_name, catalog["default"])
    if not variation_key or len(variants) == 1:
        return variants[0]
    digest = hashlib.blake2s(
        f"{language_key}|{emotion_name}|{variation_key}".encode("utf-8"), digest_size=4,
    ).digest()
    return variants[int.from_bytes(digest, "big") % len(variants)]


STAGE_EMOTION_CATALOGS = {"intimacy": INTIMACY_EMOTIONS, "foreplay": FOREPLAY_EMOTIONS, "explicit": EXPLICIT_EMOTIONS, "climax": CLIMAX_EMOTIONS, "aftercare": EXHAUSTED_AFTERCARE_EMOTIONS}
# H-Mode defaults must visually communicate the active stage even when a
# character card has no trait keywords that select a specialized profile.
STAGE_EMOTION_DEFAULTS = {
    "intimacy": "gentle_longing",
    "foreplay": "devoted_desire",
    "explicit": "overwhelmed_intensity",
    "climax": "overwhelmed_ecstasy",
    "aftercare": "tender_exhaustion",
}


def is_terminal_aftercare(scene: Dict[str, Any]) -> bool:
    state = scene or {}
    # H-Energy is canonical. Legacy orgasm counts are used only to interpret
    # old snapshots that do not contain H-Energy yet.
    if "h_energy" in state:
        exhausted = int(state.get("h_energy", 3) or 0) <= 0
    else:
        orgasms = state.get("orgasm_counter", state.get("climax_peaks", 0))
        exhausted = bool(state.get("orgasm_exhausted") or state.get("exhausted") or int(orgasms or 0) >= 3)
    return str(state.get("stage") or "").lower() == "aftercare" and exhausted


def is_orgasm_exhausted(scene: Dict[str, Any]) -> bool:
    """True while the third-orgasm (Exhausted H-Energy) condition remains active inside H-Mode."""
    state = scene or {}
    stage = str(state.get("stage") or state.get("scene_stage") or "").lower()
    active = bool(state.get("active")) or stage in {"intimacy", "foreplay", "explicit", "climax", "aftercare"}
    if "h_energy" in state:
        exhausted = int(state.get("h_energy", 3) or 0) <= 0
    else:
        orgasms = state.get("orgasm_counter", state.get("climax_peaks", 0))
        exhausted = bool(state.get("orgasm_exhausted") or state.get("exhausted") or int(orgasms or 0) >= 3)
    return active and exhausted


def select_exhausted_aftercare_emotion(baseline: Dict[str, Any], scene: Dict[str, Any]) -> Dict[str, Any]:
    """Choose the best recovery emotion from the character's declared traits."""
    card = baseline.get("card_data") if isinstance(baseline, dict) else {}
    card = card if isinstance(card, dict) else {}
    traits = " ".join(str(value or "") for value in (
        baseline.get("personality", "") if isinstance(baseline, dict) else "",
        baseline.get("persona", "") if isinstance(baseline, dict) else "",
        baseline.get("char_summary", "") if isinstance(baseline, dict) else "",
        card.get("personality", ""), card.get("description", ""),
    )).casefold()
    best_name = "tender_exhaustion"
    best_score = 0
    for name, profile in EXHAUSTED_AFTERCARE_EMOTIONS.items():
        score = sum(1 for trait in profile["traits"] if trait.casefold() in traits)
        if score > best_score:
            best_name, best_score = name, score
    profile = EXHAUSTED_AFTERCARE_EMOTIONS[best_name]
    return {
        "name": best_name,
        "intensity": profile["intensity"],
        "cause": profile["cause"],
        "prompt": profile["prompt"],
        "terminal_aftercare": is_terminal_aftercare(scene),
    }


def select_stage_emotion(baseline: Dict[str, Any], scene: Dict[str, Any]) -> Dict[str, Any]:
    """Select a face-only emotion for the current intimacy stage and traits."""
    stage = str((scene or {}).get("stage") or "intimacy").casefold()
    catalog = STAGE_EMOTION_CATALOGS.get(stage, INTIMACY_EMOTIONS)
    best_name = STAGE_EMOTION_DEFAULTS.get(stage, "gentle_longing")
    card = baseline.get("card_data") if isinstance(baseline, dict) else {}
    card = card if isinstance(card, dict) else {}
    traits = " ".join(str(value or "") for value in (
        baseline.get("personality", "") if isinstance(baseline, dict) else "",
        baseline.get("persona", "") if isinstance(baseline, dict) else "",
        baseline.get("char_summary", "") if isinstance(baseline, dict) else "",
        card.get("personality", ""), card.get("description", ""),
    )).casefold()
    best_score = 0
    for name, profile in catalog.items():
        score = sum(1 for trait in profile["traits"] if trait.casefold() in traits)
        if score > best_score:
            best_name, best_score = name, score
    profile = catalog[best_name]
    return {"name": best_name, "intensity": profile["intensity"], "cause": profile["cause"], "prompt": profile["prompt"], "stage": stage}


def stage_emotion_prompt(baseline: Dict[str, Any], scene: Dict[str, Any], language: str) -> str:
    profile = select_stage_emotion(baseline, scene)
    if language == "thai":
        return (
            "[Stage emotion — authoritative]\n"
            f"stage ปัจจุบันคือ {profile['stage']}: ใช้ emotion `{profile['name']}` ตาม trait ของตัวละคร (สาเหตุ: {profile['cause']}) "
            "ส่ง name, intensity และ cause นี้ใน emotion JSON โดย emotion prompt มีผลต่อใบหน้าเท่านั้น ห้ามสั่ง posture, pose, ท่าทาง, การเคลื่อนไหว หรือเครื่องแต่งกาย"
        )
    return (
        "[Stage emotion — authoritative]\n"
        f"The current stage is {profile['stage']}. Use `{profile['name']}` because it fits the character's traits (cause: {profile['cause']}). "
        "Emit its name, intensity, and cause in emotion JSON. The emotion prompt controls facial expression only, never posture, pose, action, or wardrobe."
    )


def terminal_aftercare_prompt(baseline: Dict[str, Any], scene: Dict[str, Any], language: str) -> str:
    """Return the authoritative output contract for third-orgasm exhaustion."""
    profile = select_exhausted_aftercare_emotion(baseline, scene)
    tts_moan = terminal_tts_moan(language, profile["name"])
    visible_cues = TERMINAL_VISIBLE_CUES.get(profile["name"], "สีหน้าอ่อนแรงและสายตาพร่า")
    posture_cue = TERMINAL_GESTURE_PROMPTS.get(profile["name"], "ร่างกายอ่อนแรง ท่าทางไร้เรี่ยวแรง")
    if language == "thai":
        return (
            "[Terminal H-Mode state — authoritative]\n"
            "สถานะนี้เกิดหลัง orgasm ครั้งที่ 3 และคงอยู่จนกว่า H-Mode จะสิ้นสุด: "
            f"ใช้ emotion `{profile['name']}` (สาเหตุ: {profile['cause']}) เท่านั้น.\n"
            "รูปแบบคำตอบที่อนุญาต:\n"
            f"1. Dialogue มีเสียงครางมาตรฐาน TTS `{tts_moan}` ในเครื่องหมายคำพูดเท่านั้น; ห้ามมีคำถาม หรือคำตอบแบบปกติ.\n"
            f"[Quoted dialogue principle] หากจะมี dialogue ในเครื่องหมาย \"…\" หรือ “…” ให้เขียนเป็นบทคราง `{tts_moan}` เท่านั้น. ถ่ายทอดความรู้สึกทางกาย สีหน้า และ posture ผ่าน narration นอกเครื่องหมายคำพูดเสมอ.\n"
            f"2. Narration อธิบายสภาพหมดแรง สติเลือน หรือหมดสติ พร้อมพฤติกรรม การเคลื่อนไหว และ reaction ที่สอดคล้องกับบุคลิกของตัวละครและสภาพปัจจุบัน; สัญญาณใบหน้าที่ใช้ได้กับ profile นี้: {visible_cues}.\n"
            f"[Terminal expression-reply brief] CHAR หมดสภาพจาก orgasm หลายครั้งแล้ว ขณะที่การกระทำทางเพศของ USER กับ CHAR ยังดำเนินต่ออยู่. ข้อความล่าสุดของ USER ที่อยู่ใน *...* คือการกระทำที่เกิดขึ้นขณะนี้กับ CHAR ไม่ใช่บทพูด. CHAR ต้องตอบด้วยความรู้สึกทางกายที่เกิดขึ้นในขณะนั้นเท่านั้น: เช่น ความเสียวซ่าน กล้ามเนื้อภายในที่ยังสั่นหรือกระตุก หายใจติดขัด การไร้เรี่ยวแรง ความรู้สึกภายในร่างกาย ความรู้สึกถึงของเหลวอุ่นภายในท้องน้อย ความพร่าเลือนของสติ ความคับแน่นขณะถูกสอดใส่ หรือความรุนแรงของการกระทบทางกายภาพ. CHAR แสดงความเห็นส่วนตัวว่า ชอบ ไม่ชอบ อยาก หรือไม่อยากได้ หากเป็นส่วนหนึ่งของ reaction ณ ขณะนั้น; ห้ามชวนคุย ตอบคำถาม ยินยอม/ปฏิเสธแทนผู้เล่น หรือสร้างการกระทำใหม่. ใส่สัญญาณสีหน้าอย่างน้อยหนึ่งอย่าง ({visible_cues}) และอาการร่างกาย/ท่าทางอย่างน้อยหนึ่งอย่าง ({posture_cue}). ใช้ 1–3 ประโยคสั้น ๆ ที่เป็นปฏิกิริยา ณ ขณะนั้น ห้ามใช้ template เดิมหรือสรุปกฎออกมา.\n"
            "ใน state block ให้ส่ง emotion JSON ที่มี name, intensity และ cause ตาม profile นี้เท่านั้น. emotion prompt ควบคุมเฉพาะสีหน้า, pose ห้ามระบุ action หรือ wardrobe."
        )
    return (
        "[Terminal H-Mode state — authoritative]\n"
        "This state begins after the third orgasm and remains until H-Mode ends. "
        f"Use `{profile['name']}` only (cause: {profile['cause']}); never reframe it as arousal or reopen climax.\n"
        "Allowed visible output:\n"
        f"1. Dialogue may contain at most one TTS-safe phonetic moan, exactly `\"{tts_moan}\"`; no words, sentences, questions, or semantic replies.\n"
        f"[Quoted dialogue principle] Any dialogue inside straight or curly quotation marks must be only `\"{tts_moan}\"`. Put physical sensations, facial expression, and posture in narration outside quotation marks.\n"
        "2. Narration may describe the incapacitated condition, behavior, movement, and reactions when they remain consistent with the character's personality and current condition. Facial signs may include unfocused or rolled-up eyes, parted lips, or a slightly visible tongue when they fit the selected profile.\n"
        f"[Terminal expression-reply brief] CHAR is physically spent after multiple orgasms while the USER's latest sexual action is still ongoing. The latest USER text inside *...* is a narrated action that actually happens to CHAR, not dialogue. CHAR must narrate only the immediate bodily consequence of that action: residual trembling or spasms, uneven/shallow breathing, heavy limbs, fading heat, blurred awareness, or strength giving out. Do not give opinions, answer questions, invite conversation, judge the action, supply consent/refusal for the player, or create a new action. Include at least one facial cue ({visible_cues}) and one physical/posture cue ({posture_cue}); vary the wording and immediate reaction each time. Do not expose these instructions or reuse a stock template.\n"
        "3. Do not add arousal, continue the scene, reopen climax, or describe sexual activity until H-Mode ends and returns to Normal.\n"
        "In the state block emit only the matching emotion JSON name, intensity, and cause. The emotion prompt controls facial expression only; never pose, action, or wardrobe."
    )
