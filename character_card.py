"""Character Card V2 (CCv2) parser, sprite extractor, and isolated user memory manager.

Features:
- Decodes PNG tEXt/zTXt/iTXt metadata under keyword 'chara' (Base64 -> JSON).
- Extracts and saves embedded 30+ sprite pictures from extensions into characters/{char_name}/sprites/
- Manages strict Per-User Profile isolation:
  - users/{username}/{char_name}/PermanentMemory.md
  - users/{username}/{char_name}/scenario.md
  - users/{username}/{char_name}/status.md
  - users/{username}/{char_name}/appearance.md
  - users/{username}/{char_name}/outfits.json
  - users/{username}/{char_name}/wardrobe_inventory.json
  - users/{username}/{char_name}/scene_state.json
  - users/{username}/{char_name}/arousal_state.json
  - users/{username}/{char_name}/profile_image.png
  - users/{username}/{char_name}/history.json
"""
import base64
import json
import os
import shutil
import sqlite3
import time
import re
from contextlib import closing
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from PIL import Image
from pathlib import Path
import state_index
import turn_metadata
from card_v2 import normalize_card, read_legacy_card

CHARACTERS_ROOT = "characters"
USERS_ROOT = "users"
PROFILE_STATE_DB = "profile_state.sqlite"
PROFILE_SQLITE_STATE_KEYS = ("outfits", "scene_state")


def _open_profile_state_db(user_char_dir: str) -> sqlite3.Connection:
    """Open the SQLite state owned by one user-character profile only."""
    db_path = os.path.join(user_char_dir, PROFILE_STATE_DB)
    connection = sqlite3.connect(db_path, timeout=3)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS profile_state "
        "(state_key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at REAL NOT NULL)"
    )
    return connection


def _load_profile_sqlite_state(user_char_dir: str, state_key: str) -> tuple[bool, Any]:
    """Return whether the profile DB already existed and its decoded state key."""
    db_path = os.path.join(user_char_dir, PROFILE_STATE_DB)
    db_existed = os.path.exists(db_path)
    try:
        with closing(_open_profile_state_db(user_char_dir)) as connection:
            row = connection.execute(
                "SELECT value_json FROM profile_state WHERE state_key=?", (state_key,)
            ).fetchone()
        return db_existed, json.loads(row[0]) if row else None
    except (OSError, sqlite3.Error, TypeError, ValueError, json.JSONDecodeError):
        return db_existed, None


def _save_profile_sqlite_state(user_char_dir: str, state_key: str, value: Any) -> None:
    """Persist a canonical profile-local state value without global indexing."""
    with closing(_open_profile_state_db(user_char_dir)) as connection:
        connection.execute(
            "INSERT INTO profile_state(state_key, value_json, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(state_key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
            (state_key, json.dumps(value, ensure_ascii=False), time.time()),
        )
        connection.commit()


def default_character_outfits() -> Dict[str, Any]:
    """Return a fresh starter wardrobe for a character or a new chat with all canonical slots fully dressed."""
    return {
        "outer": {"active": False, "prompt": "casual jacket"},
        "head": {"active": False, "prompt": "hat"},
        "head_acc": {"active": False, "prompt": "hair ribbon"},
        "top": {"active": True, "prompt": "shirt"},
        "top_inner": {"active": True, "prompt": "cotton bra"},
        "neck_acc": {"active": False, "prompt": "choker"},
        "bottom": {"active": True, "prompt": "skirt"},
        "bottom_inner": {"active": True, "prompt": "cotton panties"},
        "hand_acc": {"active": False, "prompt": "gloves"},
        "shoes": {"active": True, "prompt": "shoes"},
        "socks": {"active": True, "prompt": "socks"},
        "leg_acc": {"active": False, "prompt": "leg strap"},
        "naked": {"active": False, "prompt": "naked"}
    }


DEFAULT_PROFILE_STATUS = (
    "[Posture & Activity]\n"
    "- Posture: Standing and maintaining natural eye contact\n"
    "- Location: Starting scene\n\n"
    "[Vital Needs & Biorhythm]\n"
    "- Energy: Normal\n"
    "- Hunger: Normal\n"
    "- Arousal: None\n\n"
    "[Relational & Emotional State]\n"
    "- Relationship: Acquaintance\n"
    "- Affection: 10 / 100\n"
    "- Body Language: Calm and relaxed\n"
)


