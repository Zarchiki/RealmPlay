"""Random Character Card Generator for RealmPlay.

Wildcards are resolved once into compact card facts and an image prompt.  The
resolved prompt creates the shared 2:3 card/profile/chat portrait; wildcard
source text is never placed in roleplay context.
"""
import os
import random
import json
import re
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WILDCARDS_DIR = os.path.join(BASE_DIR, "data", "wildcards")
CREATION_WILDCARDS_DIR = os.path.join(BASE_DIR, "data", "character_creation_wildcards")
CATALOG_PATH = os.path.join(BASE_DIR, "data", "wardrobe_catalog.json")

# Names are curated rather than derived from wildcard text. A character name
# is an identity shown throughout the UI, not an image-prompt fragment.
FEMALE_GIVEN_NAMES = (
    "Aerin", "Elara", "Lyra", "Mira", "Nerissa", "Seren", "Talia", "Vesper",
    "Aveline", "Celia", "Iris", "Maeve", "Nadia", "Rhea", "Sable", "Thalia",
)
FAMILY_NAMES = (
    "Ashvale", "Brightwood", "Dawnmere", "Emberfall", "Hawthorne", "Moonveil",
    "Ravenhart", "Silverbrook", "Starling", "Vale", "Wintermere", "Wren",
)

# Popular female Thai nicknames (Strictly standalone nickname only - no realname, no surname, strictly female)
THAI_FEMALE_NICKNAMES = (
    "พลอย", "ฟ้า", "มายด์", "เบล", "มิ้นต์", "พริม", "นุ่น", "น้ำ", "แนน", "กวาง",
    "แพร", "แป้ง", "ใบเฟิร์น", "ไอซ์", "มุก", "ปุยฝ้าย", "พิม", "จูน", "เกรซ", "วิว",
    "แพรวา", "อลิส", "เนย", "โบว์", "เชอร์รี่", "ฝน", "บิวตี้", "น้ำหวาน", "แอม", "เฟิร์น",
    "โมเน่ต์", "โยเกิร์ต", "พิมมี่", "เมย์", "จอย", "ออม", "ปอ", "ดาว", "หวาน", "พั้นช์",
    "นิ่ม", "บัว", "ใบบัว", "มะปราง", "ส้ม", "ครีม", "แอปเปิ้ล", "ป๊อป", "แพม"
)

ETHNIC_NAME_BANKS = {
    "Japanese": {
        "given": ("Aoi", "Hina", "Yuna", "Mio", "Rin", "Sakura", "Koharu", "Mei", "Nanami", "Akari", "Rei", "Kasumi", "Ayaka", "Asuka", "Chiyo", "Emi", "Haruka", "Kanna", "Misaki", "Nozomi", "Sayaka", "Tomoyo", "Yukiko"),
        "family": ("Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kobayashi", "Kato", "Fujimoto", "Mori", "Inoue", "Kimura", "Hayashi", "Shimizu", "Yamazaki", "Ikeda", "Hashimoto")
    },
    "Korean": {
        "given": ("Ji-woo", "Seo-yeon", "Min-ji", "Ha-eun", "Yoo-jin", "Chae-won", "Soo-jin", "Ye-ji", "Da-eun", "Ji-min", "Eun-ji", "Bo-young", "Hye-jin", "So-hee", "Yu-na"),
        "family": ("Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon", "Jang", "Lim", "Han", "Song", "Bae")
    },
    "Chinese": {
        "given": ("Mei-ling", "Xiao-ting", "Jia-yi", "Yu-xin", "Xin-yi", "Shu-fen", "Ting-ting", "Lin", "An-qi", "Ruo-xi", "Xiao-yu", "Ying-ying", "Jing", "Yan", "Li-wei", "Hui-ling", "Zi-han", "Si-qi"),
        "family": ("Chen", "Lin", "Huang", "Zhang", "Li", "Wang", "Wu", "Liu", "Yang", "Zhao", "Sun", "Zhu", "Gao", "He", "Guo")
    },
    "Vietnamese": {
        "given": ("Linh", "Mai", "Anh", "Hoa", "Lan", "Huong", "Trang", "Phuong", "Thao", "Ngoc"),
        "family": ("Nguyen", "Tran", "Le", "Pham", "Hoang", "Phan", "Vu", "Dang", "Bui")
    },
    "Filipina": {
        "given": ("Maria", "Bea", "Angel", "Jasmine", "Kristine", "Alyssa", "Bianca", "Camille", "Chloe"),
        "family": ("Santos", "Reyes", "Cruz", "Bautista", "Del Rosario", "Aquino", "Garcia", "Mendoza")
    },
    "Western": {
        "given": ("Camille", "Elise", "Faye", "Harper", "Juno", "Kira", "Lena", "Noelle", "Sofia", "Tessa", "Chloe", "Emma", "Audrey", "Olivia"),
        "family": ("Bennett", "Delacroix", "Hart", "Rossi", "Miller", "Dubois", "Moreau", "Larsen", "Keller", "Vargas")
    }
}

CONTEMPORARY_GIVEN_NAMES = (
    "Aiko", "Camille", "Dara", "Elise", "Faye", "Harper", "Juno", "Kira",
    "Lena", "Mina", "Noelle", "Priya", "Reina", "Sofia", "Tessa", "Yuna",
)
CONTEMPORARY_FAMILY_NAMES = (
    "Bennett", "Chandra", "Delacroix", "Fujimoto", "Hart", "Ibrahim", "Kwon",
    "Morales", "Nguyen", "Park", "Rossi", "Sato", "Serrano", "Tan", "Vargas", "Yamada",
)
PERSONALITY_SEEDS = (
    "methodical and self-contained, with a dry sense of humor that appears only when she feels safe",
    "outwardly charismatic and fearless, privately anxious about disappointing people who rely on her",
    "gentle and observant, but unexpectedly stubborn when a personal value is challenged",
    "restlessly curious and impulsive, masking a fear of being ordinary with ambitious plans",
    "disciplined and practical, with a hidden sentimental streak expressed through small acts of care",
    "sharp-tongued and competitive, yet deeply protective of people who earn her loyalty",
    "calm under pressure and emotionally guarded, with a fascination for people unlike herself",
    "playful and inventive, but serious about promises and quick to notice injustice",
)
APPEARANCE_SEEDS = (
    "a faint crescent scar through one eyebrow and hands marked by a practical craft",
    "an attentive, difficult-to-read gaze, a slightly crooked smile, and an immaculate personal style",
    "wind-tousled hair, a habitual thoughtful frown, and posture shaped by long hours of work",
    "expressive eyes that reveal amusement before her words do, with a distinctive piece of inherited jewelry",
    "a poised bearing, callused fingertips, and an easy smile that arrives only after careful observation",
    "a striking profile, a soft voice that contrasts with her direct manner, and an old injury she protects instinctively",
)
BACKGROUND_HOOKS = (
    "left a secure path after uncovering a mistake no one else wanted to acknowledge",
    "is rebuilding her life after a public failure taught her whom to trust",
    "supports a close relative while quietly pursuing a dream she once considered impossible",
    "returned to her hometown carrying a secret about why she left years ago",
    "owes a complicated favor to a mentor, guild, or employer and is determined to settle it on her own terms",
    "keeps a private record of unsolved questions that have followed her since childhood",
    "was raised between two communities and never fully accepted either label until now",
    "made a promise during a crisis and is still living with the cost of keeping it",
)

# Context-aware background story variations tailored specifically per genre/mode
BACKGROUND_HOOKS_BY_MODE = {
    "highschool": (
        "recently transferred from another prefecture after a quiet rumor made staying at her old school uncomfortable",
        "carries intense family expectations for elite entrance exams while secretly spending afternoons pursuing music or art",
        "was formerly the standout star athlete of her club until a minor injury forced her to step back and redefine herself",
        "works an unpermitted part-time job after class to cover her own personal expenses and independence",
        "serves on the student council where she often stays late resolving disputes while keeping her personal feelings tightly guarded",
        "struggled with long-term absence due to a past illness and is now trying to catch up with everyday teenage social life",
        "is a quiet scholarship student who feels out of place among wealthier peers but refuses to let anyone pity her",
        "spends long evenings studying at the library or cram school, driven by a determination to leave her small hometown",
        "lives mostly independently while her busy parents work overseas, learning self-reliance much earlier than her classmates",
        "hides an unexpected hobby or geek passion behind an immaculate, ordinary high school exterior",
        "navigates a complicated friendship fallout that made her cautious about getting too close to people too quickly",
        "acts as a cheerful and reliable mood-maker in class, though few classmates know how lonely she feels at home",
    ),
    "normal": (
        "walked away from an exhausting corporate career in the capital to run a small independent business on her own terms",
        "is an investigative researcher or journalist tracing an unresolved local incident that authorities quietly dismissed",
        "works demanding hospital night shifts while saving up to establish an independent community wellness clinic",
        "ended a long, stifling relationship and relocated to a new neighborhood to reclaim her autonomy",
        "is an accomplished craftswoman or designer rebuilding her reputation after a business partner betrayed her intellectual property",
        "moonlights as an underground indie musician while maintaining a quiet, ordinary day job during working hours",
        "is a dedicated police detective dealing with bureaucratic red tape while protecting a vulnerable informant",
        "grew up in a strict traditional family household and chose her own unconventional vocation despite their disapproval",
        "manages a quiet evening bookstore or café that serves as an oasis for regulars with stories of their own",
        "returned from living abroad with broadened horizons, finding her familiar hometown both nostalgic and subtly alien",
        "is an emergency response specialist whose calm bedside demeanor hides memories of high-stress situations",
        "balances caring for an ailing family member with her own fierce ambition in a competitive professional industry",
    ),
    "monster": (
        "is the last known heir of an ancient abyssal or serpentine lineage, seeking a peaceful sanctuary amidst human expansion",
        "was once kept in a clandestine imperial bestiary or collector's menagerie before staging a daring midnight escape",
        "guards a forgotten subterranean spring or secluded coastal shrine whose sacred waters are beginning to dry up",
        "trades in rare alchemical relics and monster-lore in secluded black markets while concealing her true monstrous traits",
        "was banished from her beastkin clan for defending an outsider and now wanders between frontiers as an independent scout",
        "instinctively experiences seasonal feral surges and heat cycles, seeking a partner whose trust and strength can ground her",
        "was nurtured by an eccentric human hermit scholar who taught her language, etiquette, and the complexities of mortal emotion",
        "maintains an isolated lighthouse or sea watchtower, warning sailors away from the jagged reefs where her kin dwell",
        "possesses powerful predatory instincts that she consciously restrains behind an elegant, polite demeanor",
        "seeks a lost ancestral relic stolen by dungeon raiders, following whispers through dimly lit tavern alleys",
        "has lived centuries longer than the mortals around her, carrying both fond memories and a deep longing for genuine companionship",
        "serves as an intermediary between territorial wilderness beasts and border towns, trusted by neither side completely",
    ),
    "fantasy": (
        "was expelled from the Royal Arcane Academy for studying forbidden ancient wards to cure a mysterious magical affliction",
        "is a retired elite vanguard knight who laid down her standard after witnessing the corrupt motives behind a border war",
        "serves as a consecrated temple investigator tasked with tracking down consecrated artifacts stolen by shadowy cults",
        "inherited a run-down alchemical workshop and mountain of guild debts from a master who vanished without a word",
        "survived an expedition deep into a shifting dungeon that claimed the rest of her mercenary party",
        "belongs to a wandering nomadic ranger order sworn to cull demonic anomalies spreading along ancient leylines",
        "was born under a rare astronomical eclipse that granted her strange arcane sight, marking her as an omen among peers",
        "escaped an arranged political marriage among nobility to make her fortune as a freelance adventurer and dungeon cartographer",
        "studies ancient draconic and forgotten titan dialects, deciphering stone monoliths across dangerous wild territories",
        "carries an enchanted heirloom blade or seal that whispers cryptic warnings whenever danger approaches",
        "was trained in a secluded mountain monastery in unarmed combat and inner ki before descending into the chaotic realms",
        "is a master battle-chef or wilderness herbalist seeking mythical beast ingredients across untamed continents",
    ),
}
NAME_BANNED_WORDS = {
    "character", "adventurer", "unnamed", "unknown", "probe", "context", "test",
    "female", "girl", "woman", "elf", "human", "knight", "mage", "ranger",
    "warrior", "princess", "lady", "miss", "the", "of", "and",
    # Male titles, terms, and common male names filtered out
    "male", "boy", "man", "guy", "mister", "mr", "sir", "lord", "king", "prince",
    "john", "david", "michael", "james", "robert", "william", "alex", "jack", "tom",
    "สมชาย", "สมศักดิ์", "ประเสริฐ", "บุญมี", "อนุชา", "ธนกร", "กิตติ", "ศิริ", "ภานุ",
}



