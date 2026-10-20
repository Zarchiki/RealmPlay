"""Random Character Card Generator for RealmPlay.
Combines Stable Diffusion Wildcards Matrix with LLM synthesis to create
complete, multi-dimensional RPG character cards (especially female personas).
"""
import os
import random
import json
import re
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WILDCARDS_DIR = os.path.join(BASE_DIR, "data", "wildcards")
CATALOG_PATH = os.path.join(BASE_DIR, "data", "wardrobe_catalog.json")



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
    "bust_size": ["medium breasts", "large breasts", "perky breasts", "ample breasts"]
}


def _read_wildcard_lines(tag_name: str) -> list:
    """Read non-empty lines from a wildcard file with recursive fallback and alias search."""
    tag_clean = tag_name.strip().replace("\\", "/")
    if tag_clean.endswith(".txt"):
        tag_clean = tag_clean[:-4]

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


def sample_rpg_female_wildcard_matrix() -> Dict[str, Any]:
    """Sample an RPG female character prompt matrix from wildcards."""
    # 1. Races & Archetypes
    races = _read_wildcard_lines("race.txt") or [
        "elf, long pointed ears", "human", "half-elf, slightly pointed ears",
        "tiefling, curved horns, pointed tail", "kitsune, fox ears and bushy tail"
    ]
    raw_race = random.choice(races)
    resolved_race = _resolve_template_tags(raw_race)

    jobs = _read_wildcard_lines("job_adventurer.txt") or [
        "ranger, moss-green cloak, quiver on back",
        "mage, embroidered robes, crystal staff",
        "knight, polished armor, silver sword",
        "rogue, leather armor, twin daggers",
        "cleric, holy robes, silver amulet"
    ]
    raw_job = _resolve_template_tags(random.choice(jobs))

    # 2. Physical Appearance
    haircuts = _read_wildcard_lines("haircut-female.txt") or ["long braided hair", "ponytail", "bob cut", "wavy twin tails", "flowing straight hair"]
    hair_colors = _read_wildcard_lines("hair_color.txt") or ["silver hair", "golden blonde hair", "raven black hair", "crimson red hair", "pastel pink hair"]
    eye_colors = _read_wildcard_lines("eye_color.txt") or ["amber eyes", "sapphire blue eyes", "crimson red eyes", "emerald green eyes", "violet eyes"]
    bust_sizes = _read_wildcard_lines("bust_size.txt") or ["medium breasts", "large breasts", "slender chest", "perky breasts"]
    body_types = _read_wildcard_lines("female body type.txt") or ["slender figure", "curvaceous hourglass body", "athletic toned physique", "petite frame"]

    raw_hair = f"{random.choice(haircuts)}, {random.choice(hair_colors)}"
    raw_eyes = random.choice(eye_colors)
    raw_body = f"{random.choice(body_types)}, {random.choice(bust_sizes)}"

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

    outer_item = random.choice(catalog_items.get("outer", [])) if catalog_items.get("outer") else {"prompt": "leather traveler cloak"}
    top_item = random.choice(catalog_items.get("top", [])) if catalog_items.get("top") else {"prompt": "fitted linen tunic"}
    bottom_item = random.choice(catalog_items.get("bottom", [])) if catalog_items.get("bottom") else {"prompt": "leather travel pants"}
    shoes_item = random.choice(catalog_items.get("shoes", [])) if catalog_items.get("shoes") else {"prompt": "leather adventuring boots"}
    top_inner_item = random.choice(catalog_items.get("top_inner", [])) if catalog_items.get("top_inner") else {"prompt": "silk bralette"}
    bottom_inner_item = random.choice(catalog_items.get("bottom_inner", [])) if catalog_items.get("bottom_inner") else {"prompt": "matching panties"}

    outfits = {
        "outer": {"prompt": outer_item["prompt"], "active": True},
        "top": {"prompt": top_item["prompt"], "active": True},
        "bottom": {"prompt": bottom_item["prompt"], "active": True},
        "shoes": {"prompt": shoes_item["prompt"], "active": True},
        "top_inner": {"prompt": top_inner_item["prompt"], "active": True},
        "bottom_inner": {"prompt": bottom_inner_item["prompt"], "active": True}
    }

    # 4. Location & Environment
    locations = _read_wildcard_lines("location+theme.txt") or _read_wildcard_lines("where.txt") or [
        "ancient overgrown ruin cathedral courtyard", "mystical luminous glowing forest", "bustling fantasy tavern corner",
        "dungeon cavern lit by crystals", "moonlit castle balcony overlooking kingdom"
    ]
    resolved_location = _resolve_template_tags(random.choice(locations))

    # 5. Scene & Composition
    compositions = _read_wildcard_lines("composition.txt") or ["cowboy shot, looking at viewer", "three-quarter view, dramatic angle", "portrait shot, soft depth of field"]
    resolved_composition = _resolve_template_tags(random.choice(compositions))

    visual_quality = _read_wildcard_lines("visual_quality.txt")
    quality_str = visual_quality[0] if visual_quality else "masterpiece, high quality, highly detailed, sharp focus"

    # Assemble complete SD Image Prompt and clean all wildcards thoroughly
    avatar_prompt = _clean_unresolved_wildcards(
        f"1girl, solo, {resolved_race}, {raw_job}, {hair_chosen}, {eyes_chosen}, {body_chosen}, "
        f"wearing {outer_item['prompt']}, {top_item['prompt']}, {bottom_item['prompt']}, {shoes_item['prompt']}, "
        f"in {resolved_location}, {resolved_composition}, {quality_str}"
    )

    # Visual appearance prompt specifically for ComfyUI / SD (character features: race, hair, eyes, body)
    image_appearance = _clean_unresolved_wildcards(
        f"1girl, solo, {resolved_race}, {raw_job}, {hair_chosen}, {eyes_chosen}, {body_chosen}"
    )

    return {
        "gender": "Female",
        "race": _clean_unresolved_wildcards(resolved_race),
        "job": _clean_unresolved_wildcards(raw_job),
        "hair": _clean_unresolved_wildcards(hair_chosen),
        "eyes": _clean_unresolved_wildcards(eyes_chosen),
        "body": _clean_unresolved_wildcards(body_chosen),
        "image_appearance": image_appearance,
        "location": _clean_unresolved_wildcards(resolved_location),
        "outfits": outfits,
        "avatar_prompt": avatar_prompt
    }