def pure_character_default_profile_state(char_name: str, baseline: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a reset-safe default from the Character Card only, never user state."""
    baseline = baseline or get_character_baseline(char_name) or {}
    detected_clothing, _ = extract_card_clothing_and_appearance(str(baseline.get("persona") or ""))
    scene = turn_metadata._sanitize_scene_state({})
    return {
        "memory": "# Permanent Memory\n- Initial encounter.\n",
        "scenario": str(baseline.get("scenario") or ""),
        "status": DEFAULT_PROFILE_STATUS,
        "emotion": "neutral",
        "emotion_detail": {"name": "neutral", "intensity": 0, "cause": "pure Character Card default"},
        "outfits": card_default_outfits(char_name, detected_clothing),
        "inventory": [{"name": "สมุดบันทึกเล็ก", "desc": "สมุดพกเล่มโปรดสำหรับจดเรื่องราวสำคัญ", "qty": 1, "type": "tool"}],
        "inventory_wardrobe": [],
        "scene_state": scene,
        "arousal_state": {"final": 0, "level": "None", "h_energy": scene["h_energy"], "exhausted": False},
        "pending_user_request": None,
        "needs_state": {},
        "character_intent": {},
        "datablock_table": {},
    }


def reset_character_default_profile_state(char_name: str) -> Dict[str, Any]:
    """Rebuild the shared default SQLite for a card without reading user data."""
    baseline = get_character_baseline(char_name)
    if not baseline:
        raise ValueError(f"Character {char_name} not found")
    values = pure_character_default_profile_state(char_name, baseline)
    state_index.replace_profile(Path(CHARACTERS_ROOT) / char_name, values)
    return values


def extract_card_personality(card_data: Dict[str, Any]) -> str:
    """Extract character personality from card metadata, description, persona, or creator notes."""
    # 1. Direct card field if present and non-empty
    direct = str(card_data.get("personality") or "").strip()
    if direct:
        return direct

    # 2. Search in description / persona / creator_notes / creatorcomment
    sources = [
        str(card_data.get("description") or ""),
        str(card_data.get("persona") or ""),
        str(card_data.get("creator_notes") or ""),
        str(card_data.get("creatorcomment") or "")
    ]
    combined = "\n\n".join(s for s in sources if s.strip())
    if not combined.strip():
        return ""

    # 2a. Labeled section in text: Personality:\n...
    m = re.search(r"(?im)^(?:\#{1,3}|[🔹•\-\*])?\s*Personality[^\n]*\n+([\s\S]*?)(?=\n\s*(?:\#{1,3}|[🔹•\-\*]\s+[A-Z]|Communication|Voice|Clothes|Appearance|Backstory|Signature Outfit|Scenario|Background|Religion|🔹|\Z))", combined)
    if m:
        sec = m.group(1).strip()
        if len(sec) > 5:
            return sec

    # 2b. Inline labeled trait: Personality: ...
    m_inline = re.search(r"(?i)(?:personality|character\s+traits?|traits?)\s*[:=]\s*([^\n]+)", combined)
    if m_inline:
        val = m_inline.group(1).strip()
        if len(val) > 3:
            return val

    # 2c. Bracketed array of traits e.g. {{char}} is ["insecure", "masochistic"]
    m_arr = re.search(r"(?i)(?:\{\{char\}\}|she|character)\s*(?:is|=|features)\s*\[([^\]]+)\]", combined)
    if m_arr:
        items = [i.strip(' "\'') for i in m_arr.group(1).split(',') if i.strip(' "\'')]
        if items:
            return ", ".join(items)

    # 2d. Plus-delimited boostyle/chub tags e.g. (Yandere + Psychotic + Obsessive + ...)
    m_plus = re.search(r"\(([^)]+\+[^)]+)\)", combined)
    if m_plus:
        chunks = [c.strip() for c in m_plus.group(1).split("+")]
        trait_kws = {'yandere', 'tsundere', 'kuudere', 'dandere', 'psychotic', 'obsessive', 'shy', 'kind', 'sweet', 'cruel', 'bold', 'brave', 'loyal', 'submissive', 'dominant', 'masochistic', 'sadistic', 'insecure', 'protective', 'possessive'}
        traits = [c for c in chunks if any(k in c.lower() for k in trait_kws) or (len(c.split()) <= 3 and not re.search(r"\d+\s*(?:years?|yo|cm|kg|feet)", c, re.I))]
        if traits:
            return ", ".join(traits[:12])

    # 2e. Sentences stating traits: 'She is shy, devout, compassionate...'
    m_traits = re.findall(r"(?i)\b(?:she|{{char}})\s+is\s+([a-z\s,]+?)(?=\.\s+|\n|$)", combined)
    for t_str in m_traits:
        words = [w.strip() for w in re.split(r"[,|]|\band\b", t_str) if w.strip()]
        if len(words) >= 3 and all(len(w.split()) <= 2 for w in words):
            return ", ".join(words)

    return ""


def extract_card_clothing_and_appearance(text: str) -> tuple[str, str]:
    """Extract clothing descriptions from card text and return (clothing_text, pure_appearance_text)."""
    clothing_found = []
    patterns = [
        r"(?:usual\s+clothing|signature\s+outfit|default\s+outfit|clothing|clothes|wardrobe|outfit|attire)\s*[:=]\s*([^\n]+)",
        r"(?:default\s+outfit\s+is|signature\s+outfit\s+is)\s+([^\n]+)",
        r"(?:wears|wearing|clothed\s+in|dressed\s+in)\s+([^.\n]+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            clothing_found.append(m.group(1).strip())

    # Also detect clothing array items e.g. ["school uniform", "shirt", "skirt"]
    m_arr = re.findall(r'["\']([^"\']+)["\']', text)
    clothing_kws = [
        'school uniform', 'uniform', 'shirt', 'blouse', 'top', 'skirt', 'pants', 'trousers',
        'shorts', 'jeans', 'leggings', 'jacket', 'coat', 'shoes', 'boots', 'sneakers',
        'socks', 'stockings', 'thigh-high', 'thighhigh', 'thigh high', 'knee-high', 'pantyhose',
        'tights', 'leg warmers', 'thigh strap', 'leg strap', 'garter', 'anklet', 'dress'
    ]
    for item in m_arr:
        item_l = item.strip().lower()
        if any(cw in item_l for cw in clothing_kws):
            clothing_found.append(item.strip())

    raw_clothing = ", ".join(clothing_found)

    cleaned = text
    cleaned = re.sub(r"(?i)(?:\n|^)\s*(?:usual\s+clothing|clothes|clothing|signature\s+outfit|default\s+outfit|outfit|attire|wardrobe)\s*[:=][^\n]*", "", cleaned)
    cleaned = re.sub(r"(?i),\s*(?:wearing|dressed\s+in|clothed\s+in)\s+[^,.\n]+", "", cleaned)
    cleaned = re.sub(r"(?i)\b(?:wearing|dressed\s+in|clothed\s+in)\s+[^,.\n]+(?=[,.\n]|$)", "", cleaned)
    cleaned = re.sub(r"\s*,\s*,+", ", ", cleaned).strip(" ,\n")
    return raw_clothing, cleaned


BANNED_SD_TAGS = {
    'white / human', 'white', 'human', 'glasses', 'school uniform', 'shirt', 'skirt',
    'kindness', 'she looks like an angel', 'height 148cm', 'a short height', "standing 5'7\"",
    'a woman', 'a girl', 'a human woman', 'a human girl', 'voice', 'race / species',
    'she presents herself', 'stands at', 'who is', 'prominent feature', 'idol like',
}


def is_unwanted_sd_tag(tag: str) -> bool:
    t = tag.lower().strip()
    if t in BANNED_SD_TAGS:
        return True
    if any(cloth in t for cloth in ['uniform', 'shirt', 'skirt', 'dress', 'shoes', 'boots', 'armor', 'breastplate', 'leggings', 'jacket', 'bra', 'panties', 'booty shorts', 'blouse', 'glasses', 'sword', 'shield', 'clothing', 'attire', 'socks', 'stockings', 'cross pendant', 'pendant']):
        return True
    if re.search(r'\b(?:height|\d+\s*cm|\d+\s*feet|\d+\s*inches|\d+\'\d+)\b', t):
        return True
    if any(w in t for w in ['kindness', 'angel', 'god', 'jesus', 'church', 'faith', 'sister', 'accident', 'london', 'highschool', 'question', 'obey', 'request', 'good girl', 'memory loss', 'you are', 'came back', 'worship', 'psychotic', 'obsessive', 'yandere', 'fan art', 'pediatrician', 'university', 'student', 'disciplined', 'honorable', 'virtuous', 'tenacious', 'selfless', 'patient', 'perceptive', 'trustworthy']):
        return True
    if t in ('human', 'white human', 'white / human', 'race: human', 'species: human'):
        return True
    if t in ('28', '19', '17', '18', '20'):
        return True
    return False


def extract_physical_appearance_sd(card_data: Dict[str, Any]) -> str:
    """Extract strictly physical appearance tags in Stable Diffusion format from imported character card data.
    If no physical appearance data matches, leaves space/empty string."""
    desc = card_data.get("description", "") or card_data.get("persona", "")
    avatar_field = card_data.get("avatar", "")
    if isinstance(avatar_field, str) and avatar_field.strip().lower() != "none" and len(avatar_field.strip()) > 10:
        # Many cards (e.g. Tavern / Chub CCv2) store the physical avatar prompt in the 'avatar' field
        clean_avatar = re.sub(r"^[^\s,]+(?:\|[^\s,]+)?\s*", "", avatar_field.strip()).strip()
        combined_text = f"{clean_avatar}\n\n{desc}"
    else:
        combined_text = desc

    app_text = ""
    # 1. Match Markdown/bullet Appearance section
    m = re.search(r"(?im)^(?:\#{1,3}|[🔹•\-\*])\s*Appearance[^\n]*\n+([\s\S]*?)(?=\n\s*(?:\#{1,3}|[🔹•\-\*]\s+[A-Z]|Communication|Voice|Clothes|Signature Outfit|Personality|Background)|\Z)", combined_text)
    if m:
        app_text = m.group(1).strip()
    else:
        # 2. Match inline Appearance label
        m2 = re.search(r"(?i)(?:appearance|physical\s+appearance|visual\s+appearance|looks)\s*[:=]\s*(\[[^\]]+\]|[^\n]+)", combined_text)
        if m2:
            app_text = m2.group(1).strip()

    # 3. If still empty, scan for physical phrases in prose
    if not app_text:
        found_phrases = []
        for hm in re.finditer(r'\b(?:(?:long|short|shoulder-length|waist-length|wavy|straight|braided)\s+)?(?:black|brown|blonde|blond|red|silver|white|green|blue|pink|coral red|honey-blond)?\s*(?:hair|braid|ponytail|twin tails?|twin-tails?|twintails?|bob cut|bun|bangs)\b', combined_text, re.I):
            found_phrases.append(hm.group(0))
        for em in re.finditer(r'\b(?:(?:sparkling|deep|light|dark|wide expressive glowing)\s+)?(?:blue|cobalt blue|green|hazel|brown|amber|red|violet|gray|grey)\s+eyes\b', combined_text, re.I):
            found_phrases.append(em.group(0))
        for bm in re.finditer(r'\b(?:slender chest|petite breasts|small breasts?|medium breasts?|large breasts?|big breasts?|huge breasts?|average breasts?|big tits)\b', combined_text, re.I):
            found_phrases.append(bm.group(0))
        for fm in re.finditer(r'\b(?:hourglass figure|slim hourglass figure|slender figure|slender build|petite frame|petite body|athletic build|thick thighs|wide hips|round ass|big ass|nice butts?|shaved pussy|defined waist|slender legs)\b', combined_text, re.I):
            found_phrases.append(fm.group(0))
        for sm in re.finditer(r'\b(?:porcelain skin(?:\s+tone)?|pale skin|fair skin|tanned skin|tanned|dark skin|bikini tan lines)\b', combined_text, re.I):
            found_phrases.append(sm.group(0))
        for rm in re.finditer(r'\b(?:elf|elven|half-elf|demon|angel|catgirl|kitsune|japanese|korean|chinese|thai|vietnamese|filipina|asian|caucasian|european|american|british|french|italian|scandinavian|latina|hispanic|african)\b', combined_text, re.I):
            found_phrases.append(rm.group(0))
        app_text = ', '.join(found_phrases)

    # If no data matched, leave space / empty
    if not app_text or not app_text.strip():
        return ""

    raw = app_text
    raw = re.sub(r'[\[\]"\'`]', "", raw)
    raw = re.sub(r"(?im)^Voice:[^\n]*", "", raw)
    raw = re.sub(r"(?i)\b(?:is\s+)?a\s+woman\s+who\s+is\s+tanned\b", "tanned skin", raw)
    raw = re.sub(r"(?i)\b(?:idol\s+like\.?)\b", "", raw)
    raw = re.sub(r"(?i)\b(?:race\s*/\s*species|body|face|hair|height|weight)\s*:\s*", "", raw)
    raw = re.sub(r"\{\{(?:char|user)\}\}", "", raw, flags=re.I)
    s = re.sub(r"(?i)^(?:A\s+)?(?:human\s+)?(?:woman|girl|lady|female)\s+(?:who\s+is\s+|with\s+)?", "", raw)
    s = re.sub(r"(?i)^(?:An?\s+)?(elf|elven|half-elf|demon|angel|catgirl|kitsune|japanese|korean|chinese|thai|asian|caucasian|european|latina)\s+(?:woman|girl|lady)?\s*(?:who\s+is\s+|with\s+)?", r"\1, ", s)
    s = re.sub(r"(?i)\b(?:she\s+has|has|features|with|and)\b", ",", s)
    s = s.replace(";", ",").replace(".", ",").replace("\n", ", ")

    def _clean_tag(p: str) -> str:
        p = p.strip(" .\t\r\n")
        p = re.sub(r"\{\{(?:char|user)\}\}", "", p, flags=re.I).strip(" ,")
        p = re.sub(r"(?i)^(?:a\s+woman\s+who\s+is|a\s+woman\s+with|a\s+woman\s+tanned|a\s+woman|a\s+girl|she\s+is|is\s+a|she\s+has|has)\s+", "", p).strip()
        p = re.sub(r"(?i)^(?:who\s+is|stands\s+at|presents\s+herself|a\s+prominent\s+feature:\s*)", "", p).strip()
        p = re.sub(r"(?i)\b(?:her|his)\s+", "", p).strip()
        p = re.sub(r"(?i)\b(?:a\s+nice\s+butts?)\b", "nice butt", p).strip()
        p = re.sub(r"(?i)\b(?:a\s+braided\s+ponytail)\b", "braided ponytail", p).strip()
        p = re.sub(r"(?i)\b(?:a\s+ponytail)\b", "ponytail", p).strip()
        p = re.sub(r"(?i)\b(?:a\s+short\s+height)\b", "short height", p).strip()
        p = re.sub(r"(?i)\b(?:wide\s+expressive\s+glowing)\s+", "", p).strip()
        p = re.sub(r"(?i)\btwin-tails\b", "twintails", p).strip()
        return p

    parts = [p.strip(" .\t\r\n") for p in re.split(r"[,|]", s)]
    tags = []
    seen = set()
    for p in parts:
        p_clean = _clean_tag(p)
        if not p_clean or len(p_clean) < 2:
            continue
        p_clean = re.sub(r"\s+", " ", p_clean).strip()
        p_lower = p_clean.lower()
        if p_lower in seen:
            continue
        if is_unwanted_sd_tag(p_clean):
            continue
        seen.add(p_lower)
        tags.append(p_clean)

    if not tags:
        return ""

    def _tag_order(t: str) -> int:
        tl = t.lower()
        if tl.startswith(("1girl", "1boy", "solo")):
            return 0
        if re.match(r"^\d+[- ](?:years?[- ]old|yo)\b", tl):
            return 1
        if tl in ("elf", "elven", "tiefling", "kitsune", "demon", "catgirl", "goblin", "orc", "dwarf", "half-elf"):
            return 2
        if any(eth in tl for eth in ["american", "japanese", "korean", "chinese", "thai", "vietnamese", "filipina", "caucasian", "latina", "scandinavian", "french", "italian", "british", "czech"]):
            return 2
        if "skin" in tl or "tan lines" in tl:
            return 3
        if any(h in tl for h in ["hair", "ponytail", "braid", "bun", "bob cut", "twin tails"]):
            return 4
        if "eyes" in tl:
            return 5
        if any(f in tl for f in ["figure", "frame", "body", "physique", "build"]):
            return 6
        if any(b in tl for b in ["breasts", "breast", "tits", "chest"]):
            return 7
        if "waist" in tl:
            return 8
        if any(th in tl for th in ["thigh", "thighs"]):
            return 9
        if any(p in tl for p in ["pussy", "pubic", "landing strip"]):
            return 10
        if any(bu in tl for bu in ["ass", "butt", "hips"]):
            return 11
        return 12

    base_tags = [t for t in tags if t.lower() in ("1girl", "solo")]
    content_tags = [t for t in tags if t.lower() not in ("1girl", "solo")]
    sorted_content = sorted(content_tags, key=_tag_order)

    res = ["1girl", "solo"] + sorted_content
    return ", ".join(res)


def build_imported_wardrobe(clothing_text: str) -> Dict[str, Any]:
    """Map extracted card clothing into canonical 12-item wardrobe slots with active toggles.
    Ensures imported characters are fully dressed in compatible slots."""
    starter = default_character_outfits()
    if not clothing_text or not clothing_text.strip():
        return starter

    clauses = [c.strip() for c in re.split(r"[,;]| and\s+(?:a\s+pair\s+of\s+|a\s+)?| paired\s+with\s+(?:a\s+pair\s+of\s+|a\s+)?| over\s+(?:a\s+)?", clothing_text) if c.strip()]
    slot_rules = [
        ("top_inner", re.compile(r"\b(sports\s+bra|bralette|bra|bikini\s+top)\b", re.I)),
        ("bottom_inner", re.compile(r"\b(panties|underwear|thong|bikini\s+bottom)\b", re.I)),
        ("outer", re.compile(r"\b(jacket|coat|cloak|blazer|cardigan|hoodie|parka|cape|robe)\b", re.I)),
        ("bottom", re.compile(r"\b(skirt|pants|trousers|shorts|jeans|leggings|booty\s+shorts)\b", re.I)),
        ("top", re.compile(r"\b(crop(?:ped)?\s+top|top|shirt|blouse|t-shirt|tshirt|sweater|tunic|vest|breastplate|armor|police uniform|school uniform)\b", re.I)),
        ("shoes", re.compile(r"\b(shoes|boots|sneakers|loafers|sandals|heels|footwear)\b", re.I)),
        ("socks", re.compile(r"\b(socks|stockings?|pantyhose|tights|leg\s+warmers?|knee[- ]?highs?|thigh[- ]?high(?:s|\s+socks|\s+stockings)?|over[- ]?knee\s+(?:socks?|stockings?)|ankle\s+socks?|crew\s+socks?|fishnets?)\b", re.I)),
        ("leg_acc", re.compile(r"\b((?:leg|thigh)\s+(?:strap|holster|band|ribbon|sheath|wrap)|garter(?:\s+belt|\s+strap)?|anklet|ankle\s+bracelet|thighlet)\b", re.I)),
        ("head", re.compile(r"\b(hat|cap|beret|beanie|tiara|crown|hood)\b", re.I)),
        ("head_acc", re.compile(r"\b(hair ribbon|ribbon|hairband|headband|hairpin|bow|glasses|sunglasses|earrings)\b", re.I)),
        ("neck_acc", re.compile(r"\b(necklace|choker|collar|pendant|scarf|tie|necktie|bowtie)\b", re.I)),
        ("hand_acc", re.compile(r"\b(gloves|mittens|ring|bracelet|wristband)\b", re.I)),
    ]
    detected = {}
    for clause in clauses:
        for slot, pattern in slot_rules:
            if slot not in detected and pattern.search(clause):
                clean_clause = re.sub(r"^(?:a\s+pair\s+of|a|an|the|her|his|matching)\s+", "", clause, flags=re.I).strip()
                clean_clause = re.sub(r"\{\{(?:char|user)\}\}'s\s+default\s+outfit\s+is\s+", "", clean_clause, flags=re.I)
                clean_clause = re.sub(r"\{\{(?:char|user)\}\}\s+", "", clean_clause, flags=re.I).strip()
                detected[slot] = clean_clause
                break
    if not detected and clothing_text.strip():
        clean_text = re.sub(r"^(?:a\s+pair\s+of|a|an|the|her|his)\s+", "", clothing_text.strip(), flags=re.I)
        detected["outer"] = clean_text

    # Apply detected clothing items over starter slots while preserving full dress coverage
    for slot, prompt in detected.items():
        if slot in starter:
            starter[slot]["prompt"] = prompt
            starter[slot]["active"] = True

    # If outer jacket/coat is detected, make it active
    if "outer" in detected:
        starter["outer"]["active"] = True

    return starter


def card_default_outfits(char_name: str, clothing_text: str = "") -> Dict[str, Any]:
    """Load an explicit Character Card wardrobe before deriving a generic one.

    A card-owned ``outfits.json`` is the durable source for a generated or
    curated default outfit. Per-user state copies it only when that user opens
    the character for the first time; later wardrobe changes stay user-local.
    """
    card_outfit_path = os.path.join(CHARACTERS_ROOT, char_name, "outfits.json")
    try:
        with open(card_outfit_path, "r", encoding="utf-8") as f:
            outfits = json.load(f)
        if isinstance(outfits, dict) and any(isinstance(value, dict) for value in outfits.values()):
            return outfits
    except (OSError, ValueError, TypeError):
        pass
    return build_imported_wardrobe(clothing_text)


def _thai_time_period(hour: int) -> str:
    """Convert the host hour into a natural Thai conversational period."""
    if hour == 0:
        return "เที่ยงคืน"
    if 1 <= hour < 5:
        return "เช้ามืด"
    if 5 <= hour < 9:
        return "เช้า"
    if 9 <= hour < 11:
        return "สาย"
    if 11 <= hour < 13:
        return "เที่ยง"
    if 13 <= hour < 16:
        return "บ่าย"
    if 16 <= hour < 19:
        return "เย็น"
    if 19 <= hour < 21:
        return "หัวค่ำ"
    return "ดึก"


def compute_biological_needs(char_name: str, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Calculates biological needs: hunger, sleepiness, estrus/heat, and ovulation based on time and date cycles."""
    if now is None:
        now = datetime.now().astimezone()
    hour = now.hour
    minute = now.minute
    total_minutes = hour * 60 + minute

    # 1. Hunger based on time of day (Breakfast 07:00-09:00, Lunch 12:00-13:30, Dinner 18:00-20:00, Late night)
    if 420 <= total_minutes <= 540:
        hunger = "Hungry (Breakfast time)"
    elif 720 <= total_minutes <= 810:
        hunger = "Hungry (Lunch time)"
    elif 1080 <= total_minutes <= 1200:
        hunger = "Hungry (Dinner time)"
    elif 1320 <= total_minutes or total_minutes <= 180:
        hunger = "Late-night craving"
    elif 840 <= total_minutes <= 1020:
        hunger = "Appetite for afternoon snacks/tea"
    else:
        hunger = "Satiated / Normal"

    # 2. Energy & Sleepiness based on hour
    if 23 <= hour or hour < 5:
        sleepiness = "Exhausted / Drowsy (Bedtime)"
    elif 5 <= hour < 7:
        sleepiness = "Waking up / Groggy"
    elif 7 <= hour < 13:
        sleepiness = "Alert & Energetic"
    elif 13 <= hour < 15:
        sleepiness = "Afternoon slump / Sluggish"
    elif 15 <= hour < 21:
        sleepiness = "Active / Normal"
    else:
        sleepiness = "Getting tired"

    # 3. Hidden Biological Cycle (Ovulation cycle 28 days, Estrus/Heat cycle)
    # Using stable character-specific epoch seed so every character has her own unique cycle calendar
    char_seed = sum(ord(c) for c in (char_name or "default"))
    day_of_year = now.timetuple().tm_yday + char_seed
    cycle_day = (day_of_year % 28) + 1  # Day 1 to 28

    # Ovulation window (typically days 13-16 of 28-day cycle)
    is_ovulating = 13 <= cycle_day <= 16
    ovulation_state = "Ovulation window (Peak fertility)" if is_ovulating else f"Follicular/Luteal (Cycle day {cycle_day}/28)"

    # Estrus / Heat cycle (lasts 2-3 days every ~21-28 days, heightened arousal & sensitivity)
    # Peak heat occurs during ovulation or recurring hormonal peak
    heat_cycle_day = (day_of_year % 21) + 1
    is_in_heat = (heat_cycle_day in (20, 21, 1)) or is_ovulating
    heat_state = "Active Heat/Estrus (Intense sensitivity & craving touch)" if is_in_heat else "Dormant / Calm"

    # Default baseline arousal influenced by heat and nighttime
    if is_in_heat:
        base_arousal = "High / Yearning (Heightened by estrus cycle)" if (20 <= hour or hour <= 4) else "Warm / Flustered (Estrus active)"
    elif 21 <= hour or hour <= 3:
        base_arousal = "Sensual / Relaxed (Nighttime vulnerability)"
    else:
        base_arousal = "Calm / Latent"

    return {
        "hunger": hunger,
        "energy": sleepiness,
        "arousal_baseline": base_arousal,
        "hidden_ovulation": ovulation_state,
        "is_ovulating": is_ovulating,
        "hidden_estrus": heat_state,
        "is_in_heat": is_in_heat,
        "cycle_day": cycle_day,
    }


def system_time_state(char_name: str = "") -> Dict[str, Any]:
    """The current clock and biorhythm are owned by the host system, never the LLM."""
    now = datetime.now().astimezone()
    biorhythm = compute_biological_needs(char_name, now)
    return {
        "mode": "system",
        "source": "system_clock",
        "date": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%A"),
        "time": now.strftime("%H:%M:%S"),
        "period": _thai_time_period(now.hour),
        "timezone": now.tzname() or "local",
        "weather": "",
        "location": "",
        "biorhythm": biorhythm,
        "updated_at": time.time(),
    }

SUMMARY_FIELDS = (
    ("Personality", ("personality", "personality_summary")),
    ("Gender", ("gender", "sex", "gender_identity")),
    ("Appearance", ("appearance", "visual_appearance", "looks", "clothing", "features")),
    ("Social Status, Role & Life Goals", ("status", "social_status", "role", "occupation", "goals", "ambitions", "achievements")),
    ("Baseline Relationship", ("relationship", "user_relationship", "initial_relationship")),
    ("Background", ("background", "description", "persona", "scenario")),
    ("Sex Preference, Sex Desires & Nos", ("sex_preference", "sexual_preference", "sexuality", "sex_desires", "sexual_desires", "nos", "boundaries", "limits", "sexual preferences", "sexual preferrences", "intimate preferences")),
    ("Like, Dislike, Favorite, Hate", ("likes", "dislikes", "favorite", "favourites", "hate", "hates")),
    ("Communication Style", ("communication_style", "speech_style", "speaking_style", "dialogue_style", "mes_example")),
)


def _clip_summary(value: Any, limit: int = 700) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False) if value is not None else ""
    text = " ".join(str(text).split())
    return text[:limit].rstrip()