# Fallback dictionary for known external wildcard packs not locally present on disk
FALLBACK_WILDCARDS = {
    "character-figure-apple": ["apple-shaped figure, soft rounded curves", "slender pear-shaped silhouette"],
    "character-figure-hourglass": ["hourglass figure, slender waist, curvaceous hips", "voluptuous hourglass silhouette"],
    "character-figure-rectangle": ["athletic toned figure, slender straight waist", "lean athletic build"],
    "character-figure-round": ["soft curvaceous figure, full feminine curves", "plump hourglass body"],
    "character-figure-triangle": ["pear-shaped figure, slender waist, wide hips", "slender torso with flared hips"],
    "character-figure": ["slender hourglass figure", "athletic toned physique", "curvaceous feminine body"],
    "cc_breast_size": ["medium breasts", "large breasts", "perky breasts", "ample breasts", "slender chest"],
    "cc_body_shape": ["hourglass figure", "slender feminine body", "petite curvy frame", "athletic physique"],
    "colors": ["black", "silver", "golden blonde", "chestnut brown", "crimson red", "platinum"],
    "hair-length": ["long", "waist-length", "shoulder-length", "short"],
    "bust_size": ["medium breasts", "large breasts", "perky breasts", "ample breasts"],
    "figure_type": [
        "slender figure", "curvaceous hourglass body", "athletic toned physique",
        "petite frame", "curvy voluptuous body", "slim build", "pear-shaped build",
        "soft curvaceous figure", "tall slender figure", "compact athletic build"
    ],
    "waist_size": [
        "slender waist", "narrow waist", "tiny waist", "slim waist",
        "defined waist", "tapered waist", "toned waist", "petite waist"
    ],
    "thigh_size": [
        "slender thighs", "thick thighs", "toned thighs", "shapely thighs",
        "curvy thighs", "plump thighs", "smooth thighs", "athletic thighs"
    ],
    "pubic_style": [
        "shaved pussy", "trimmed pubic hair, ", "neat landing strip pubic hair",
        "natural pubic hair", "bare pubic pussy"
    ],
}