def synthesize_complete_character_card(matrix: Dict[str, Any], query_llm_func) -> Dict[str, Any]:
    """Uses LLM to synthesize a full multi-dimensional RealmPlay character card based on wildcards matrix in 100% English."""
    prompt = f"""You are a master Character Designer for RealmPlay (RPG Fantasy & Adult NSFW H-Mode).
Create a rich, multi-dimensional female character card based on the sampled wildcards matrix below.
IMPORTANT: You MUST write EVERYTHING strictly in 100% ENGLISH. Do not use any Thai or other non-English language.

[Wildcards Matrix]
- Gender: {matrix['gender']}
- Race / Heritage: {matrix['race']}
- Class / Profession / Role: {matrix['job']}
- Physical Attributes: {matrix['hair']}, Eyes: {matrix['eyes']}, Physique: {matrix['body']}
- Starting Attire: {matrix['outfits']['outer']['prompt']}, {matrix['outfits']['top']['prompt']}, {matrix['outfits']['bottom']['prompt']}
- Opening Location: {matrix['location']}

Respond with a strictly valid JSON object (and ONLY JSON, no conversational markdown or preamble) with the following fields:
{{
  "name": "Only character full name with given name and optional surname separated by a space (e.g. 'Jennifer Lopez' or 'Aeloria Silverwhisper'), strictly NO titles, epithets, honorifics, or commas (e.g. do NOT write 'the Wandering Arcanist')",
  "personality": "Detailed personality traits, core values, psychological strengths, vulnerabilities, behavioral quirks, and mannerisms",
  "appearance": "Rich narrative physical description: face, expressions, hair color and style, eyes, body proportions, posture, skin texture, and aesthetic details",
  "status_role_goals": "Social standing, vocation, affiliations, and compelling personal ambitions or quests",
  "baseline_relationship": "Initial dynamic with {{{{user}}}} (e.g. adventuring companion bound by contract, survivor rescued from ruins, rival turned reluctant ally)",
  "background": "In-depth backstory, formative life events, training, and past history leading up to the current setting",
  "sex_preference_kinks": "Intimate preferences, sensual desires, erogenous zones, turn-ons, kinks, pacing, and boundaries for H-Mode (e.g. passionate, submissive/dominant inclinations, physical sensitivity)",
  "likes_dislikes": "Favorite foods, habits, creatures, environments | Dislikes, pet peeves, taboos, fears",
  "communication_style": "Vocal cadence, tone of voice, linguistic quirks, pet names or honorifics used, intimacy progression in speech",
  "scenario": "Introductory scenario set at {matrix['location']} framing the initial meeting with {{{{user}}}}",
  "first_mes": "Opening introductory roleplay message containing vivid sensory narration in *asterisks* and natural spoken dialogue in \\"quotes\\""
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

    try:
        data = json.loads(cleaned)
    except Exception as e:
        # Fallback if json parse fails (100% English)
        data = {
            "name": "Lyra Moonshadow",
            "personality": "Fiercely independent and determined, cloaking a tender and loyal heart beneath a sharp, guarded exterior.",
            "appearance": f"A striking {matrix['race']} maiden with {matrix['hair']}, captivating {matrix['eyes']}, and an alluring {matrix['body']}.",
            "status_role_goals": f"An adventurous {matrix['job']} striving to unravel ancient forgotten relics and forge a legendary legacy.",
            "baseline_relationship": "A trusted traveling companion and ally met upon the treacherous frontier roads.",
            "background": f"Raised in the frontier wilds, she honed her martial and survival instincts before venturing toward {matrix['location']}.",
            "sex_preference_kinks": "Intensely responsive to gentle caresses along her neck and sensitive collarbone; desires passionate closeness and intense mutual eye contact.",
            "likes_dislikes": "Likes: Starry night skies, herbal tea, campfire solitude | Dislikes: Deceit, arrogance, filthy daggers",
            "communication_style": "Calm, articulate, and steady, occasionally softening into gentle undertones when trust deepens.",
            "first_mes": f'*Turns slightly toward {{{{user}}}}, pulling her cloak tighter against the mountain draft with a thoughtful gaze.* "We have finally arrived... Are you ready to step inside with me?"'
        }

    data["outfits"] = matrix["outfits"]
    data["image_appearance"] = matrix.get("image_appearance") or matrix["avatar_prompt"]
    data["avatar_prompt"] = matrix["avatar_prompt"]
    data["gender"] = matrix["gender"]
    data["location"] = matrix["location"]
    return data


def save_character_to_realmplay(char_data: Dict[str, Any], user: str = "default_user") -> Dict[str, Any]:
    """Writes all baseline files and initializes the character in RealmPlay characters directory."""
    raw_name = char_data.get("name", "Unnamed Adventurer")
    # Clean name: remove parentheses and titles/epithets after commas or dashes
    cleaned_name = re.sub(r"\(.*?\)", "", raw_name)
    cleaned_name = re.split(r"[,;]|\b(?:the|of)\b", cleaned_name, flags=re.IGNORECASE)[0].strip()
    # Normalize multiple whitespace to single space, allow only word characters, spaces, and hyphens
    cleaned_name = re.sub(r"[^\w\s-]", "", cleaned_name)
    cleaned_name = re.sub(r"\s+", " ", cleaned_name).strip()
    safe_name = cleaned_name if cleaned_name else f"Adventurer_{random.randint(1000, 9999)}"
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

## Intimate Preferences & Boundaries (H-Mode)
{char_data.get('sex_preference_kinks', '')}
"""
    with open(os.path.join(char_dir, "personality.md"), "w", encoding="utf-8") as f:
        f.write(personality_content.strip() + "\n")

    # 3. default_scenario.md
    scenario_content = char_data.get("scenario", f"You and she meet at {char_data.get('location', 'the ancient grounds')}.")
    with open(os.path.join(char_dir, "default_scenario.md"), "w", encoding="utf-8") as f:
        f.write(scenario_content.strip() + "\n")

    # 4. first_mes.txt
    first_mes = char_data.get("first_mes", '*Looks directly into your eyes with cautious curiosity.* "Who travels these parts...?"')
    with open(os.path.join(char_dir, "first_mes.txt"), "w", encoding="utf-8") as f:
        f.write(first_mes.strip() + "\n")

    # 5. Char_Summary.md (Matching RealmPlay SUMMARY_FIELDS exactly - Card Avatar / รูปลักษณ์)
    summary_lines = [
        "# Character Summary",
        f"Name: {raw_name}",
        "",
        "## Personality",
        char_data.get("personality", ""),
        "",
        "## Gender",
        char_data.get("gender", "Female"),
        "",
        "## Appearance",
        card_appearance,
        "",
        "## Social Status, Role & Life Goals",
        char_data.get("status_role_goals", ""),
        "",
        "## Baseline Relationship",
        char_data.get("baseline_relationship", ""),
        "",
        "## Background",
        char_data.get("background", ""),
        "",
        "## Sex Preference, Sex Desires & Nos",
        char_data.get("sex_preference_kinks", ""),
        "",
        "## Like, Dislike, Favorite, Hate",
        char_data.get("likes_dislikes", ""),
        "",
        "## Communication Style",
        char_data.get("communication_style", ""),
        ""
    ]
    with open(os.path.join(char_dir, "Char_Summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines).strip() + "\n")

    # 6. Save avatar prompt for SD generation
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
            {"slot": k, "prompt": v["prompt"], "status": "equipped"}
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