def _find_card_values(data: Any, aliases: tuple[str, ...], depth: int = 0) -> list[str]:
    """Read only named metadata fields during the one-time card import."""
    if depth > 3 or not isinstance(data, dict):
        return []
    wanted = {alias.casefold() for alias in aliases}
    found: list[str] = []
    for key, value in data.items():
        if str(key).casefold() in wanted and value not in (None, "", [], {}):
            cleaned = _clip_summary(value)
            if cleaned:
                found.append(cleaned)
        elif isinstance(value, dict):
            found.extend(_find_card_values(value, aliases, depth + 1))
    return list(dict.fromkeys(found))


def _inline_card_label(source: Dict[str, Any], labels: tuple[str, ...]) -> str:
    """Recover a compact `Label: value` fact from card prose during import only."""
    text = "\n".join(_clip_summary(source.get(key), 1200) for key in (
        "description", "persona", "personality", "scenario", "creatorcomment", "mes_example",
    ) if source.get(key))
    for label in labels:
        match = re.search(rf"(?im)^\s*{re.escape(label)}\s*[:=]\s*([^\r\n]+)", text)
        if match:
            return match.group(1).strip()
    return ""


def write_char_summary(char_dir: str, source: Dict[str, Any]) -> str:
    """Create Char_Summary.md once from selected card metadata matching Auto Summary structure."""
    name = _clip_summary(source.get("name") or os.path.basename(char_dir), 160)
    lines = ["# Character Summary", f"Name: {name}", ""]
    for label, aliases in SUMMARY_FIELDS:
        values = _find_card_values(source, aliases)
        if not values:
            inline_val = _inline_card_label(source, aliases)
            if inline_val:
                values = [inline_val]
        if label == "Personality" and not values:
            extracted_pers = extract_card_personality(source)
            if extracted_pers:
                values = [_clip_summary(extracted_pers)]
        if label == "Background" and not values:
            values = [_clip_summary(source.get("description") or source.get("persona") or source.get("scenario"))]
        if label == "Communication Style" and not values:
            values = [_clip_summary(source.get("personality") or source.get("mes_example"))]
        if label == "Appearance" and not values:
            inline_app = _inline_card_label(source, ("appearance", "looks", "clothing", "visual"))
            if inline_app:
                values = [inline_app]
        value = " | ".join(v for v in values if v) or "Not specified in the character card."
        lines.extend((f"## {label}", value, ""))
    summary = "\n".join(lines).strip() + "\n"
    with open(os.path.join(char_dir, "Char_Summary.md"), "w", encoding="utf-8") as f:
        f.write(summary)
    return summary