def _read_wildcard_lines(tag_name: str) -> list:
    """Read non-empty lines from a wildcard file with recursive fallback and alias search."""
    tag_clean = tag_name.strip().replace("\\", "/")
    if tag_clean.endswith(".txt"):
        tag_clean = tag_clean[:-4]

    # 0. Check specialized Character Creation Wildcards first (by relative path or basename)
    if os.path.exists(CREATION_WILDCARDS_DIR):
        creation_direct = os.path.join(CREATION_WILDCARDS_DIR, tag_clean.replace("/", os.sep) + ".txt")
        if os.path.exists(creation_direct):
            try:
                with open(creation_direct, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
                if lines:
                    return lines
            except Exception:
                pass
        import glob
        creation_base = os.path.basename(tag_clean) + ".txt"
        creation_matches = glob.glob(os.path.join(CREATION_WILDCARDS_DIR, "**", creation_base), recursive=True)
        if creation_matches:
            try:
                with open(creation_matches[0], "r", encoding="utf-8", errors="ignore") as f:
                    lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
                if lines:
                    return lines
            except Exception:
                pass

    # 1. Direct path check
    direct_path = os.path.join(WILDCARDS_DIR, tag_clean.replace("/", os.sep) + ".txt")
    if os.path.exists(direct_path):
        try:
            with open(direct_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            if lines:
                return lines
        except Exception:
            pass

    # 2. Local fallback in data/wildcards/attire
    local_path = os.path.join("data", "wildcards", "attire", tag_clean.replace("/", os.sep) + ".txt")
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            if lines:
                return lines
        except Exception:
            pass

    # 3. Basename search across entire WILDCARDS_DIR
    base_file = os.path.basename(tag_clean) + ".txt"
    try:
        import glob
        matches = glob.glob(os.path.join(WILDCARDS_DIR, "**", base_file), recursive=True)
        if matches:
            with open(matches[0], "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            if lines:
                return lines
    except Exception:
        pass

    # 4. Check internal fallback dictionary
    pure_key = os.path.basename(tag_clean).lower().replace(" ", "_").replace("-", "_")
    for fb_k, fb_vals in FALLBACK_WILDCARDS.items():
        if fb_k in pure_key or pure_key in fb_k:
            return fb_vals

    return []


def _clean_unresolved_wildcards(text: str) -> str:
    """Guarantees zero __wildcard__ strings remain in the final prompt."""
    def clean_match(m):
        raw_tag = m.group(1).strip()
        # Extract the last component of any path (e.g. 'free cards/character-figure-apple' -> 'character-figure-apple')
        name_only = os.path.basename(raw_tag)
        # Check dictionary again
        pure_key = name_only.lower().replace(" ", "_").replace("-", "_")
        for fb_k, fb_vals in FALLBACK_WILDCARDS.items():
            if fb_k in pure_key or pure_key in fb_k:
                return random.choice(fb_vals)
        # Convert tag into clean readable english
        cleaned_words = name_only.replace("_", " ").replace("-", " ")
        cleaned_words = re.sub(r"\b(cc|free|cards|wildcards|v\d+)\b", "", cleaned_words, flags=re.IGNORECASE).strip()
        return cleaned_words or "detailed"

    # Replace any leftover __...__
    cleaned = re.sub(r"__([a-zA-Z0-9_\-+/ \\.%]+)__", clean_match, text)
    # Clean up double commas or messy spacing
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    return cleaned


def _generated_name() -> str:
    return f"{random.choice(FEMALE_GIVEN_NAMES)} {random.choice(FAMILY_NAMES)}"


def _wildcard_pick(*names: str, fallback: str) -> str:
    """Select one resolved value from the installed wildcard library."""
    for name in names:
        values = _read_wildcard_lines(name)
        if values:
            return _resolve_template_tags(random.choice(values))
    return fallback


def _identity_seed(mode: str, ethnicity: Optional[str] = None) -> Dict[str, str]:
    """Build a concrete identity anchor that prevents generic card prose, respecting ethnicity & Thai naming."""
    mode_lower = str(mode or "").lower()
    if mode_lower in ("normal", "highschool"):
        eth = str(ethnicity or "").strip()
        if "thai" in eth.casefold():
            # Thai character: Pure popular female nickname only (no real name, no family name)
            char_full_name = random.choice(THAI_FEMALE_NICKNAMES)
        elif "japanese" in eth.casefold():
            bank = ETHNIC_NAME_BANKS["Japanese"]
            char_full_name = f"{random.choice(bank['given'])} {random.choice(bank['family'])}"
        elif "korean" in eth.casefold():
            bank = ETHNIC_NAME_BANKS["Korean"]
            char_full_name = f"{random.choice(bank['given'])} {random.choice(bank['family'])}"
        elif "chinese" in eth.casefold():
            bank = ETHNIC_NAME_BANKS["Chinese"]
            char_full_name = f"{random.choice(bank['given'])} {random.choice(bank['family'])}"
        elif "vietnamese" in eth.casefold():
            bank = ETHNIC_NAME_BANKS["Vietnamese"]
            char_full_name = f"{random.choice(bank['given'])} {random.choice(bank['family'])}"
        elif "filipina" in eth.casefold() or "filipino" in eth.casefold():
            bank = ETHNIC_NAME_BANKS["Filipina"]
            char_full_name = f"{random.choice(bank['given'])} {random.choice(bank['family'])}"
        elif any(w in eth.casefold() for w in ("caucasian", "french", "italian", "british", "american", "scandinavian", "latina", "western")):
            bank = ETHNIC_NAME_BANKS["Western"]
            char_full_name = f"{random.choice(bank['given'])} {random.choice(bank['family'])}"
        else:
            given = random.choice(CONTEMPORARY_GIVEN_NAMES)
            family = random.choice(CONTEMPORARY_FAMILY_NAMES)
            char_full_name = f"{given} {family}"
    else:
        given, family = random.choice(FEMALE_GIVEN_NAMES), random.choice(FAMILY_NAMES)
        char_full_name = f"{given} {family}"

    mode_hooks = BACKGROUND_HOOKS_BY_MODE.get(mode_lower, BACKGROUND_HOOKS)
    hook = random.choice(mode_hooks)

    return {
        "name": char_full_name,
        "personality_anchor": random.choice(PERSONALITY_SEEDS),
        "appearance_anchor": _wildcard_pick("rpg/trait.txt", "rpg/appearance.txt", "face.txt", fallback=random.choice(APPEARANCE_SEEDS)),
        "background_hook": hook,
    }


def normalize_character_name(value: Any, default_name: Optional[str] = None) -> str:
    """Accept a short person name in English or Thai; otherwise fallback to default or curated name."""
    raw = str(value or "").strip()
    raw = re.sub(r"\(.*?\)", "", raw)
    raw = re.split(r"[,;:/|]|\s+[—–-]\s+", raw, maxsplit=1)[0].strip()
    # Support Thai Unicode ฀-๿ along with Latin letters
    raw = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ฀-๿' -]", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" -'")
    words = raw.split()

    is_thai = any(re.search(r"[฀-๿]", w) for w in words)
    invalid = (
        not (1 <= len(words) <= 3)
        or len(raw) < 2
        or len(raw) > 40
        or any(word.casefold() in NAME_BANNED_WORDS for word in words)
        or (not is_thai and any(len(word) < 2 for word in words))
    )
    if invalid:
        return default_name or _generated_name()
    if is_thai:
        return raw
    return " ".join(word[:1].upper() + word[1:] for word in words)


def _resolve_template_tags(template_text: str, max_iterations: int = 12) -> str:
    """Recursively resolve __tag__ and {a|b} choices until completely resolved."""
    current = template_text

    for _ in range(max_iterations):
        changed = False

        # 1. Resolve {choice1|choice2}
        if "{" in current and "}" in current:
            def replace_choice(match):
                choices = [c.strip() for c in match.group(1).split("|") if c.strip()]
                return random.choice(choices) if choices else ""
            new_text = re.sub(r"\{([^{}]+)\}", replace_choice, current)
            if new_text != current:
                current = new_text
                changed = True

        # 2. Resolve __wildcard_tag__ (supporting paths with slash, spaces, dashes)
        wildcard_pattern = r"__([a-zA-Z0-9_\-+/ \\.%]+)__"
        matches = list(re.finditer(wildcard_pattern, current))
        if matches:
            for m in matches:
                tag_name = m.group(1)
                full_tag = m.group(0)
                lines = _read_wildcard_lines(tag_name)
                if lines:
                    chosen_val = random.choice(lines)
                else:
                    # Resolve through fallback cleaner immediately
                    chosen_val = _clean_unresolved_wildcards(full_tag)
                current = current.replace(full_tag, chosen_val, 1)
                changed = True

        if not changed:
            break

    # Final guarantee: eliminate any remaining raw wildcard markers
    return _clean_unresolved_wildcards(current)


# Contemporary & School ethnicity and skin tone palettes
ETHNICITY_OPTIONS = (
    "Japanese", "Korean", "Chinese", "Thai", "Vietnamese", "Filipina",
    "Caucasian", "East Asian", "Southeast Asian", "Latina", "Mixed-race Asian-Caucasian",
    "Scandinavian", "French", "Italian", "British", "American", "Eurasian", "Half-Japanese"
)

SKIN_TONE_OPTIONS = (
    "fair skin", "pale skin", "porcelain skin", "tan skin", "natural skin", 
    "light skin", "olive skin", "sun-kissed tan skin", "golden skin",
    "brown skin", "dark skin", "deep brown skin", "bronze skin", "warm ivory skin"
)

def sample_ethnicity_and_skin(mode: str) -> tuple[str, str]:
    """Sample an ethnicity and natural single-token skin tone for contemporary and highschool characters."""
    mode_lower = str(mode or "").lower()
    if mode_lower == "highschool":
        weights = [
            "Japanese", "Japanese", "Japanese", "Korean", "Chinese", "East Asian",
            "Thai", "Chinese", "Mixed-race Asian-Caucasian", "Half-Japanese",
            "Russian", "Norwegian", "Swedish", "Romanian", "Persian", "Czech", 
            "Kazakhstanis", "Ukranian", "British", "USA", "Caucasian", "Eurasian"
        ]
        ethnicity = random.choice(weights)
    else:
        ethnicity = random.choice(ETHNICITY_OPTIONS)

    # Pick single skin tone without multiple undertone clauses
    wildcard_tones = _read_wildcard_lines("skin.txt") or _read_wildcard_lines("skin_tone.txt")
    cleaned_tones = []
    for t in (wildcard_tones or []):
        t_clean = re.sub(r"(?i),\s*.*undertone.*$", "", t).strip().lower()
        if t_clean:
            cleaned_tones.append(t_clean)
    if cleaned_tones:
        skin_tone = random.choice(cleaned_tones)
    else:
        skin_tone = random.choice(SKIN_TONE_OPTIONS)
    return ethnicity, skin_tone


HIGHSCHOOL_OUTFIT_VARIANTS = (
    {
        "outer": "school uniform blazer",
        "top": "white collared dress shirt with red ribbon tie",
        "bottom": "navy pleated school uniform skirt",
        "shoes": "black loafers",
        "socks": "white crew socks",
        "top_inner": "plain white school undershirt",
        "bottom_inner": "simple cotton panties",
        "head_acc": "red ribbon bowtie",
    },
    {
        "outer": "navy sailor uniform jacket with white collar and neckerchief",
        "top": "white sailor uniform top with navy trim",
        "bottom": "pleated sailor skirt",
        "shoes": "brown leather penny loafers",
        "socks": "knee-high navy socks",
        "top_inner": "soft cotton bralette",
        "bottom_inner": "plain cotton panties",
        "neck_acc": "sailor neckerchief",
    },
    {
        "outer": "oversized beige knit school cardigan",
        "top": "crisp white button-down uniform shirt with plaid necktie",
        "bottom": "grey tartan pleated school skirt",
        "shoes": "dark loafers",
        "socks": "white loose socks",
        "top_inner": "light cotton undershirt",
        "bottom_inner": "comfortable cotton panties",
        "neck_acc": "plaid necktie",
    },
    {
        "outer": "sleeveless navy school uniform sweater vest",
        "top": "short-sleeved white collared school shirt with cute bowtie",
        "bottom": "plaid pleated highschool skirt",
        "shoes": "clean white sneakers",
        "socks": "white ankle socks",
        "top_inner": "breathable sports bralette",
        "bottom_inner": "simple everyday panties",
        "head_acc": "hair ribbon",
    },
    {
        "outer": "fitted school track jacket",
        "top": "white gym uniform shirt with name badge",
        "bottom": "navy school gym shorts",
        "shoes": "athletic school running shoes",
        "socks": "cotton athletic crew socks",
        "top_inner": "athletic sports bra",
        "bottom_inner": "breathable cotton panties",
        "hand_acc": "wrist sweatbands",
    },
    {
        "outer": "charcoal grey school blazer with golden buttons",
        "top": "fitted white uniform blouse with striped necktie",
        "bottom": "dark pleated uniform mini skirt",
        "shoes": "polished black mary jane shoes",
        "socks": "over-the-knee black socks",
        "top_inner": "simple cotton bra",
        "bottom_inner": "plain white panties",
        "neck_acc": "striped necktie",
    },
    {
        "outer": "pastel school pullover sweater",
        "top": "white uniform shirt with sailor collar and ribbon",
        "bottom": "checkered pleated school uniform skirt",
        "shoes": "brown loafers",
        "socks": "black high socks",
        "top_inner": "soft white bralette",
        "bottom_inner": "soft cotton panties",
        "head_acc": "cute hair clip",
    },
)


CHARACTER_MODES = {
    "highschool": {
        "label": "High School Uniform",
        "races": ["human"],
        "jobs": [
            "highschool student and class representative",
            "highschool student in the literature club",
            "highschool student and track-and-field athlete",
            "highschool student working part-time at a nearby convenience store",
            "highschool student and student council vice president",
            "highschool student in the art club sketching after class",
            "highschool student in the school band practicing flute",
            "quiet highschool student who spends lunch breaks on the rooftop",
            "highschool student working a weekend café shift",
            "highschool student and archery club member",
            "transfer highschool student adapting to a new school",
            "highschool student tutoring classmates after school",
            "highschool student and school festival planning committee member",
            "highschool student walking home after cram school"
        ],
        "locations": [
            "a quiet classroom after school with afternoon golden hour light through windows",
            "an empty school rooftop with a gentle breeze and sunset city view",
            "a quiet highschool library between tall bookshelves",
            "a school corridor after final bell with lockers in the background",
            "a leafy school courtyard bench under cherry blossom trees",
            "a neighborhood convenience store after cram school on a rainy evening",
            "a school staircase landing with soft afternoon shadows",
            "a quiet school gymnasium entrance after practice",
            "a school music room beside a grand piano at dusk",
            "a cozy student café near the train station",
            "a pedestrian railway crossing on the walk home from school",
            "a quiet school rooftop garden at sunset"
        ],
    },
    "normal": {
        "label": "Contemporary / Non-Fantasy",
        "races": ["human"],
        "jobs": [
            "highschool student working a part-time after school", "college girl working as an online idol",
            "university student working a weekend café shift", "girl-next-door florist",
            "fashion model between studio shoots", "detective police officer following a missing-person lead",
            "night-shift nurse", "emergency physician", "barista who knows the regulars",
            "indie musician preparing for a small venue performance", "museum curator handling a disputed donation",
            "local journalist following a city-hall story", "software engineer staying late to fix a release",
            "restaurant chef during an unexpected dinner rush", "veterinarian finishing an evening appointment",
            "architect reviewing a renovation site", "bookstore manager closing up after an author event"
        ],
        "locations": [
            "a rain-soaked convenience store at midnight", "a crowded commuter train delayed between stations",
            "a quiet apartment rooftop garden at sunset", "a hospital staff lounge after a long shift",
            "a summer festival after the last fireworks", "a seaside photography studio before dawn",
            "a university library during a sudden storm", "a small apartment after a delivery mix-up",
            "a neighborhood laundromat on a rainy evening", "a nearly empty bookstore just before closing",
            "a late-night diner beside the highway", "a city park café on a quiet weekend morning"
        ],
    },
    "monster": {
        "label": "Monster Girl",
        "races": ["shapeshifter with subtle animal traits", "fox-eared beastkin", "tentacle-born abyssal girl",
                  "mermaid with iridescent scales", "arachnid woman with elegant chitin markings",
                  "serpentine naga", "harpy with broad feathered wings", "dragon-blooded girl"],
        "jobs": ["underwater salvage diver", "moonlit shrine guardian", "traveling healer", "black-market relic broker",
                  "lighthouse keeper", "royal bestiary caretaker", "glamorous stage performer", "wandering cartographer"],
        "locations": ["an Abandoned Labyrinth Maze", "a Cathedral Beneath the Sea", "a Monster-girl Underground Black Market Beneath the City",
                       "a Lighthouse during a violent storm", "a Bioluminescent Jungle Lagoon",
                       "an Abandoned Observatory surrounded by webs", "an Abandoned Laboratory"
                       "an ancient overgrown ruin cathedral courtyard", "a mystical luminous forest research camp",
                       "a bustling fantasy tavern during a guild auction", "a crystal-lit dungeon elevator",
                       "a moonlit castle balcony overlooking the kingdom", "a skyship dock above the clouds",
                       "a desert caravan oasis hiding a portal", "a magical academy greenhouse", "a haunted village market"],
    },
    "fantasy": {
        "label": "Fantasy Adventure",
        "races": ["human", "elf, long pointed ears", "half-elf, slightly pointed ears", "tiefling, curved horns and pointed tail",
                  "kitsune, fox ears and bushy tail", "dwarf artisan", "fae-blooded traveler"],
        "jobs": ["ranger", "mage-scholar", "knight", "rogue", "cleric", "alchemist", "battle chef",
                 "royal librarian", "arcane investigator", "beast tamer", "merchant guild negotiator",
                 "dragon-language translator", "traveling bard", "dungeon cartographer", "herbalist", "castle architect"],
        "locations": ["an ancient overgrown ruin cathedral courtyard", "a mystical luminous forest research camp",
                       "a bustling fantasy tavern during a guild auction", "a crystal-lit dungeon elevator",
                       "a moonlit castle balcony overlooking the kingdom", "a skyship dock above the clouds",
                       "a desert caravan oasis hiding a portal", "a magical academy greenhouse", "a haunted village market"],
    },
}

CONTEMPORARY_OUTFITS = {
    "outer": ("light denim jacket", "tailored blazer", "soft knit cardigan", "casual trench coat", "cropped utility jacket"),
    "top": ("clean white blouse", "fitted ribbed sweater", "simple graphic T-shirt", "button-up work shirt", "casual knit top"),
    "bottom": ("high-waisted jeans", "tailored slacks", "pleated midi skirt", "casual straight-leg trousers", "dark denim skirt"),
    "shoes": ("clean white sneakers", "low leather ankle boots", "simple loafers", "comfortable canvas shoes"),
    "socks": ("white ankle socks", "black crew socks", "sheer stockings", "invisible liner socks"),
    "top_inner": ("simple cotton bralette", "comfortable everyday bra"),
    "bottom_inner": ("comfortable everyday underwear", "simple cotton panties"),
    "neck_acc": ("delicate silver pendant necklace", "simple chain necklace", "minimalist choker"),
    "head_acc": ("simple hair clip", "slender headband", "subtle stud earrings"),
    "hand_acc": ("minimalist silver ring", "leather wrist watch", "simple bracelet"),
}


def _catalog_item_for_prompt(catalog_items: Dict[str, list], slot: str, prompt: str) -> Dict[str, str]:
    """Return the named catalogue record for a known garment prompt.

    School-uniform variants are intentionally authored as matched sets.  Resolve
    each component back through the catalogue instead of discarding its item
    identity and storing a bare prompt string.
    """
    target = str(prompt or "").strip().casefold()
    for item in catalog_items.get(slot, []) or []:
        if not isinstance(item, dict):
            continue
        item_prompt = str(item.get("prompt") or "").strip()
        item_name = str(item.get("name") or "").strip()
        if item_prompt and item_name and item_prompt.casefold() == target:
            return {"name": item_name, "prompt": item_prompt}
    # Catalogue may be incomplete while it is being refreshed.  Keep a useful,
    # specific item identity rather than falling back to an unnamed slot label.
    return {"name": str(prompt or "").strip(), "prompt": str(prompt or "").strip()}


def _catalog_item_for_category(
    catalog_items: Dict[str, list], slot: str, category: str, fallback_prompt: str,
) -> Dict[str, str]:
    """Pick a named catalogue item from one category and wardrobe slot."""
    wanted_category = str(category or "").strip().casefold()
    candidates = []
    for item in catalog_items.get(slot, []) or []:
        if not isinstance(item, dict):
            continue
        item_name = str(item.get("name") or "").strip()
        item_prompt = str(item.get("prompt") or "").strip()
        if item_name and item_prompt and str(item.get("category") or "").strip().casefold() == wanted_category:
            candidates.append({"name": item_name, "prompt": item_prompt})
    return random.choice(candidates) if candidates else {
        "name": str(fallback_prompt or "").strip(),
        "prompt": str(fallback_prompt or "").strip(),
    }

# These seeds make every generated card behaviorally distinct even when the
# LLM returns incomplete JSON. They describe relationship behavior, not a
# generic list of traits to paste into every character.
BEHAVIORAL_ARCHETYPES = (
    {
        "orientation": "bisexual, drawn to emotional honesty and self-possession",
        "courtship_style": "warm banter, small acts of care, and invitations that leave the other person room to choose",
        "initiative_rules": "waits for reciprocal interest, then makes a calm and unmistakable invitation",
        "preferred_dynamic": "affectionate switch who values equality and responsive communication",
        "attraction_signals": "remembers small details, seeks one-on-one conversation, and lets teasing become gently personal",
        "turn_ons": "competence, attentive listening, and honest vulnerability",
        "turn_offs": "showing off, pressure, and dismissing boundaries",
        "consent_style": "asks directly, waits for a clear answer, and treats hesitation as a reason to pause",
        "hard_limits": "coercion, humiliation, and ignored refusal",
        "pacing": "slow-burn; reserved early, playful after trust, direct only after mutual interest is clear",
        "aftercare": "quiet reassurance, water, and checking how the other person feels",
        "dialogue_behavior": "uses dry warmth and precise invitations; a refusal is kind but firm",
    },
    {
        "orientation": "queer, attracted to confidence that is considerate rather than controlling",
        "courtship_style": "bold eye contact, mischievous challenges, and spontaneous plans",
        "initiative_rules": "will initiate when chemistry is obvious but never assumes interest from flirtation alone",
        "preferred_dynamic": "playful leader who enjoys a partner willing to challenge her",
        "attraction_signals": "finds excuses to stay nearby, turns jokes into dares, and offers a disarming sincere compliment",
        "turn_ons": "wit, bravery, and being met as an equal",
        "turn_offs": "dishonesty, cruelty, and possessiveness",
        "consent_style": "makes boundaries explicit before escalating and checks in when the mood changes",
        "hard_limits": "manipulation, degradation, and any pressured roleplay",
        "pacing": "fast emotional spark but deliberate physical pacing until trust is proven",
        "aftercare": "humor to release tension followed by a genuine private check-in",
        "dialogue_behavior": "teases freely, but drops the teasing immediately if discomfort appears",
    },
    {
        "orientation": "demisexual, with attraction growing from loyalty, safety, and shared purpose",
        "courtship_style": "observant companionship, practical help, and gradually disclosed personal stories",
        "initiative_rules": "does not initiate early; needs repeated evidence of patience and mutual respect",
        "preferred_dynamic": "gentle, reciprocal, and emotionally grounded",
        "attraction_signals": "shares guarded truths, stays after the task is done, and becomes quietly protective",
        "turn_ons": "reliability, consent-aware tenderness, and intellectual connection",
        "turn_offs": "rushing intimacy, public pressure, and broken promises",
        "consent_style": "names what she wants in plain language and needs a verbal confirmation",
        "hard_limits": "coercion, public exposure, and emotional manipulation",
        "pacing": "very gradual; affection changes from cautious distance to deliberate closeness",
        "aftercare": "calm conversation, a familiar routine, and reassurance that nothing was expected in return",
        "dialogue_behavior": "speaks sparingly at first; intimacy makes her more honest, not more theatrical",
    },
    {
        "orientation": "pansexual, attracted to presence, imagination, and respectful confidence",
        "courtship_style": "creative gifts, theatrical flirtation, and carefully planned moments",
        "initiative_rules": "initiates only after stating what she is asking for and receiving an enthusiastic response",
        "preferred_dynamic": "expressive switch who enjoys collaborative play and mutual attention",
        "attraction_signals": "composes personal compliments, creates a private ritual, and asks surprisingly perceptive questions",
        "turn_ons": "creativity, praise freely given, and mutual curiosity",
        "turn_offs": "mockery, carelessness, and treating intimacy as a performance for others",
        "consent_style": "uses explicit invitations and treats a change of mind as ordinary and welcome",
        "hard_limits": "non-consent, humiliation without prior agreement, and emotional coercion",
        "pacing": "romantic and intentional; grows bolder with reassurance rather than pressure",
        "aftercare": "affectionate debriefing, soft music or a shared quiet activity",
        "dialogue_behavior": "language is vivid and flirtatious but never evasive about requests or limits",
    },
    {
        "orientation": "lesbian, strongly attracted to capable women with a quietly assertive presence",
        "courtship_style": "measured compliments, protective gestures, and deliberately building private tension",
        "initiative_rules": "takes the lead after receiving unmistakable reciprocal interest",
        "preferred_dynamic": "confident dominant who enjoys negotiated control and an engaged, expressive partner",
        "attraction_signals": "holds eye contact, closes distance deliberately, and gives precise personal praise",
        "turn_ons": "obedience freely offered, praise, light restraint, anticipation, and affectionate possessiveness",
        "turn_offs": "passivity without communication, performative submission, jealousy games, and disrespect",
        "consent_style": "negotiates roles and signals clearly before taking control",
        "hard_limits": "coercion, fear-based play, public exposure, and ignored safewords",
        "pacing": "controlled and unhurried, building tension before becoming openly demanding",
        "aftercare": "physical closeness, praise, water, and a calm review of what felt best",
        "dialogue_behavior": "uses low, direct instructions and rewards honest reactions with warmth",
    },
    {
        "orientation": "heterosexual, drawn to patient and emotionally steady men",
        "courtship_style": "reserved flirting, lingering proximity, and gradually revealing private fantasies",
        "initiative_rules": "invites the partner to lead once safety, discretion, and mutual desire are established",
        "preferred_dynamic": "devoted submissive who enjoys structure, guidance, and attentive authority",
        "attraction_signals": "becomes unusually compliant, asks personal questions, and quietly tests reliability",
        "turn_ons": "confident leadership, praise, consensual restraint, ritual, and being carefully directed",
        "turn_offs": "impatience, ridicule, unpredictable aggression, and emotionally detached control",
        "consent_style": "discusses limits beforehand and uses clear verbal check-ins and safewords",
        "hard_limits": "coercion, degradation, abandonment, and any punishment without prior agreement",
        "pacing": "slow surrender, beginning tenderly and deepening only with consistent reassurance",
        "aftercare": "being held, gentle praise, warmth, hydration, and dependable emotional presence",
        "dialogue_behavior": "starts shy and indirect, then becomes candid about wanting guidance",
    },
    {
        "orientation": "bisexual, attracted to bold personalities and playful sexual confidence",
        "courtship_style": "competitive flirting, provocative dares, and humor charged with obvious chemistry",
        "initiative_rules": "initiates readily when interest is explicit and pauses to negotiate unfamiliar play",
        "preferred_dynamic": "adventurous switch who alternates control and enjoys energetic reciprocity",
        "attraction_signals": "turns banter into challenges, mirrors touch, and proposes increasingly private games",
        "turn_ons": "role reversal, playful power exchange, praise, light bondage, costumes, and novelty",
        "turn_offs": "repetition without connection, fragile egos, selfishness, and refusal to communicate",
        "consent_style": "uses enthusiastic verbal agreement, negotiated signals, and frequent playful check-ins",
        "hard_limits": "non-consent, genuine humiliation, injury, and involving unconsenting observers",
        "pacing": "quick chemistry with deliberate negotiation before anything intense or unfamiliar",
        "aftercare": "laughter, affectionate touch, snacks, and an honest conversation about favorite moments",
        "dialogue_behavior": "is openly suggestive, witty, and comfortable asking for exactly what she wants",
    },
    {
        "orientation": "pansexual and sensually motivated, valuing attentiveness more than gender or status",
        "courtship_style": "luxurious hospitality, sustained touch, sensory gifts, and intimate conversation",
        "initiative_rules": "creates an inviting atmosphere and offers choices rather than assuming a partner's desires",
        "preferred_dynamic": "service-oriented switch focused on mutual pleasure and responsive body language",
        "attraction_signals": "notices subtle reactions, offers tailored comforts, and makes ordinary contact feel intentional",
        "turn_ons": "massage, praise, sensory play, mutual focus, elegant lingerie, and prolonged anticipation",
        "turn_offs": "rushing, poor hygiene, inattentiveness, emotional coldness, and treating pleasure as a performance",
        "consent_style": "checks preferences in plain language and adjusts immediately to verbal or physical feedback",
        "hard_limits": "coercion, pain beyond prior agreement, humiliation, and disregard for physical comfort",
        "pacing": "slow, immersive, and highly responsive, favoring buildup over urgency",
        "aftercare": "clean linens, water, gentle massage, affectionate conversation, and quiet rest together",
        "dialogue_behavior": "uses warm questions, specific praise, and softly confident suggestions",
    },
    {
        "orientation": "bisexual, especially attracted to composed partners who can handle playful defiance",
        "courtship_style": "provoking banter, mock challenges, and deliberately testing a partner's confidence",
        "initiative_rules": "invites pursuit through obvious teasing but requires explicit agreement before power play",
        "preferred_dynamic": "bratty submissive who enjoys earning firm guidance without surrendering her wit",
        "attraction_signals": "playfully disobeys harmless requests, seeks reactions, and becomes sincere in private",
        "turn_ons": "verbal sparring, negotiated discipline, playful restraint, earned praise, and confident correction",
        "turn_offs": "genuine anger, fragile authority, cruelty, inconsistent rules, and punishment without care",
        "consent_style": "negotiates the difference between playful resistance and a genuine stop signal",
        "hard_limits": "real intimidation, coercion, degrading identity-based language, and ignored safewords",
        "pacing": "mischievous and provocative at first, becoming softer as mutual trust is demonstrated",
        "aftercare": "reassurance, affectionate praise, humor, a warm drink, and closeness without demands",
        "dialogue_behavior": "uses cheeky challenges during flirtation and becomes direct when naming genuine needs",
    },
    {
        "orientation": "queer, drawn to sensitive partners who respond well to nurturing confidence",
        "courtship_style": "gentle attention, reassuring touch, thoughtful planning, and quietly decisive invitations",
        "initiative_rules": "leads once a partner expresses a desire for guidance and continues checking comfort",
        "preferred_dynamic": "gentle dominant who combines structure, praise, caretaking, and calm authority",
        "attraction_signals": "anticipates needs, gives focused compliments, and creates a safe private atmosphere",
        "turn_ons": "service, praise, guided surrender, soft commands, ritual, and attentive sensory play",
        "turn_offs": "recklessness, emotional games, performative toughness, poor communication, and needless pain",
        "consent_style": "sets expectations collaboratively and uses regular verbal and nonverbal check-ins",
        "hard_limits": "coercion, abandonment scenarios, severe pain, humiliation, and emotional manipulation",
        "pacing": "patient and ceremonial, allowing anticipation to build through small acts of obedience",
        "aftercare": "blankets, hydration, soothing touch, praise, and an unhurried emotional debrief",
        "dialogue_behavior": "speaks with calm certainty, gives choices clearly, and praises honest vulnerability",
    },
    {
        "orientation": "heteroflexible, attracted to charisma, physical confidence, and controlled intensity",
        "courtship_style": "charged eye contact, competitive physical activities, and direct invitations",
        "initiative_rules": "moves quickly when desire is mutual but negotiates intensity and boundaries first",
        "preferred_dynamic": "primal switch who enjoys consensual pursuit, resistance, and changes of control",
        "attraction_signals": "becomes physically playful, watches reactions closely, and challenges a partner to keep up",
        "turn_ons": "consensual chase, wrestling, assertive touch, biting within limits, and instinctive roleplay",
        "turn_offs": "timidity without communication, uncontrolled aggression, carelessness, and broken agreements",
        "consent_style": "establishes safe signals, physical limits, and exactly when resistance remains playful",
        "hard_limits": "actual violence, fear without consent, injury, breath restriction, and impaired judgment",
        "pacing": "fast and energetic after careful negotiation, with frequent checks during intense play",
        "aftercare": "cooling down together, water, checking for discomfort, reassurance, and quiet physical closeness",
        "dialogue_behavior": "uses brief challenges and confident demands but immediately respects a genuine stop",
    },
    {
        "orientation": "pansexual, attracted to imagination, intelligence, and partners who enjoy inhabiting a role",
        "courtship_style": "inventive scenarios, coded invitations, shared fiction, and elaborate private games",
        "initiative_rules": "proposes a scenario openly and separates character roles from real-life consent",
        "preferred_dynamic": "immersive roleplay switch who enjoys costumes, personas, and negotiated power stories",
        "attraction_signals": "shares private creative ideas, writes suggestive scenarios, and invites collaborative planning",
        "turn_ons": "costumes, fantasy roles, scripted tension, praise, authority play, and surprising character reversals",
        "turn_offs": "mocking fantasies, breaking character to belittle someone, poor preparation, and blurred boundaries",
        "consent_style": "agrees on roles, forbidden themes, exit signals, and post-scene expectations in advance",
        "hard_limits": "non-consensual themes without negotiation, identity-based degradation, recording, and public exposure",
        "pacing": "carefully planned buildup followed by expressive, theatrical play and a clear return to reality",
        "aftercare": "dropping character explicitly, affectionate reassurance, refreshments, and discussing favorite details",
        "dialogue_behavior": "adapts her voice to the role while remaining unmistakably clear during check-ins",
    },
    {
        "orientation": "lesbian, drawn to stylish women who share her taste for controlled exhibition and glamour",
        "courtship_style": "fashion-focused compliments, private photographs, elegant dates, and bold mutual admiration",
        "initiative_rules": "suggests visually expressive play only after confirming privacy and enthusiastic interest",
        "preferred_dynamic": "glamorous switch who enjoys being admired as much as directing a partner's presentation",
        "attraction_signals": "adjusts a partner's outfit, offers lingering compliments, and invites private posing",
        "turn_ons": "lingerie, mirrors, consensual photography, dressing up, praise, posing, and mutual display",
        "turn_offs": "unauthorized sharing, careless privacy, body criticism, jealousy, and unwanted spectators",
        "consent_style": "confirms what may be seen, photographed, stored, or deleted before any visual play",
        "hard_limits": "secret recording, public exposure, identifiable sharing, coercion, and appearance-based humiliation",
        "pacing": "flirtatious and visually focused, with deliberate staging and regular privacy checks",
        "aftercare": "compliments, reviewing or deleting images together, skincare, refreshments, and affectionate closeness",
        "dialogue_behavior": "gives precise aesthetic praise and directly asks how visible or daring a partner wants to be",
    },
    {
        "orientation": "bisexual and non-monogamy-friendly, attracted to emotionally mature and communicative adults",
        "courtship_style": "transparent flirting, candid expectation-setting, and introducing new connections without secrecy",
        "initiative_rules": "initiates only after relationship agreements, safer-sex expectations, and other partners are discussed",
        "preferred_dynamic": "social switch comfortable with casual intimacy, recurring partners, or consensual group dynamics",
        "attraction_signals": "states interest plainly, discusses availability, and includes partners in relevant decisions",
        "turn_ons": "compersion, shared attention, partner swapping, collaborative flirting, and confident communication",
        "turn_offs": "hidden agreements, jealousy games, triangulation, unsafe practices, and treating partners as accessories",
        "consent_style": "requires informed agreement from every involved adult and revisits consent as dynamics change",
        "hard_limits": "deception, unprotected risk without disclosure, intoxicated consent, coercion, and excluded stakeholders",
        "pacing": "socially open but logistically deliberate, prioritizing discussion before expanding the dynamic",
        "aftercare": "individual check-ins, group reassurance where appropriate, hydration, and follow-up the next day",
        "dialogue_behavior": "is candid about attraction, agreements, jealousy, health, and emotional expectations",
    },
)
_LAST_BEHAVIOR_INDEX: Optional[int] = None
AGE_RANGES = (
    (13, 19),
    (20, 24),
    (25, 29),
    (30, 35),
    (36, 42),
    (43, 50),
)


def _behavioral_seed() -> Dict[str, str]:
    """Return a fresh behavioral archetype without repeating the prior card."""
    global _LAST_BEHAVIOR_INDEX
    options = list(range(len(BEHAVIORAL_ARCHETYPES)))
    if _LAST_BEHAVIOR_INDEX in options and len(options) > 1:
        options.remove(_LAST_BEHAVIOR_INDEX)
    _LAST_BEHAVIOR_INDEX = random.choice(options)
    return dict(BEHAVIORAL_ARCHETYPES[_LAST_BEHAVIOR_INDEX])


def _behavior_profile_text(behavior: Dict[str, Any], age: Optional[int] = None) -> str:
    """Build a natural, layered preference profile instead of a flat label list."""
    def value(key: str, fallback: str = "") -> str:
        return str(behavior.get(key) or fallback).strip().rstrip(". ;")

    def sentence(text: str) -> str:
        text = text.strip()
        return f"{text[0].upper()}{text[1:]}." if text else ""

    orientation = value("orientation", "her attraction is guided by personal chemistry")
    courtship = value("courtship_style", "patient conversation and mutual curiosity")
    signals = value("attraction_signals", "seeking private time and offering sincere attention")
    pacing = value("pacing", "lets closeness develop at a pace that feels mutual")
    dialogue = value("dialogue_behavior", "becomes more candid as trust grows")

    if age is not None and int(age) < 13:
        return " ".join(filter(None, (
            sentence(f"Romantically, she is {orientation}"),
            sentence(f"Her courtship style centers on {courtship}, and she shows interest by {signals}"),
            sentence(f"She {pacing}; in conversation, she {dialogue}"),
        )))

    dynamic = value("preferred_dynamic", "a reciprocal dynamic shaped by trust and communication")
    initiative = value("initiative_rules", "waits for clear mutual interest before initiating")
    turn_ons = value("turn_ons", "confidence, attentiveness, and emotional honesty")
    turn_offs = value("turn_offs", "pressure, carelessness, and emotional distance")
    consent = value("consent_style", "communicates directly and checks that enthusiasm remains mutual")
    limits = value("hard_limits", "coercion and ignored refusal")
    aftercare = value("aftercare", "reassurance and a private emotional check-in")

    return " ".join(filter(None, (
        sentence(f"She is {orientation}, and she prefers {dynamic}"),
        sentence(f"Attraction develops through {courtship}; she reveals it by {signals}"),
        sentence(f"She {initiative}. Her strongest turn-ons are {turn_ons}, while {turn_offs} quickly extinguish her interest"),
        sentence(f"Her consent style is deliberate: she {consent}. Her non-negotiable limits are {limits}"),
        sentence(f"Her preferred pacing is {pacing}, followed by {aftercare}"),
        sentence(f"In intimate conversation, she {dialogue}"),
    )))


def _sample_age(specific_age: Optional[int] = None) -> tuple[int, int, int]:
    """Pick a varied age band, or use one explicitly requested age."""
    if specific_age is not None:
        age = int(specific_age)
        minimum = maximum = age
    else:
        minimum, maximum = random.choice(AGE_RANGES)
        age = random.randint(minimum, maximum)
    return minimum, maximum, age


def sample_rpg_female_wildcard_matrix(
    mode: str = "fantasy", specific_age: Optional[int] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Sample a female character matrix for contemporary, monster, or fantasy mode."""
    overrides = overrides or {}
    profile = CHARACTER_MODES.get(str(mode or "fantasy").lower(), CHARACTER_MODES["fantasy"])
    # 1. Races, Ethnicity & Skin Tone
    mode_str = str(mode or "fantasy").lower()
    is_fantasy = (mode_str == "fantasy")
    is_monster = (mode_str == "monster")
    if is_monster:
        monster_races = _read_wildcard_lines("monster_girl/races.txt") or profile["races"]
        raw_race = random.choice(monster_races)
        resolved_heritage = _resolve_template_tags(raw_race)
        resolved_skin = random.choice(SKIN_TONE_OPTIONS)
        heritage_label = resolved_heritage
    elif not is_fantasy:
        ethnicity, skin_tone = sample_ethnicity_and_skin(mode_str)
        heritage_label = ethnicity
        resolved_heritage = ethnicity
        resolved_skin = skin_tone
    else:
        races = _read_wildcard_lines("fantasy/races.txt") or _read_wildcard_lines("race.txt") or profile["races"]
        raw_race = random.choice(races)
        resolved_heritage = _resolve_template_tags(raw_race)
        resolved_skin = random.choice(SKIN_TONE_OPTIONS)
        heritage_label = resolved_heritage

    if is_fantasy:
        jobs = _read_wildcard_lines("fantasy/jobs_adventurer.txt") or _read_wildcard_lines("job_adventurer.txt") or profile["jobs"]
    elif mode_str == "normal":
        jobs = _read_wildcard_lines("contemporary/jobs.txt") or profile["jobs"]
    else:
        jobs = profile["jobs"]
    raw_job = _resolve_template_tags(random.choice(jobs))

    # 2. Physical Appearance
    haircuts = _read_wildcard_lines("haircut-female.txt") or ["long braided hair", "ponytail", "bob cut", "wavy twin tails", "flowing straight hair"]
    hair_colors = _read_wildcard_lines("hair_color.txt") or ["silver hair", "golden blonde hair", "raven black hair", "crimson red hair", "pastel pink hair"]
    eye_colors = _read_wildcard_lines("eye_color.txt") or ["amber eyes", "sapphire blue eyes", "crimson red eyes", "emerald green eyes", "violet eyes"]
    bust_sizes = _read_wildcard_lines("bust_size.txt") or ["medium breasts", "large breasts", "slender chest", "perky breasts"]
    figure_types = _read_wildcard_lines("figure_type.txt") or [
        "slender figure", "curvaceous hourglass body", "athletic toned physique",
        "petite frame", "curvy voluptuous body", "slim build", "pear-shaped build",
        "soft curvaceous figure", "tall slender figure", "compact athletic build"
    ]
    waist_sizes = _read_wildcard_lines("waist_size.txt") or [
        "slender waist", "narrow waist", "tiny waist", "slim waist",
        "defined waist", "tapered waist", "toned waist", "petite waist"
    ]
    thigh_sizes = _read_wildcard_lines("thigh_size.txt") or [
        "slender thighs", "thick thighs", "toned thighs", "shapely thighs",
        "curvy thighs", "plump thighs", "smooth thighs", "athletic thighs"
    ]
    pubic_styles = _read_wildcard_lines("pubic_style.txt") or [
        "shaved pussy", "trimmed pubic hair", "neat landing strip",
        "natural pubic hair", "bare pubic area"
    ]

    raw_hair = f"{random.choice(haircuts)}, {random.choice(hair_colors)}"
    raw_eyes = random.choice(eye_colors)
    chosen_figure = random.choice(figure_types)
    chosen_bust = random.choice(bust_sizes)
    chosen_waist = random.choice(waist_sizes)
    chosen_thigh = random.choice(thigh_sizes)
    chosen_pubic = random.choice(pubic_styles)
    raw_body = f"{chosen_figure}, {chosen_bust}, {chosen_waist}, {chosen_thigh}, {chosen_pubic}"

    hair_chosen = _resolve_template_tags(raw_hair)
    eyes_chosen = _resolve_template_tags(raw_eyes)
    body_chosen = _resolve_template_tags(raw_body)


    # 3. Attire from Wardrobe Catalog
    outfit_tags = {}
    catalog_items = {}
    if os.path.exists(CATALOG_PATH):
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                catalog_data = json.load(f)
                catalog_items = catalog_data.get("slots", {})
        except Exception:
            pass

    mode_str = str(mode or "fantasy").lower()
    if mode_str == "highschool":
        hs_outfit = random.choice(HIGHSCHOOL_OUTFIT_VARIANTS)
        outer_item = _catalog_item_for_prompt(catalog_items, "outer", hs_outfit["outer"])
        top_item = _catalog_item_for_prompt(catalog_items, "top", hs_outfit["top"])
        bottom_item = _catalog_item_for_prompt(catalog_items, "bottom", hs_outfit["bottom"])
        shoes_item = _catalog_item_for_prompt(catalog_items, "shoes", hs_outfit["shoes"])
        socks_item = _catalog_item_for_prompt(catalog_items, "socks", hs_outfit.get("socks", "white crew socks"))
        top_inner_item = _catalog_item_for_prompt(catalog_items, "top_inner", hs_outfit["top_inner"])
        bottom_inner_item = _catalog_item_for_prompt(catalog_items, "bottom_inner", hs_outfit["bottom_inner"])
        head_item = _catalog_item_for_prompt(catalog_items, "head", hs_outfit.get("head", "hair ribbon"))
        head_acc_item = _catalog_item_for_prompt(catalog_items, "accessories", hs_outfit.get("head_acc", "hair ribbon"))
        neck_acc_item = _catalog_item_for_prompt(catalog_items, "neck", hs_outfit.get("neck_acc", "ribbon tie"))
        hand_acc_item = _catalog_item_for_prompt(catalog_items, "hands", hs_outfit.get("hand_acc", "wristband"))
        leg_acc_item = _catalog_item_for_prompt(catalog_items, "accessories", hs_outfit.get("leg_acc", "leg strap"))
    elif mode_str == "normal":
        outer_item = _catalog_item_for_category(catalog_items, "outer", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["outer"]))
        top_item = _catalog_item_for_category(catalog_items, "top", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["top"]))
        bottom_item = _catalog_item_for_category(catalog_items, "bottom", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["bottom"]))
        shoes_item = _catalog_item_for_category(catalog_items, "shoes", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["shoes"]))
        socks_item = _catalog_item_for_category(catalog_items, "socks", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["socks"]))
        top_inner_item = _catalog_item_for_category(catalog_items, "top_inner", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["top_inner"]))
        bottom_inner_item = _catalog_item_for_category(catalog_items, "bottom_inner", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["bottom_inner"]))
        head_item = _catalog_item_for_category(catalog_items, "head", "Contemporary", "stylish sun hat")
        head_acc_item = _catalog_item_for_category(catalog_items, "accessories", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["head_acc"]))
        neck_acc_item = _catalog_item_for_category(catalog_items, "neck", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["neck_acc"]))
        hand_acc_item = _catalog_item_for_category(catalog_items, "hands", "Contemporary", random.choice(CONTEMPORARY_OUTFITS["hand_acc"]))
        leg_acc_item = _catalog_item_for_category(catalog_items, "accessories", "Contemporary", "delicate ankle bracelet")
    else:
        outer_item = random.choice(catalog_items.get("outer", [])) if catalog_items.get("outer") else {"prompt": "leather traveler cloak"}
        top_item = random.choice(catalog_items.get("top", [])) if catalog_items.get("top") else {"prompt": "fitted linen tunic"}
        bottom_item = random.choice(catalog_items.get("bottom", [])) if catalog_items.get("bottom") else {"prompt": "leather travel pants"}
        shoes_item = random.choice(catalog_items.get("shoes", [])) if catalog_items.get("shoes") else {"prompt": "leather adventuring boots"}
        socks_item = random.choice(catalog_items.get("socks", [])) if catalog_items.get("socks") else {"prompt": "adventurer wool socks"}
        top_inner_item = random.choice(catalog_items.get("top_inner", [])) if catalog_items.get("top_inner") else {"prompt": "silk bralette"}
        bottom_inner_item = random.choice(catalog_items.get("bottom_inner", [])) if catalog_items.get("bottom_inner") else {"prompt": "matching panties"}
        head_item = random.choice(catalog_items.get("head", [])) if catalog_items.get("head") else {"prompt": "hooded traveler mantle"}
        head_acc_item = random.choice(catalog_items.get("accessories", [])) if catalog_items.get("accessories") else {"prompt": "silver hair pin"}
        neck_acc_item = random.choice(catalog_items.get("neck", [])) if catalog_items.get("neck") else {"prompt": "enchanted protective amulet"}
        hand_acc_item = random.choice(catalog_items.get("hands", [])) if catalog_items.get("hands") else {"prompt": "leather archer gloves"}
        leg_acc_item = {"prompt": "leather dagger sheath strap"}

    # Apply user overrides if specified
    if overrides.get("outer"):
        outer_item = {"name": str(overrides["outer"]).strip(), "prompt": str(overrides["outer"]).strip()}
    if overrides.get("top"):
        top_item = {"name": str(overrides["top"]).strip(), "prompt": str(overrides["top"]).strip()}
    if overrides.get("bottom"):
        bottom_item = {"name": str(overrides["bottom"]).strip(), "prompt": str(overrides["bottom"]).strip()}
    if overrides.get("shoes"):
        shoes_item = {"name": str(overrides["shoes"]).strip(), "prompt": str(overrides["shoes"]).strip()}
    if overrides.get("socks"):
        socks_item = {"name": str(overrides["socks"]).strip(), "prompt": str(overrides["socks"]).strip()}
    if overrides.get("top_inner"):
        top_inner_item = {"name": str(overrides["top_inner"]).strip(), "prompt": str(overrides["top_inner"]).strip()}
    if overrides.get("bottom_inner"):
        bottom_inner_item = {"name": str(overrides["bottom_inner"]).strip(), "prompt": str(overrides["bottom_inner"]).strip()}
    if overrides.get("head"):
        head_item = {"name": str(overrides["head"]).strip(), "prompt": str(overrides["head"]).strip()}
    if overrides.get("neck_acc"):
        neck_acc_item = {"name": str(overrides["neck_acc"]).strip(), "prompt": str(overrides["neck_acc"]).strip()}
    if overrides.get("accessories"):
        head_acc_item = {"name": str(overrides["accessories"]).strip(), "prompt": str(overrides["accessories"]).strip()}

    def _outfit_slot(item: Dict[str, Any], active: bool) -> Dict[str, Any]:
        prompt = str(item.get("prompt") or item.get("name") or "").strip()
        return {"name": str(item.get("name") or prompt).strip(), "prompt": prompt, "active": active}

    outfits = {
        "outer": _outfit_slot(outer_item, bool(outer_item["prompt"])),
        "top": _outfit_slot(top_item, bool(top_item["prompt"])),
        "bottom": _outfit_slot(bottom_item, bool(bottom_item["prompt"])),
        "shoes": _outfit_slot(shoes_item, bool(shoes_item["prompt"])),
        "socks": _outfit_slot(socks_item, bool(socks_item["prompt"])),
        "top_inner": _outfit_slot(top_inner_item, True),
        "bottom_inner": _outfit_slot(bottom_inner_item, True),
        "head": _outfit_slot(head_item, bool(overrides.get("head"))),
        "head_acc": _outfit_slot(head_acc_item, mode_str == "highschool" or bool(overrides.get("accessories"))),
        "neck_acc": _outfit_slot(neck_acc_item, mode_str == "highschool" or bool(overrides.get("neck_acc"))),
        "hand_acc": _outfit_slot(hand_acc_item, False),
        "leg_acc": _outfit_slot(leg_acc_item, False),
        "naked": {"prompt": "naked", "active": False}
    }

    # 4. Location & Environment
    locations = (_read_wildcard_lines("location+theme.txt") if mode == "fantasy" else []) or profile["locations"] or [
        "ancient overgrown ruin cathedral courtyard", "mystical luminous glowing forest", "bustling fantasy tavern corner",
        "dungeon cavern lit by crystals", "moonlit castle balcony overlooking kingdom"
    ]
    resolved_location = _resolve_template_tags(random.choice(locations))

    # 5. Scene & Composition
    compositions = _read_wildcard_lines("composition.txt") or ["cowboy shot, looking at viewer", "three-quarter view, dramatic angle", "portrait shot, soft depth of field"]
    resolved_composition = _resolve_template_tags(random.choice(compositions))

    visual_quality = _read_wildcard_lines("visual_quality.txt")
    quality_str = visual_quality[0] if visual_quality else "masterpiece, high quality, highly detailed, sharp focus"
    behavior_seed = _behavioral_seed()
    if str(mode or '').lower() == 'highschool' and specific_age is None:
        age_min, age_max, age = 13, 50, random.randint(13, 50)
    else:
        age_min, age_max, age = _sample_age(specific_age)
    sampled_ethnicity = ethnicity if mode_str in ("highschool", "normal") else None
    identity_seed = _identity_seed(mode_str, ethnicity=sampled_ethnicity)

    # Tailor clothing & appearance tags for Monster Girl anatomical integrity
    is_legless_monster = is_monster and any(k in str(resolved_heritage).lower() for k in [
        "lamia", "snake", "serpent", "arachne", "spider", "mermaid", "siren", "centaur", "scylla", "alraune", "sphinx"
    ])

    if is_monster:
        # Avoid conflicting human clothing tags on non-human lower body parts
        if is_legless_monster:
            wearing_parts = [p for p in [outer_item['prompt'], top_item['prompt'], neck_acc_item.get('prompt')] if p]
            wearing_str = f"wearing {', '.join(wearing_parts)}, " if wearing_parts else ""
        else:
            wearing_str = f"wearing {outer_item['prompt']}, {top_item['prompt']}, {bottom_item['prompt']}, {socks_item['prompt']}, {shoes_item['prompt']}, "

        monster_lead = "(monster girl:1.25), (monstrous non-human anatomy:1.2), "
        avatar_prompt = _clean_unresolved_wildcards(
            f"{monster_lead}1girl, {age}-year-old, solo, {resolved_heritage}, {hair_chosen}, {eyes_chosen}, {body_chosen}, "
            f"{wearing_str}in {resolved_location}, {resolved_composition}, {quality_str}"
        )
        image_appearance = _clean_unresolved_wildcards(
            f"{monster_lead}1girl, {age}-year-old, solo, {resolved_heritage}, {hair_chosen}, {eyes_chosen}, {body_chosen}"
        )
    else:
        avatar_prompt = _clean_unresolved_wildcards(
            f"1girl, {age}-year-old, solo, {resolved_heritage}, {resolved_skin}, {raw_job}, {hair_chosen}, {eyes_chosen}, {body_chosen}, "
            f"wearing {outer_item['prompt']}, {top_item['prompt']}, {bottom_item['prompt']}, {socks_item['prompt']}, {shoes_item['prompt']}, "
            f"in {resolved_location}, {resolved_composition}, {quality_str}"
        )
        image_appearance = _clean_unresolved_wildcards(
            f"1girl, {age}-year-old, solo, {resolved_heritage}, {resolved_skin}, {hair_chosen}, {eyes_chosen}, {body_chosen}"
        )

    result = {
        "gender": "Female",
        "mode": str(mode or "fantasy").lower(),
        "mode_label": profile["label"],
        "behavior_seed": behavior_seed,
        "age_range": f"{age_min}-{age_max}",
        "age": age,
        "identity_seed": identity_seed,
        "skin": _clean_unresolved_wildcards(resolved_skin),
        "job": _clean_unresolved_wildcards(raw_job),
        "hair": _clean_unresolved_wildcards(hair_chosen),
        "eyes": _clean_unresolved_wildcards(eyes_chosen),
        "body": _clean_unresolved_wildcards(body_chosen),
        "figure": _clean_unresolved_wildcards(chosen_figure),
        "waist": _clean_unresolved_wildcards(chosen_waist),
        "thigh": _clean_unresolved_wildcards(chosen_thigh),
        "pubic": _clean_unresolved_wildcards(chosen_pubic),
        "image_appearance": image_appearance,
        "location": _clean_unresolved_wildcards(resolved_location),
        "outfits": outfits,
        "avatar_prompt": avatar_prompt
    }
    if is_fantasy:
        result["race"] = _clean_unresolved_wildcards(resolved_heritage)
    else:
        result["ethnicity"] = _clean_unresolved_wildcards(resolved_heritage)
        result["race"] = result["ethnicity"]  # compatibility fallback

    return result


def synthesize_complete_character_card(matrix: Dict[str, Any], query_llm_func) -> Dict[str, Any]:
    """Uses LLM to synthesize a full multi-dimensional RealmPlay character card based on wildcards matrix in 100% English."""
    prompt = f"""You are a master Character Designer for RealmPlay (RPG Fantasy & Adult NSFW H-Mode).
Create a rich, multi-dimensional female character card based on the sampled wildcards matrix below.
IMPORTANT: You MUST write EVERYTHING strictly in 100% ENGLISH. Do not use any Thai or other non-English language.
The character's sexuality must be individual and behaviorally visible, never a generic list copied between characters.

[Wildcards Matrix]
- Gender: {matrix['gender']}
- Race / Heritage: {matrix['race']}
- Class / Profession / Role: {matrix['job']}
- Physical Attributes: {matrix['hair']}, Eyes: {matrix['eyes']}, Physique: {matrix['body']}
- Starting Attire: {matrix['outfits']['outer']['prompt']}, {matrix['outfits']['top']['prompt']}, {matrix['outfits']['bottom']['prompt']}
- Opening Location: {matrix['location']}
- Character Mode: {matrix.get('mode_label', matrix.get('mode', 'Fantasy'))}
- Required age range: {matrix.get('age_range', '13-50')}; use this exact age: {matrix.get('age', 13)} years old.
- Required identity seed: {json.dumps(matrix.get('identity_seed') or {}, ensure_ascii=False)}
- Required behavioral seed: {json.dumps(matrix.get('behavior_seed') or {}, ensure_ascii=False)}

You MUST preserve and elaborate this behavioral seed in `intimacy_behavior`. Do not replace it with a generic profile.
You MUST use the exact seeded first and family name. Make the personality, appearance, and background concrete expansions of the identity seed; do not reuse generic fantasy phrasing, interchangeable trauma, or stock descriptions.

Respond with a strictly valid JSON object (and ONLY JSON, no conversational markdown or preamble) with the following fields:
{{
  "name": "Only character full name with given name and optional surname separated by a space (e.g. 'Jennifer Lopez' or 'Aeloria Silverwhisper'), strictly NO titles, epithets, honorifics, or commas (e.g. do NOT write 'the Wandering Arcanist')",
  "gender": "Female",
  "age": "Use the required exact age above, formatted as e.g. '13 years old'.",
  "status": "Marital or relationship status (e.g. 'Single', 'In a relationship', 'Married', 'Divorced')",
  "personality": "Detailed personality traits, core values, psychological strengths, vulnerabilities, behavioral quirks, and mannerisms",
  "appearance": "Rich narrative physical description: face, expressions, hair color and style, eyes, body proportions, posture, skin texture, and aesthetic details",
  "role_goals": "Social standing, vocation, affiliations, and compelling personal ambitions or quests (e.g. 'Senior Monster Hunter, seeking legendary beasts')",
  "baseline_relationship": "Initial dynamic with {{{{user}}}} (e.g. adventuring companion bound by contract, survivor rescued from ruins, rival turned reluctant ally)",
  "background": "In-depth backstory, formative life events, training, and past history leading up to the current setting. MUST be strictly coherent with the character mode ({matrix.get('mode_label', matrix.get('mode', 'Fantasy'))}), role/job ({matrix['job']}), and opening location ({matrix['location']}). Concrete and specific rather than generic.",
  "sex_preference": "A detailed, character-specific sexual preferences profile. Include her sexual orientation and preferred genders; preferred partners and relationship styles; sexual desires, turn-ons, kinks, roles, and favored dynamics; whether she is shy, teasing, direct, dominant, submissive, switch, romantic, casual, or slow-burn; and how these preferences appear naturally in her dialogue and behavior. Make the profile distinctive and consistent with her personality rather than a generic list. Example result styles: 'Bisexual and drawn to confident partners of any gender; a playful switch who enjoys teasing, praise, roleplay, and slow anticipation, but only becomes openly passionate after emotional trust forms.'; 'Lesbian and strongly monogamous; naturally dominant, protective, and direct, with preferences for consensual power exchange, obedience, affectionate possessiveness, and generous aftercare.'; 'Heterosexual and romance-oriented; shy about initiating, submissive once secure, and especially attracted to patience, verbal reassurance, gentle restraint, and a partner who takes the lead.' Use these only as quality and specificity references; create an original combination for every character. If the character is under 13, omit sexual material and provide only age-appropriate romantic preferences.",
  "intimacy_behavior": {{
    "orientation": "Specific sexual orientation and attraction pattern",
    "courtship_style": "Observable way she flirts, tests interest, and builds trust",
    "initiative_rules": "Concrete conditions under which she initiates, waits, slows down, or stops",
    "preferred_dynamic": "Her preferred power/relationship dynamic and how it changes with trust",
    "attraction_signals": "Three distinctive verbal or physical signals she shows when genuinely interested",
    "turn_ons": "Character-specific emotional and situational triggers, not a generic kink list",
    "turn_offs": "Behaviors that immediately reduce interest",
    "consent_style": "How she asks, gives, checks, withdraws, and confirms consent",
    "hard_limits": "Clear non-negotiable limits",
    "pacing": "How affection level and trust alter her behavior from reserved to intimate",
    "aftercare": "What she naturally does and needs after intimacy",
    "dialogue_behavior": "How all of the above changes her word choice, tone, teasing, requests, and refusals"
  }},
  "likes_dislikes": "Favorite foods, habits, creatures, environments | Dislikes, pet peeves, taboos, fears",
  "communication_style": "Vocal cadence, tone of voice, linguistic quirks, pet names or honorifics used, intimacy progression in speech",
  "scenario": "Introductory scenario set at {matrix['location']} framing the initial meeting with {{{{user}}}}"
}}
Output strictly valid raw JSON."""

    messages = [
        {"role": "system", "content": "You are a master character designer. You output strictly valid, complete JSON without markdown wrappers. All content must be written in 100% English."},
        {"role": "user", "content": prompt}
    ]

    raw_response = query_llm_func(messages, temperature=0.85, max_tokens_override=1600)
    
    # Clean JSON
    cleaned = raw_response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    behavior_seed = matrix.get("behavior_seed") or _behavioral_seed()
    identity_seed = matrix.get("identity_seed") or _identity_seed(str(matrix.get("mode") or "fantasy"))
    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("Character card response must be a JSON object")
    except Exception as e:
        # Fallback if json parse fails (100% English)
        contemporary = str(matrix.get("mode") or "").lower() in ("normal", "highschool")
        data = {
            "name": identity_seed["name"],
            "age": f"{matrix.get('age', 13)} years old",
            "personality": identity_seed["personality_anchor"],
            "appearance": f"A {matrix['race']} girl with {matrix['hair']}, {matrix['eyes']}, and {matrix['body']}; {identity_seed['appearance_anchor']}." if contemporary else f"A {matrix['race']} woman with {matrix['hair']}, {matrix['eyes']}, and {matrix['body']}; {identity_seed['appearance_anchor']}.",
            "status_role_goals": f"Works as {matrix['job']} and is determined to define her future on her own terms.",
            "baseline_relationship": "A new acquaintance whose circumstances have created an unexpectedly personal first conversation." if contemporary else "A trusted traveling companion and ally met during an uncertain journey.",
            "background": f"She {identity_seed['background_hook']}. That choice led her to {matrix['location']} through her work as {matrix['job']}." if contemporary else f"She {identity_seed['background_hook']}. That choice led her to {matrix['location']} in her life as {matrix['job']}.",
            "sex_preference": _behavior_profile_text(behavior_seed, matrix.get("age")),
            "intimacy_behavior": behavior_seed,
            "likes_dislikes": "Likes: Starry night skies, herbal tea, campfire solitude | Dislikes: Deceit, arrogance, filthy daggers",
            "communication_style": "Calm, articulate, and steady, occasionally softening into gentle undertones when trust deepens.",
        }

    # A partial LLM response must never collapse generated characters into the
    # same default. Fill missing behavioral keys from the per-character seed.
    generated_behavior = data.get("intimacy_behavior")
    if not isinstance(generated_behavior, dict):
        generated_behavior = {}
    data["intimacy_behavior"] = {
        key: str(generated_behavior.get(key) or value)
        for key, value in behavior_seed.items()
    }
    if not str(data.get("sex_preference") or "").strip():
        data["sex_preference"] = _behavior_profile_text(data["intimacy_behavior"], matrix.get("age"))
    # The sampled age is authoritative so the LLM cannot drift outside the
    # range or return the same default age for every character.
    data["age"] = f"{matrix.get('age', 13)} years old"
    # Identity anchors are authoritative to prevent malformed or generic LLM
    # results from losing name and character-defining details.
    data["name"] = identity_seed["name"]
    if not str(data.get("personality") or "").strip():
        data["personality"] = identity_seed["personality_anchor"]
    if not str(data.get("appearance") or "").strip():
        desc_subject = "girl" if str(matrix.get("mode") or "").lower() in ("normal", "highschool") else "woman"
        data["appearance"] = f"{matrix['race']} {desc_subject}; {identity_seed['appearance_anchor']}."
    if not str(data.get("background") or "").strip():
        data["background"] = identity_seed["background_hook"]

    data["outfits"] = matrix["outfits"]
    data["image_appearance"] = matrix.get("image_appearance") or matrix["avatar_prompt"]
    data["avatar_prompt"] = matrix["avatar_prompt"]
    data["gender"] = matrix["gender"]
    data["location"] = matrix["location"]
    data["mode"] = matrix.get("mode", "fantasy")
    # Random cards deliberately start without a canned opener. A future
    # character-aware opening system can fill this after it understands the
    # generated occupation, setting, and relationship premise.
    data["first_mes"] = ""
    return data


def save_character_to_realmplay(char_data: Dict[str, Any], user: str = "default_user") -> Dict[str, Any]:
    """Writes all baseline files and initializes the character in RealmPlay characters directory."""
    safe_name = normalize_character_name(char_data.get("name"), default_name=char_data.get("name"))
    # Avoid silently merging a new random character into an existing card.
    for _ in range(24):
        if not os.path.exists(os.path.join("characters", safe_name)):
            break
        safe_name = _generated_name()
    else:
        raise RuntimeError("Could not allocate a unique generated character name")
    raw_name = safe_name

    char_dir = os.path.join("characters", safe_name)
    os.makedirs(char_dir, exist_ok=True)
    os.makedirs(os.path.join(char_dir, "sprites"), exist_ok=True)

    # Distinguish Narrative Appearance (Character Card / รูปลักษณ์) and Visual Image Appearance (SD Prompt)
    card_appearance = char_data.get("appearance", "")
    image_appearance = char_data.get("image_appearance") or char_data.get("avatar_prompt", "")

    # 1. persona.md (Character Card Baseline - includes Narrative Appearance)
    persona_content = f"""# {raw_name}
**Gender**: {char_data.get('gender', 'Female')}
**Social Status, Role & Life Goals**: {char_data.get('status_role_goals', '')}
**Baseline Relationship**: {char_data.get('baseline_relationship', '')}

## Appearance
{card_appearance}

## Background
{char_data.get('background', '')}
"""
    with open(os.path.join(char_dir, "persona.md"), "w", encoding="utf-8") as f:
        f.write(persona_content.strip() + "\n")

    # 2. personality.md
    personality_content = f"""# Personality & Traits
{char_data.get('personality', '')}

## Communication Style
{char_data.get('communication_style', '')}

## Likes & Dislikes
{char_data.get('likes_dislikes', '')}

## Sexual Preferences
{char_data.get('sex_preference') or char_data.get('sex_preference_kinks', '')}
"""
    with open(os.path.join(char_dir, "personality.md"), "w", encoding="utf-8") as f:
        f.write(personality_content.strip() + "\n")

    # Structured behavioral contract used by the live roleplay prompt. Keeping
    # this separate prevents it from being clipped out of the character summary.
    behavior = char_data.get("intimacy_behavior") or {}
    if not isinstance(behavior, dict):
        behavior = {"profile": str(behavior)}
    behavior_lines = ["# Character-Specific Intimacy Behavior"]
    for key, value in behavior.items():
        clean_key = str(key).replace("_", " ").strip().title()
        clean_value = str(value or "").strip()
        if clean_value:
            behavior_lines.append(f"- {clean_key}: {clean_value}")
    if len(behavior_lines) == 1:
        behavior_lines.append(f"- Profile: {char_data.get('sex_preference') or char_data.get('sex_preference_kinks', '')}")
    with open(os.path.join(char_dir, "intimacy_behavior.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(behavior_lines).strip() + "\n")

    # 3. default_scenario.md
    scenario_content = char_data.get("scenario", f"You and she meet at {char_data.get('location', 'the ancient grounds')}.")
    with open(os.path.join(char_dir, "default_scenario.md"), "w", encoding="utf-8") as f:
        f.write(scenario_content.strip() + "\n")

    # 4. first_mes.txt
    first_mes = char_data.get("first_mes", '*Looks directly into your eyes with cautious curiosity.* "Who travels these parts...?"')
    with open(os.path.join(char_dir, "first_mes.txt"), "w", encoding="utf-8") as f:
        f.write(first_mes.strip() + "\n")

    # 5. Char_Summary.md (Matching RealmPlay SUMMARY_FIELDS exactly - Card Avatar / รูปลักษณ์)
    def _format_summary_field(val: Any, default: str = "") -> str:
        if val is None:
            return default
        if isinstance(val, (list, tuple)):
            return ", ".join(str(item).strip() for item in val if item is not None)
        if isinstance(val, dict):
            return ", ".join(f"{k}: {v}" for k, v in val.items() if v is not None)
        return str(val)

    summary_lines = [
        "# Character Summary",
        f"Name: {raw_name}",
        "",
        "## Gender",
        _format_summary_field(char_data.get("gender"), "Female"),
        "",
        "## Age",
        _format_summary_field(char_data.get("age"), "24 years old"),
        "",
        "## Personality",
        _format_summary_field(char_data.get("personality")),
        "",
        "## Status",
        _format_summary_field(char_data.get("status"), "Single"),
        "",
        "## Background",
        _format_summary_field(char_data.get("background")),
        "",
        "## Role & Life Goals",
        _format_summary_field(char_data.get("role_goals") or char_data.get("status_role_goals")),
        "",
        "## Sex Preference, Sex Desires & Nos",
        _format_summary_field(char_data.get("sex_preference") or char_data.get("sex_preference_kinks")),
        "",
        "## Like, Dislike, Favorite, Hate",
        _format_summary_field(char_data.get("likes_dislikes")),
        "",
        "## Communication Style",
        _format_summary_field(char_data.get("communication_style")),
        ""
    ]
    with open(os.path.join(char_dir, "Char_Summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines).strip() + "\n")

    # 5.1 Save Canonical Card JSON with avatar slot containing image appearance
    mode_str = str(char_data.get("mode") or "fantasy").lower()
    card_json_data = {
        "name": raw_name,
        "description": persona_content.strip(),
        "personality": char_data.get("personality", ""),
        "scenario": scenario_content.strip(),
        "first_mes": first_mes.strip(),
        "mes_example": "",
        "creatorcomment": "",
        "avatar": image_appearance.strip(),
        "talkativeness": 0.5,
        "fav": False,
        "tags": [mode_str.title(), "Random"],
        "alternate_greetings": [],
        "character_version": "1.0",
        "creator": "RealmPlay Generator",
        "creator_notes": "Randomly generated in RealmPlay",
        "extensions": {},
        "post_history_instructions": "",
        "system_prompt": ""
    }
    with open(os.path.join(char_dir, "card.json"), "w", encoding="utf-8") as f:
        json.dump(card_json_data, f, ensure_ascii=False, indent=2)

    # 6. Save the compact SD identity and the full avatar composition separately.
    with open(os.path.join(char_dir, "image_appearance.txt"), "w", encoding="utf-8") as f:
        f.write(image_appearance.strip() + "\n")
    with open(os.path.join(char_dir, "avatar_prompt.txt"), "w", encoding="utf-8") as f:
        f.write(char_data.get("avatar_prompt", "").strip() + "\n")

    # 7. Initialize character state:
    # - "appearance" is used specifically by Image Appearance (users/{user}/{name}/appearance.md)
    #   and fed into ComfyUI / SD prompts via image_context["appearance"].
    # - "avatar_prompt" holds the full resolved SD prompt.
    import character_card
    initial_state = {
        "status": f"[Posture & Activity]\n- Posture: Standing attentively\n- Location: {char_data.get('location', 'Starting area')}\n\n[Vital Needs & Biorhythm]\n- Energy: High\n- Hunger: Normal\n- Arousal: None\n\n[Relational & Emotional State]\n- Relationship: Initial meeting\n- Affection: 10 / 100\n- Body Language: Calm and observant",
        "scenario": scenario_content,
        "appearance": image_appearance,
        "outfits": char_data.get("outfits", {}),
        "inventory_wardrobe": [
            {
                "slot": k,
                "name": str(v.get("name") or v.get("prompt") or "").strip(),
                "prompt": v["prompt"],
                "status": "equipped",
            }
            for k, v in char_data.get("outfits", {}).items()
            if isinstance(v, dict) and v.get("prompt")
        ],
        "avatar_prompt": char_data.get("avatar_prompt", "")
    }
    character_card.save_user_character_state(user, safe_name, initial_state)

    return {
        "ok": True,
        "character_name": safe_name,
        "display_name": raw_name,
        "char_dir": char_dir,
        "data": char_data
    }

