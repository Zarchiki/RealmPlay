"""Resolve durable wardrobe state into image/prompt tags."""
import re

# These values describe UI/history selection only; they are never garments.
_OUTFIT_METADATA_KEYS = {"current_outfit", "outfits", "current_preset"}

KNOWN_COLORS = {
    'red', 'blue', 'green', 'yellow', 'black', 'white', 'purple', 'pink',
    'navy', 'grey', 'gray', 'brown', 'orange', 'beige', 'teal', 'maroon',
    'crimson', 'silver', 'gold', 'violet', 'indigo', 'lavender', 'cyan'
}

KNOWN_PATTERNS = {
    'plaid', 'striped', 'checkered', 'polka dot', 'floral', 'argyle',
    'houndstooth', 'camo', 'camouflage', 'ribbed', 'tartan', 'gingham',
    'lace', 'sheer', 'leather', 'denim', 'silk', 'cotton'
}


def compose_slot_prompt(item: dict) -> str:
    """Compose full slot prompt by adding color and pattern sub-data as prefix."""
    prompt = str(item.get("prompt") or "").strip()
    if not prompt or prompt.lower() in ("naked", "none"):
        return prompt

    color = item.get("color")
    pattern = item.get("pattern")
    if not color and not pattern:
        return prompt

    clean = prompt
    words_to_strip = []
    if color:
        words_to_strip.extend(KNOWN_COLORS)
    if pattern:
        words_to_strip.extend(KNOWN_PATTERNS)

    if words_to_strip:
        rx = r'\b(?:' + '|'.join(re.escape(w) for w in words_to_strip) + r')\b'
        clean = re.sub(rx, '', clean, flags=re.I)
        clean = re.sub(r'\s+', ' ', clean).strip(' ,')

    clean = re.sub(r'^(?:a|an|the)\s+', '', clean, flags=re.I).strip()

    prefixes = []
    if color:
        prefixes.append(str(color).strip())
    if pattern:
        prefixes.append(str(pattern).strip())

    pref_str = ' '.join(prefixes)
    return f"{pref_str} {clean}".strip()


# Slots that should be placed at the very end of resolved prompts
_INNER_SLOT_KEYS = ("top_inner", "bra", "bottom_inner", "panties")


def resolve(outfits: dict, clothing_parts: tuple | list) -> str:
    if not isinstance(outfits, dict):
        return ""
    clothes_on = any(
        (isinstance(outfits.get(part), dict) and outfits[part].get("active") and outfits[part].get("prompt", "").strip())
        or isinstance(outfits.get(part), bool) and outfits[part]
        for part in clothing_parts
    )
    tags = [] if clothes_on else ["naked"]
    inner_tags = []

    for key, value in outfits.items():
        if key == "naked" and clothes_on:
            continue
        if isinstance(value, dict) and value.get("active") and value.get("prompt", "").strip():
            prompt = compose_slot_prompt(value)
        elif isinstance(value, str) and value.strip() and key not in _OUTFIT_METADATA_KEYS:
            prompt = value.strip()
        else:
            continue

        if key in _INNER_SLOT_KEYS:
            if prompt not in inner_tags:
                inner_tags.append(prompt)
        else:
            if prompt not in tags:
                tags.append(prompt)

    for prompt in inner_tags:
        if prompt not in tags:
            tags.append(prompt)

    return ", ".join(tags)


def attire_summary(outfits: dict) -> str:
    if not isinstance(outfits, dict) or not outfits:
        return "Standard attire"
    worn, removed = [], []
    for slot, item in outfits.items():
        if slot in {*_OUTFIT_METADATA_KEYS, "naked"}:
            continue
        prompt = compose_slot_prompt(item) if isinstance(item, dict) else slot
        active = item.get("active", False) if isinstance(item, dict) else bool(item)
        (worn if active else removed).append(f"{slot} ({prompt})" if active else slot)
    parts = ["Worn: " + ", ".join(worn) if worn else "Worn: None (Completely naked/bare)"]
    if removed:
        parts.append("Removed/Stripped/Exposed: " + ", ".join(removed))
    return " | ".join(parts)