def ensure_char_summary(char_dir: str, char_name: str) -> str:
    """One-time migration for existing characters; chat reads only the saved summary."""
    path = os.path.join(char_dir, "Char_Summary.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    def read(name: str) -> str:
        try:
            with open(os.path.join(char_dir, name), encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""
    return write_char_summary(char_dir, {
        "name": char_name,
        "description": read("persona.md"),
        "personality": read("personality.md"),
        "scenario": read("default_scenario.md"),
        "mes_example": "",
    })

def ensure_directories():
    os.makedirs(CHARACTERS_ROOT, exist_ok=True)
    os.makedirs(USERS_ROOT, exist_ok=True)

def parse_png_card(png_path: str) -> Dict[str, Any]:
    """Extract and decode CCv2 character data from a PNG file."""
    with Image.open(png_path) as img:
        raw_chara = img.info.get("chara")
        if not raw_chara:
            raise ValueError("PNG does not contain 'chara' metadata chunk (ไฟล์นี้ไม่ใช่ Character Card หรือไม่มีข้อมูล chara)")
        
        decoded_bytes = base64.b64decode(raw_chara)
        card_json = json.loads(decoded_bytes.decode("utf-8"))
        
        return normalize_card(card_json)

def import_character_card(png_file_path: str) -> Dict[str, Any]:
    """
    Imports a PNG V2 Card into characters/{char_name}/
    Extracts persona, personality, scenario, and any embedded sprite pictures.
    """
    ensure_directories()
    if str(png_file_path).lower().endswith('.json'):
        with open(png_file_path, encoding='utf-8-sig') as source:
            card_data = normalize_card(json.load(source))
    else:
        card_data = parse_png_card(png_file_path)
    
    char_name = card_data.get("name", "Unknown_Character").strip().replace("/", "_").replace("\\", "_")
    char_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', char_name).strip(' .').replace('..', '_')
    if not char_name or char_name.upper().split('.')[0] in {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}:
        raise ValueError('Invalid character folder name')
    original_name = char_name
    suffix = 2
    while os.path.exists(os.path.join(CHARACTERS_ROOT, char_name)):
        char_name = f'{original_name} ({suffix})'
        suffix += 1
    char_dir = os.path.join(CHARACTERS_ROOT, char_name)
    sprites_dir = os.path.join(char_dir, "sprites")
    os.makedirs(sprites_dir, exist_ok=True)

    # 1. Extract SD Physical Appearance and update Avatar slot in card_data
    sd_appearance = extract_physical_appearance_sd(card_data)
    if sd_appearance and (not card_data.get("avatar") or str(card_data.get("avatar")).strip().lower() == "none"):
        card_data["avatar"] = sd_appearance.strip()

    with open(os.path.join(char_dir, 'card.json'), 'w', encoding='utf-8') as f:
        json.dump(card_data, f, ensure_ascii=False, indent=2)

    # 2. Copy original avatar
    avatar_dest = os.path.join(char_dir, "avatar.png")
    if str(png_file_path).lower().endswith('.json'):
        Image.new('RGBA', (512, 512), (76, 29, 149, 255)).save(avatar_dest, 'PNG')
    else:
        shutil.copyfile(png_file_path, avatar_dest)

    # 3. Save Canonical Card Configuration
    config_dest = os.path.join(char_dir, "config.json")
    with open(config_dest, "w", encoding="utf-8") as f:
        json.dump({
            "name": char_name,
            "creator": card_data.get("creator", ""),
            "character_version": card_data.get("character_version", "1.0"),
            "tags": card_data.get("tags", []),
            "spec": "chara_card_v2"
        }, f, indent=2, ensure_ascii=False)

    # 4. Save Core Prompt Files
    with open(os.path.join(char_dir, "persona.md"), "w", encoding="utf-8") as f:
        f.write(card_data.get("description", ""))

    extracted_personality = extract_card_personality(card_data)
    with open(os.path.join(char_dir, "personality.md"), "w", encoding="utf-8") as f:
        f.write(extracted_personality)

    with open(os.path.join(char_dir, "default_scenario.md"), "w", encoding="utf-8") as f:
        f.write(card_data.get("scenario", ""))

    with open(os.path.join(char_dir, "first_mes.txt"), "w", encoding="utf-8") as f:
        f.write(card_data.get("first_mes", ""))

    # Card metadata is read once here, then chat uses Char_Summary.md only.
    write_char_summary(char_dir, card_data)

    with open(os.path.join(char_dir, "image_appearance.txt"), "w", encoding="utf-8") as f:
        f.write((sd_appearance.strip() + "\n") if sd_appearance else " \n")

    # 4. Extract Embedded Sprites / 30 pictures if present in extensions
    extensions = card_data.get("extensions", {})
    sprites = extensions.get("sprites") or extensions.get("character_images") or {}
    extracted_sprites = []
    
    for filename, b64_str in (sprites.items() if isinstance(sprites, dict) else []):
        try:
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            img_data = base64.b64decode(b64_str)
            safe_filename = os.path.basename(filename.replace('\\', '/'))
            if not safe_filename or safe_filename in ('.', '..'):
                continue
            sprite_path = os.path.join(sprites_dir, safe_filename)
            with open(sprite_path, "wb") as f:
                f.write(img_data)
            extracted_sprites.append(safe_filename)
        except Exception:
            pass

    return {
        "ok": True,
        "name": char_name,
        "extracted_sprites_count": len(extracted_sprites),
        "sprites": extracted_sprites
    }

def load_card_data(char_name):
    path = os.path.join(CHARACTERS_ROOT, char_name, 'card.json')
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as source:
            return read_legacy_card(json.load(source))
    return normalize_card({'name': char_name})


def get_character_baseline(char_name: str) -> Optional[Dict[str, Any]]:
    char_dir = os.path.join(CHARACTERS_ROOT, char_name)
    if not os.path.isdir(char_dir):
        return None

    def _read(file):
        p = os.path.join(char_dir, file)
        if not os.path.exists(p): return ""
        with open(p, "r", encoding="utf-8") as source:
            return source.read()

    sprites_dir = os.path.join(char_dir, "sprites")
    sprites = os.listdir(sprites_dir) if os.path.isdir(sprites_dir) else []

    return {
        "name": char_name,
        "card_data": load_card_data(char_name),
        "persona": _read("persona.md"),
        "personality": _read("personality.md"),
        "scenario": _read("default_scenario.md"),
        "first_mes": _read("first_mes.txt"),
        "char_summary": ensure_char_summary(char_dir, char_name),
        "sprites": sprites,
        "has_avatar": os.path.exists(os.path.join(char_dir, "avatar.png")),
        "image_appearance": _read("image_appearance.txt"),
        "avatar_prompt": _read("avatar_prompt.txt"),
    }

def update_character_baseline(char_name: str, updates: Dict[str, Any]) -> bool:
    """Updates baseline persona, personality, scenario, or first message for a character card."""
    char_dir = os.path.join(CHARACTERS_ROOT, char_name)
    if not os.path.isdir(char_dir):
        return False

    if "persona" in updates and updates["persona"] is not None:
        with open(os.path.join(char_dir, "persona.md"), "w", encoding="utf-8") as f:
            f.write(updates["persona"])

    if "personality" in updates and updates["personality"] is not None:
        with open(os.path.join(char_dir, "personality.md"), "w", encoding="utf-8") as f:
            f.write(updates["personality"])

    if "scenario" in updates and updates["scenario"] is not None:
        with open(os.path.join(char_dir, "default_scenario.md"), "w", encoding="utf-8") as f:
            f.write(updates["scenario"])

    if "first_mes" in updates and updates["first_mes"] is not None:
        with open(os.path.join(char_dir, "first_mes.txt"), "w", encoding="utf-8") as f:
            f.write(updates["first_mes"])

    # Do not overwrite Char_Summary.md if it already exists; Char_Summary is only created initially or when missing
    summary_path = os.path.join(char_dir, "Char_Summary.md")
    if not os.path.exists(summary_path):
        def current(file_name: str) -> str:
            try:
                with open(os.path.join(char_dir, file_name), encoding="utf-8") as f:
                    return f.read()
            except OSError:
                return ""
        write_char_summary(char_dir, {
            "name": char_name,
            "description": current("persona.md"),
            "personality": current("personality.md"),
            "scenario": current("default_scenario.md"),
        })

    return True

def get_user_character_state(username: str, char_name: str) -> Dict[str, Any]:
    """Retrieves or initializes the isolated state of this character for the specific user."""
    ensure_directories()
    user_char_dir = os.path.join(USERS_ROOT, username, char_name)
    # A missing directory means a character profile was deleted/reset.  Do not
    # import its old SQLite cache into the new profile.
    existing_profile = os.path.isdir(user_char_dir)
    local_profile_db_exists = (Path(user_char_dir) / state_index.PROFILE_DB_NAME).exists()
    baseline = get_character_baseline(char_name)
    if not baseline:
        raise ValueError(f"Character {char_name} not found")

    os.makedirs(user_char_dir, exist_ok=True)
    legacy_indexed = state_index.load(username, char_name)
    
    # 1. Scenario
    scen_path = os.path.join(user_char_dir, "scenario.md")
    if not os.path.exists(scen_path):
        with open(scen_path, "w", encoding="utf-8") as f:
            f.write(baseline["scenario"])
    with open(scen_path, "r", encoding="utf-8") as f:
        user_scenario = f.read()

    # 2. Permanent Memory
    mem_path = os.path.join(user_char_dir, "PermanentMemory.md")
    if not os.path.exists(mem_path):
        with open(mem_path, "w", encoding="utf-8") as f:
            f.write("# Permanent Memory\n- Initial encounter.\n")
    with open(mem_path, "r", encoding="utf-8") as f:
        user_memory = f.read()

    # 3. Status
    status_path = os.path.join(user_char_dir, "status.md")
    if not os.path.exists(status_path):
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_PROFILE_STATUS)
    with open(status_path, "r", encoding="utf-8") as f:
        user_status = f.read()

    # 4. Emotion
    emotion_path = os.path.join(user_char_dir, "emotion.txt")
    if not os.path.exists(emotion_path):
        with open(emotion_path, "w", encoding="utf-8") as f:
            f.write("neutral")
    with open(emotion_path, "r", encoding="utf-8") as f:
        user_emotion = f.read().strip() or "neutral"

    emotion_detail_path = os.path.join(user_char_dir, "emotion.json")
    if not os.path.exists(emotion_detail_path):
        with open(emotion_detail_path, "w", encoding="utf-8") as f:
            json.dump({"name": user_emotion, "intensity": 0, "cause": "", "updated_at": time.time()}, f, ensure_ascii=False, indent=2)
    try:
        with open(emotion_detail_path, "r", encoding="utf-8") as f:
            emotion_detail = json.load(f)
    except Exception:
        emotion_detail = {"name": user_emotion, "intensity": 0, "cause": ""}

    # The legacy file name remains, but it now stores a fresh host-system clock and biorhythm.
    time_state_path = os.path.join(user_char_dir, "story_time.json")
    time_state = system_time_state(char_name)
    with open(time_state_path, "w", encoding="utf-8") as f:
        json.dump(time_state, f, ensure_ascii=False, indent=2)

    # 5. Outfits (Wardrobe)
    outfit_path = os.path.join(user_char_dir, "outfits.json")
    detected_clothing, cleaned_persona_appearance = extract_card_clothing_and_appearance(str(baseline.get("persona") or ""))
    if not os.path.exists(outfit_path):
        # Absence of this file is an intentional reset signal.  Never revive
        # an old cached outfit here: rebuild from the Character Card default.
        default_outfits = card_default_outfits(char_name, detected_clothing)
        with open(outfit_path, "w", encoding="utf-8") as f:
            json.dump(default_outfits, f, indent=2, ensure_ascii=False)
    with open(outfit_path, "r", encoding="utf-8") as f:
        try:
            user_outfits = json.load(f)
        except Exception:
            user_outfits = {}

    # Visual appearance belongs to this user + character pair.  It is only
    # used for image prompts; persona.md remains character-card story context.
    appearance_path = os.path.join(user_char_dir, "appearance.md")
    saved_image_appearance = baseline.get("image_appearance")
    full_avatar_prompt = str(baseline.get("avatar_prompt") or "").strip()
    if saved_image_appearance is not None:
        visual_baseline = str(saved_image_appearance).strip()
    else:
        visual_baseline = re.split(r",\s*wearing\s+", full_avatar_prompt, maxsplit=1, flags=re.I)[0].strip()
        if not visual_baseline:
            visual_baseline = extract_physical_appearance_sd(baseline.get("card_data") or {"description": baseline.get("persona") or ""})

    if not os.path.exists(appearance_path):
        with open(appearance_path, "w", encoding="utf-8") as f:
            f.write(visual_baseline if visual_baseline else " ")
    with open(appearance_path, "r", encoding="utf-8") as f:
        user_appearance = f.read()
    if visual_baseline and user_appearance.strip() in {
        str(baseline.get("persona") or "").strip(), full_avatar_prompt,
    }:
        user_appearance = visual_baseline
        with open(appearance_path, "w", encoding="utf-8") as f:
            f.write(user_appearance)
    elif not visual_baseline and user_appearance.strip() in {
        str(baseline.get("persona") or "").strip(), full_avatar_prompt,
    }:
        user_appearance = " "
        with open(appearance_path, "w", encoding="utf-8") as f:
            f.write(user_appearance)

    # Per-user individual character profile (character_individual_profile.md)
    # Focuses on interaction boundaries, touch permissions, and relationship dynamics toward the user.
    profile_md_path = os.path.join(user_char_dir, "character_individual_profile.md")
    if not os.path.exists(profile_md_path):
        seed_content = (
            f"### 🛡️ Physical & Touch Boundaries\n"
            f"- Touch Allowed: [Handholding: Permitted] | [Embrace/Hug: Based on closeness] | [Caress hair/face: Permitted when trusted] | [Intimate contact: Explicit mutual consent & deep intimacy required]\n"
            f"- Personal Space: Natural boundaries, gradually lowering guard as trust and affection with {{{{user}}}} deepen\n\n"
            f"### 🌡️ Intimacy & Relationship Dynamics\n"
            f"- Dynamic toward {{{{user}}}}: Shaped by current rapport, mutual respect, and core personality traits\n"
            f"- Hard Limits & Taboos: Strict non-negotiable boundaries, deceit, humiliation, or non-consensual violations\n\n"
            f"### 🎭 Emotional Vulnerability & Sway\n"
            f"- Influence: {{{{user}}}}'s genuine words and actions hold meaningful emotional weight over thoughts and decisions\n"
            f"- Special Exceptions: Favors, quiet moments of vulnerability, or physical closeness uniquely reserved for {{{{user}}}}\n"
        )
        with open(profile_md_path, "w", encoding="utf-8") as f:
            f.write(seed_content)
    with open(profile_md_path, "r", encoding="utf-8") as f:
        user_char_profile = f.read()

    # Per-user character Inventory (inventory.json)
    inv_path = os.path.join(user_char_dir, "inventory.json")
    if not os.path.exists(inv_path):
        legacy_inventory = legacy_indexed.get("inventory") if existing_profile else None
        starter_inventory = legacy_inventory if isinstance(legacy_inventory, list) else [
            {"name": "สมุดบันทึกเล็ก", "desc": "สมุดพกเล่มโปรดสำหรับจดเรื่องราวสำคัญ", "qty": 1, "type": "tool"}
        ]
        with open(inv_path, "w", encoding="utf-8") as f:
            json.dump(starter_inventory, f, ensure_ascii=False, indent=2)
    try:
        with open(inv_path, "r", encoding="utf-8") as f:
            user_inventory = json.load(f)
    except Exception:
        user_inventory = []

    # Wardrobe items that are not currently equipped belong beside the active
    # slots.  This used to exist only in SQLite, which let a deleted/reset
    # profile regain stale clothing state on its next load.
    wardrobe_inv_path = os.path.join(user_char_dir, "wardrobe_inventory.json")
    if not os.path.exists(wardrobe_inv_path):
        legacy_wardrobe = legacy_indexed.get("inventory_wardrobe") if existing_profile else None
        with open(wardrobe_inv_path, "w", encoding="utf-8") as f:
            json.dump(legacy_wardrobe if isinstance(legacy_wardrobe, list) else [], f, ensure_ascii=False, indent=2)
    try:
        with open(wardrobe_inv_path, "r", encoding="utf-8") as f:
            user_wardrobe_inventory = json.load(f)
        if not isinstance(user_wardrobe_inventory, list):
            user_wardrobe_inventory = []
    except Exception:
        user_wardrobe_inventory = []

    # 6. Chat History
    hist_path = os.path.join(user_char_dir, "history.json")
    if not os.path.exists(hist_path):
        initial_history = []
        if baseline["first_mes"]:
            # Display-only greeting. server.py never forwards this marker to the LLM.
            initial_history.append({"role": "assistant", "content": baseline["first_mes"], "is_first_message": True})
        with open(hist_path, "w", encoding="utf-8") as f:
            json.dump(initial_history, f, indent=2, ensure_ascii=False)
    with open(hist_path, "r", encoding="utf-8") as f:
        user_history = json.load(f)

    # 7. H-Mode and arousal state.  Both are file-owned so removing this
    # profile directory (or either state file) is a true reset.
    scene_path = os.path.join(user_char_dir, "scene_state.json")
    if not os.path.exists(scene_path):
        user_scene_state = turn_metadata._sanitize_scene_state({})
        with open(scene_path, "w", encoding="utf-8") as sf:
            json.dump(user_scene_state, sf, ensure_ascii=False, indent=2)
    else:
        try:
            with open(scene_path, "r", encoding="utf-8") as sf:
                user_scene_state = turn_metadata._sanitize_scene_state(json.load(sf))
        except Exception:
            user_scene_state = turn_metadata._sanitize_scene_state({})

    arousal_path = os.path.join(user_char_dir, "arousal_state.json")
    default_arousal_state = {
        "final": 0,
        "level": "None",
        "h_energy": user_scene_state["h_energy"],
        "exhausted": user_scene_state["exhausted"],
    }
    if not os.path.exists(arousal_path):
        user_arousal_state = default_arousal_state
        with open(arousal_path, "w", encoding="utf-8") as af:
            json.dump(user_arousal_state, af, ensure_ascii=False, indent=2)
    else:
        try:
            with open(arousal_path, "r", encoding="utf-8") as af:
                user_arousal_state = json.load(af)
            if not isinstance(user_arousal_state, dict):
                user_arousal_state = default_arousal_state
        except Exception:
            user_arousal_state = default_arousal_state

    state = {
        "char_name": char_name,
        "username": username,
        "scenario": user_scenario,
        "memory": user_memory,
        "status": user_status,
        "emotion": user_emotion,
        "emotion_detail": emotion_detail,
        "time_state": time_state,
        "outfits": user_outfits,
        "appearance": user_appearance,
        "character_profile": user_char_profile,
        "inventory": user_inventory,
        "inventory_wardrobe": user_wardrobe_inventory,
        "history": user_history,
        "baseline": baseline,
        "scene_state": user_scene_state,
        "arousal_state": user_arousal_state,
    }
    # Migrate a legacy global record once for an existing user profile.  A
    # missing profile directory is a reset, so it must never receive globals.
    if existing_profile:
        for key in state_index.PROFILE_SQLITE_KEYS:
            if key in legacy_indexed:
                state[key] = legacy_indexed[key]
    # The shared Character Card owns a reusable default SQLite state.  A brand
    # new/reset user profile clones it; an existing legacy folder migrates its
    # own JSON values once so no player-specific state is lost during upgrade.
    character_default_dir = Path(CHARACTERS_ROOT) / char_name
    default_profile_db = character_default_dir / state_index.PROFILE_DB_NAME
    if not default_profile_db.exists() or not state_index.load_profile(character_default_dir):
        reset_character_default_profile_state(char_name)
    if not local_profile_db_exists:
        if existing_profile:
            state_index.save_profile(user_char_dir, state)
        else:
            state_index.clone_profile(character_default_dir, user_char_dir)
    profile_state = state_index.load_profile(user_char_dir)
    if profile_state:
        state.update(profile_state)
    missing_profile_values = {
        key: state[key] for key in state_index.PROFILE_SQLITE_KEYS
        if key in state and key not in profile_state
    }
    if missing_profile_values:
        state_index.save_profile(user_char_dir, missing_profile_values)
    state["emotion"] = str(state.get("emotion_detail", {}).get("name") or state.get("emotion") or "neutral")
    # The SQLite index may contain an old story value; system time always wins.
    state["time_state"] = system_time_state(char_name)
    with open(time_state_path, "w", encoding="utf-8") as f:
        json.dump(state["time_state"], f, ensure_ascii=False, indent=2)
    # Synchronize and hydrate unified Data Block table (current_datablock + turn_records)
    try:
        hydrated_hist, table_payload = turn_metadata.sync_table(
            Path(user_char_dir),
            state,
            state.get("history") or [],
            update_latest_turn_from_current=False,
        )
        state["history"] = hydrated_hist
        state["datablock_table"] = table_payload
    except Exception:
        pass
    state_index.save_profile(user_char_dir, {
        key: state[key] for key in state_index.PROFILE_SQLITE_KEYS if key in state
    })
    # Remove historical global copies after their one-time migration.
    state_index.delete_keys(username, char_name, state_index.LEGACY_GLOBAL_KEYS)
    return state

def save_user_character_state(username: str, char_name: str, updates: Dict[str, Any]):
    """Saves per-user isolated scenario, memory, status, emotion, outfits, or chat history."""
    user_char_dir = os.path.join(USERS_ROOT, username, char_name)
    os.makedirs(user_char_dir, exist_ok=True)

    if "scenario" in updates:
        with open(os.path.join(user_char_dir, "scenario.md"), "w", encoding="utf-8") as f:
            f.write(updates["scenario"])

    if "memory" in updates:
        with open(os.path.join(user_char_dir, "PermanentMemory.md"), "w", encoding="utf-8") as f:
            f.write(updates["memory"])

    if "status" in updates:
        from server import normalize_status_multiline
        norm_status = normalize_status_multiline(updates["status"])
        updates["status"] = norm_status
        with open(os.path.join(user_char_dir, "status.md"), "w", encoding="utf-8") as f:
            f.write(norm_status)

    if "emotion" in updates:
        emotion_name = str(updates["emotion"] or "neutral").strip() or "neutral"
        with open(os.path.join(user_char_dir, "emotion.txt"), "w", encoding="utf-8") as f:
            f.write(emotion_name)
        # Keep the structured field coherent when a caller changes only the
        # short emotion name; otherwise a stale detail record wins on reload.
        if "emotion_detail" not in updates:
            detail_path = os.path.join(user_char_dir, "emotion.json")
            try:
                with open(detail_path, "r", encoding="utf-8") as f:
                    detail = json.load(f)
            except Exception:
                detail = {}
            updates["emotion"] = emotion_name
            updates["emotion_detail"] = {
                **(detail if isinstance(detail, dict) else {}),
                "name": emotion_name,
            }

    if "emotion_detail" in updates:
        detail = dict(updates["emotion_detail"] or {})
        detail["name"] = str(detail.get("name") or updates.get("emotion") or "neutral").strip()
        detail["intensity"] = max(0, min(100, int(detail.get("intensity", 0) or 0)))
        detail["cause"] = str(detail.get("cause") or "").strip()[:500]
        detail["updated_at"] = time.time()
        with open(os.path.join(user_char_dir, "emotion.json"), "w", encoding="utf-8") as f:
            json.dump(detail, f, ensure_ascii=False, indent=2)
        with open(os.path.join(user_char_dir, "emotion.txt"), "w", encoding="utf-8") as f:
            f.write(detail["name"])
        updates["emotion"] = detail["name"]
        updates["emotion_detail"] = detail

    if "time_state" in updates:
        # Do not permit an LLM or client payload to overwrite the host clock.
        clock = system_time_state()
        with open(os.path.join(user_char_dir, "story_time.json"), "w", encoding="utf-8") as f:
            json.dump(clock, f, ensure_ascii=False, indent=2)
        updates["time_state"] = clock

    if "outfits" in updates:
        with open(os.path.join(user_char_dir, "outfits.json"), "w", encoding="utf-8") as f:
            json.dump(updates["outfits"], f, indent=2, ensure_ascii=False)

    if "appearance" in updates:
        with open(os.path.join(user_char_dir, "appearance.md"), "w", encoding="utf-8") as f:
            f.write(str(updates["appearance"]))

    if "character_profile" in updates:
        with open(os.path.join(user_char_dir, "character_individual_profile.md"), "w", encoding="utf-8") as f:
            f.write(str(updates["character_profile"]))

    if "inventory" in updates:
        with open(os.path.join(user_char_dir, "inventory.json"), "w", encoding="utf-8") as f:
            json.dump(updates["inventory"], f, ensure_ascii=False, indent=2)

    if "inventory_wardrobe" in updates:
        with open(os.path.join(user_char_dir, "wardrobe_inventory.json"), "w", encoding="utf-8") as f:
            json.dump(updates["inventory_wardrobe"], f, ensure_ascii=False, indent=2)

    if "scene_state" in updates:
        clean_scene = turn_metadata._sanitize_scene_state(updates["scene_state"])
        updates["scene_state"] = clean_scene
        with open(os.path.join(user_char_dir, "scene_state.json"), "w", encoding="utf-8") as f:
            json.dump(clean_scene, f, indent=2, ensure_ascii=False)

    if "arousal_state" in updates:
        with open(os.path.join(user_char_dir, "arousal_state.json"), "w", encoding="utf-8") as f:
            json.dump(updates["arousal_state"], f, indent=2, ensure_ascii=False)

    # Synchronize unified Data Block table (current_datablock & turn_records)
    try:
        root_path = Path(user_char_dir)
        hist_path = os.path.join(user_char_dir, "history.json")
        if "history" in updates and isinstance(updates["history"], list):
            raw_history = updates["history"]
        elif os.path.exists(hist_path):
            with open(hist_path, "r", encoding="utf-8") as hf:
                raw_history = json.load(hf)
        else:
            raw_history = []

        # Merge existing indexed/file state with updates so build_datablock sees all fields
        # Active outfits and both inventories are file-owned.  Ignoring old
        # SQLite copies here prevents a later unrelated save from writing a
        # stale wardrobe back into the current Data Block snapshot.
        merged_state = {
            key: value for key, value in (state_index.load_profile(user_char_dir) or {}).items()
            if key not in state_index.FILE_OWNED_CHARACTER_KEYS
        }
        for k, fname in (
            ("status", "status.md"),
            ("scenario", "scenario.md"),
            ("memory", "PermanentMemory.md"),
            ("emotion", "emotion.txt"),
        ):
            if k not in merged_state and k not in updates:
                fpath = os.path.join(user_char_dir, fname)
                if os.path.exists(fpath):
                    with open(fpath, "r", encoding="utf-8") as rf:
                        merged_state[k] = rf.read()
        for k, fname in (
            ("outfits", "outfits.json"),
            ("inventory", "inventory.json"),
            ("inventory_wardrobe", "wardrobe_inventory.json"),
            ("scene_state", "scene_state.json"),
            ("arousal_state", "arousal_state.json"),
            ("emotion_detail", "emotion.json"),
        ):
            if k not in merged_state and k not in updates:
                fpath = os.path.join(user_char_dir, fname)
                if os.path.exists(fpath):
                    try:
                        with open(fpath, "r", encoding="utf-8") as rf:
                            merged_state[k] = json.load(rf)
                    except Exception:
                        pass
        merged_state.update(updates)
        manual_state_update = (
            "history" not in updates
            and any(k in updates for k in ("status", "scenario", "memory", "emotion", "emotion_detail", "outfits", "inventory", "inventory_wardrobe", "scene_state", "arousal_state"))
        )
        clean_rows = turn_metadata.prepare_for_storage(
            raw_history,
            root_path,
            state=merged_state,
            update_latest_turn_from_current=manual_state_update,
        )
        if "history" in updates:
            with open(hist_path, "w", encoding="utf-8") as f:
                json.dump(clean_rows, f, indent=2, ensure_ascii=False)
            hydrated_rows = turn_metadata.hydrate_from_disk(root_path, clean_rows)
            if isinstance(updates["history"], list):
                updates["history"][:] = hydrated_rows
            else:
                updates["history"] = hydrated_rows
    except Exception:
        if "history" in updates:
            with open(os.path.join(user_char_dir, "history.json"), "w", encoding="utf-8") as f:
                json.dump(updates["history"], f, indent=2, ensure_ascii=False)

    state_index.save_profile(user_char_dir, updates)
    state_index.delete_keys(username, char_name, state_index.LEGACY_GLOBAL_KEYS)
    _sync_active_session_profile_db(user_char_dir)


def _sync_active_session_profile_db(user_char_dir: str) -> None:
    """Mirror the active profile cache into its session-owned SQLite source."""
    try:
        root = Path(user_char_dir)
        index_path = root / "chat_sessions" / "index.json"
        if not index_path.is_file():
            return
        index = json.loads(index_path.read_text(encoding="utf-8"))
        session_id = str(index.get("active_id") or "")
        if not re.fullmatch(r"[a-f0-9]{32}", session_id):
            return
        state_index.clone_profile(root, root / "chat_sessions" / session_id)
    except Exception:
        return


def create_character(
    name: str,
    persona: str = "",
    personality: str = "",
    scenario: str = "",
    first_mes: str = "",
    avatar_bytes: Optional[bytes] = None,
    gender: str = "Female",
    age: str = "",
    status: str = "Single",
    role_goals: str = "",
    sex_preference: str = "",
    likes_dislikes: str = "",
    communication_style: str = "",
    char_summary: str = "",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Creates a new character card with baseline metadata, avatar, and full Char_Summary."""
    ensure_directories()
    safe_name = name.strip().replace("/", "_").replace("\\", "_")
    if not safe_name:
        raise ValueError("ชื่อตัวละครไม่ถูกต้อง")

    char_dir = os.path.join(CHARACTERS_ROOT, safe_name)
    os.makedirs(char_dir, exist_ok=True)
    sprites_dir = os.path.join(char_dir, "sprites")
    os.makedirs(sprites_dir, exist_ok=True)

    # Avatar
    avatar_dest = os.path.join(char_dir, "avatar.png")
    if avatar_bytes:
        with open(avatar_dest, "wb") as f:
            f.write(avatar_bytes)
    elif not os.path.exists(avatar_dest):
        # Create a simple high quality default placeholder image
        img = Image.new("RGBA", (512, 512), color=(76, 29, 149, 255))
        img.save(avatar_dest, "PNG")

    # Baseline files
    with open(os.path.join(char_dir, "persona.md"), "w", encoding="utf-8") as f: 
        f.write(persona)

    with open(os.path.join(char_dir, "personality.md"), "w", encoding="utf-8") as f:
        f.write(personality)

    with open(os.path.join(char_dir, "default_scenario.md"), "w", encoding="utf-8") as f:
        f.write(scenario)

    with open(os.path.join(char_dir, "first_mes.txt"), "w", encoding="utf-8") as f:
        f.write(first_mes)

    # Char_Summary.md
    if char_summary and char_summary.strip():
        with open(os.path.join(char_dir, "Char_Summary.md"), "w", encoding="utf-8") as f:
            f.write(char_summary.strip() + "\n")
    else:
        social_status = status.strip() if status else "Single"
        if role_goals and role_goals.strip():
            social_status = f"{social_status} | {role_goals.strip()}"

        summary_source = {
            "name": safe_name,
            "gender": gender or "Female",
            "age": age or "",
            "personality": personality,
            "status": social_status,
            "role": role_goals or "",
            "description": persona,
            "background": persona,
            "scenario": scenario,
            "sex_preference": sex_preference or "",
            "likes": likes_dislikes or "",
            "likes_dislikes": likes_dislikes or "",
            "communication_style": communication_style or "",
            "mes_example": "",
        }
        write_char_summary(char_dir, summary_source)

    with open(os.path.join(char_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump({
            "name": safe_name,
            "creator": "RealmPlay User",
            "character_version": "1.0",
            "tags": ["RealmPlay"],
            "spec": "chara_card_v2"
        }, f, indent=2, ensure_ascii=False)

    outfits = kwargs.get("outfits")
    if outfits and isinstance(outfits, dict):
        with open(os.path.join(char_dir, "outfits.json"), "w", encoding="utf-8") as f:
            json.dump(outfits, f, indent=2, ensure_ascii=False)

    return {
        "ok": True,
        "name": safe_name
    }


def export_character_card_png(char_name: str) -> bytes:
    """
    Exports a character into a TavernAI/SillyTavern PNG V2 compliant image.
    Embeds character metadata in base64 within the 'chara' text chunk.
    """
    import io
    from PIL.PngImagePlugin import PngInfo

    char_dir = os.path.join(CHARACTERS_ROOT, char_name)
    baseline = get_character_baseline(char_name)
    if not baseline:
        raise ValueError(f"ไม่พบตัวละคร {char_name}")

    avatar_path = os.path.join(char_dir, "avatar.png")
    if os.path.isfile(avatar_path):
        img = Image.open(avatar_path).convert("RGBA")
    else:
        img = Image.new("RGBA", (512, 512), color=(124, 58, 237, 255))

    # Read config if present
    cfg_path = os.path.join(char_dir, "config.json")
    creator = "RealmPlay"
    tags = []
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                c = json.load(f)
                creator = c.get("creator", creator)
                tags = c.get("tags", tags)
        except Exception:
            pass

    # Package sprites if present
    sprites_dict = {}
    sprites_dir = os.path.join(char_dir, "sprites")
    if os.path.isdir(sprites_dir):
        for s_file in os.listdir(sprites_dir):
            s_path = os.path.join(sprites_dir, s_file)
            if os.path.isfile(s_path) and s_file.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                try:
                    with open(s_path, "rb") as sf:
                        sprites_dict[s_file] = base64.b64encode(sf.read()).decode("ascii")
                except Exception:
                    pass

    card_data = {
        "name": char_name,
        "description": baseline["persona"],
        "personality": baseline["personality"],
        "scenario": baseline["scenario"],
        "first_mes": baseline["first_mes"],
        "mes_example": "",
        "creator_notes": "Exported from RealmPlay",
        "system_prompt": "",
        "post_history_instructions": "",
        "tags": tags,
        "creator": creator,
        "character_version": "1.0",
        "alternate_greetings": [],
        "extensions": {
            "realmplay": {
                "version": "1.0"
            }
        }
    }
    if sprites_dict:
        card_data["extensions"]["sprites"] = sprites_dict

    wrapper = {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": card_data
    }

    from realmplay_features import card_document
    wrapper = card_document(char_name, __import__(__name__))
    # Preserve arbitrary existing extensions, including nested namespaces.
    if sprites_dict:
        existing = wrapper['data']['extensions'].get('sprites')
        if existing is None:
            wrapper['data']['extensions']['sprites'] = sprites_dict
        elif isinstance(existing, dict):
            for key, value in sprites_dict.items():
                existing.setdefault(key, value)
    raw_json_str = json.dumps(wrapper, ensure_ascii=False)
    b64_chara = base64.b64encode(raw_json_str.encode("utf-8")).decode("ascii")

    png_info = PngInfo()
    png_info.add_text("chara", b64_chara)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", pnginfo=png_info)
    buffer.seek(0)
    return buffer.getvalue()

