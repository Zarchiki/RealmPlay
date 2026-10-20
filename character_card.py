"""Character Card V2 (CCv2) parser, sprite extractor, and isolated user memory manager.

Features:
- Decodes PNG tEXt/zTXt/iTXt metadata under keyword 'chara' (Base64 -> JSON).
- Extracts and saves embedded 30+ sprite pictures from extensions into characters/{char_name}/sprites/
- Manages strict Per-User Profile isolation:
  - users/{username}/{char_name}/PermanentMemory.md
  - users/{username}/{char_name}/scenario.md
  - users/{username}/{char_name}/status.md
  - users/{username}/{char_name}/appearance.md
  - users/{username}/{char_name}/profile_image.png
  - users/{username}/{char_name}/history.json
"""
import base64
import json
import os
import shutil
import time
import re
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from PIL import Image
import state_index
from card_v2 import normalize_card, read_legacy_card

CHARACTERS_ROOT = "characters"
USERS_ROOT = "users"


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
    ("Sex Preference, Sex Desires & Nos", ("sex_preference", "sexual_preference", "sexuality", "sex_desires", "sexual_desires", "nos", "boundaries", "limits")),
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

    with open(os.path.join(char_dir, 'card.json'), 'w', encoding='utf-8') as f:
        json.dump(card_data, f, ensure_ascii=False, indent=2)
    # 1. Copy original avatar
    avatar_dest = os.path.join(char_dir, "avatar.png")
    if str(png_file_path).lower().endswith('.json'):
        Image.new('RGBA', (512, 512), (76, 29, 149, 255)).save(avatar_dest, 'PNG')
    else:
        shutil.copyfile(png_file_path, avatar_dest)

    # 2. Save Canonical Card Configuration
    config_dest = os.path.join(char_dir, "config.json")
    with open(config_dest, "w", encoding="utf-8") as f:
        json.dump({
            "name": char_name,
            "creator": card_data.get("creator", ""),
            "character_version": card_data.get("character_version", "1.0"),
            "tags": card_data.get("tags", []),
            "spec": "chara_card_v2"
        }, f, indent=2, ensure_ascii=False)

    # 3. Save Core Prompt Files
    with open(os.path.join(char_dir, "persona.md"), "w", encoding="utf-8") as f:
        f.write(card_data.get("description", ""))

    with open(os.path.join(char_dir, "personality.md"), "w", encoding="utf-8") as f:
        f.write(card_data.get("personality", ""))

    with open(os.path.join(char_dir, "default_scenario.md"), "w", encoding="utf-8") as f:
        f.write(card_data.get("scenario", ""))

    with open(os.path.join(char_dir, "first_mes.txt"), "w", encoding="utf-8") as f:
        f.write(card_data.get("first_mes", ""))

    # Card metadata is read once here, then chat uses Char_Summary.md only.
    write_char_summary(char_dir, card_data)

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
        "has_avatar": os.path.exists(os.path.join(char_dir, "avatar.png"))
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
    baseline = get_character_baseline(char_name)
    if not baseline:
        raise ValueError(f"Character {char_name} not found")

    os.makedirs(user_char_dir, exist_ok=True)
    
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
        default_status = (
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
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(default_status)
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
    if not os.path.exists(outfit_path):
        # Default starter outfit with part toggles (12 items: outer, head, head_acc, top, top_inner, neck_acc, bottom, bottom_inner, hand_acc, shoes, socks, leg_acc + naked)
        default_outfits = {
            "outer": {"active": True, "prompt": "casual clothes, jacket"},
            "head": {"active": False, "prompt": "hat"},
            "head_acc": {"active": False, "prompt": "hair ribbon"},
            "top": {"active": False, "prompt": "shirt"},
            "top_inner": {"active": False, "prompt": "bra"},
            "neck_acc": {"active": False, "prompt": "choker"},
            "bottom": {"active": False, "prompt": "skirt"},
            "bottom_inner": {"active": False, "prompt": "panties"},
            "hand_acc": {"active": False, "prompt": "gloves"},
            "shoes": {"active": False, "prompt": "shoes"},
            "socks": {"active": False, "prompt": "stockings"},
            "leg_acc": {"active": False, "prompt": "leg strap"},
            "naked": {"active": False, "prompt": "naked"}
        }
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
    if not os.path.exists(appearance_path):
        with open(appearance_path, "w", encoding="utf-8") as f:
            # One-time migration keeps existing image generation useful.
            f.write(baseline["persona"])
    with open(appearance_path, "r", encoding="utf-8") as f:
        user_appearance = f.read()

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
        starter_inventory = [
            {"name": "สมุดบันทึกเล็ก", "desc": "สมุดพกเล่มโปรดสำหรับจดเรื่องราวสำคัญ", "qty": 1, "type": "tool"},
            {"name": "ลูกอมรสหวาน", "desc": "ลูกอมพกติดตัวรสผลไม้ หอมหวาน", "qty": 3, "type": "consumable"}
        ]
        with open(inv_path, "w", encoding="utf-8") as f:
            json.dump(starter_inventory, f, ensure_ascii=False, indent=2)
    try:
        with open(inv_path, "r", encoding="utf-8") as f:
            user_inventory = json.load(f)
    except Exception:
        user_inventory = []

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
        "history": user_history,
        "baseline": baseline
    }
    # Files are readable backups. Seed an empty index once, then prefer its
    # transactional values after a successful future save.
    indexed = state_index.load(username, char_name)
    if not indexed:
        state_index.save(username, char_name, state)
    else:
        for key in state_index.INDEXED_KEYS:
            if key in indexed:
                state[key] = indexed[key]
        state["emotion"] = str(state.get("emotion_detail", {}).get("name") or state.get("emotion") or "neutral")
    # The SQLite index may contain an old story value; system time always wins.
    state["time_state"] = system_time_state(char_name)
    with open(time_state_path, "w", encoding="utf-8") as f:
        json.dump(state["time_state"], f, ensure_ascii=False, indent=2)
    state_index.save(username, char_name, {"time_state": state["time_state"]})
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
        with open(os.path.join(user_char_dir, "emotion.txt"), "w", encoding="utf-8") as f:
            f.write(updates["emotion"].strip())

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
        updates = {**updates, "emotion": detail["name"], "emotion_detail": detail}

    if "time_state" in updates:
        # Do not permit an LLM or client payload to overwrite the host clock.
        clock = system_time_state()
        with open(os.path.join(user_char_dir, "story_time.json"), "w", encoding="utf-8") as f:
            json.dump(clock, f, ensure_ascii=False, indent=2)
        updates = {**updates, "time_state": clock}

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

    if "history" in updates:
        with open(os.path.join(user_char_dir, "history.json"), "w", encoding="utf-8") as f:
            json.dump(updates["history"], f, indent=2, ensure_ascii=False)

    state_index.save(username, char_name, updates)


def create_character(name: str, persona: str = "", personality: str = "", scenario: str = "", first_mes: str = "", avatar_bytes: Optional[bytes] = None) -> Dict[str, Any]:
    """Creates a new character card with baseline metadata and avatar."""
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

    write_char_summary(char_dir, {
        "name": safe_name,
        "description": persona,
        "personality": personality,
        "scenario": scenario,
    })

    with open(os.path.join(char_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump({
            "name": safe_name,
            "creator": "RealmPlay User",
            "character_version": "1.0",
            "tags": ["RealmPlay"],
            "spec": "chara_card_v2"
        }, f, indent=2, ensure_ascii=False)

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

