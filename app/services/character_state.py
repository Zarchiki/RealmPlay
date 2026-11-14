"""Per-user mutable character state rules."""

import re


def update(char_name: str, request, user: str, character_card, safe_name) -> dict:
    character = safe_name(char_name)
    updates = {}
    for field in ("scenario", "memory", "emotion", "emotion_detail", "time_state", "appearance", "character_profile", "inventory"):
        value = getattr(request, field)
        if value is not None:
            updates[field] = value
    if request.status is not None:
        updates["status"] = re.sub(r"(?im)^\s*mood\s*:\s*[^\r\n]*(?:\r?\n|$)", "", request.status).strip()
    if request.current_outfit is not None:
        state = character_card.get_user_character_state(user, character)
        outfits = state.get("outfits", {})
        outfits["current_outfit"] = request.current_outfit
        updates["outfits"] = outfits
    character_card.save_user_character_state(user, character, updates)
    return {"ok": True}
