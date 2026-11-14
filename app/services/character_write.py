"""Character-card creation and baseline updates."""

import base64
import json
import os

from fastapi import HTTPException


def update_card(char_name: str, request, character_card, safe_name) -> dict:
    character = safe_name(char_name)
    if not character_card.update_character_baseline(character, {
        "persona": request.persona, "personality": request.personality,
        "scenario": request.scenario, "first_mes": request.first_mes,
    }):
        raise HTTPException(status_code=404, detail="Character not found")
    return {"ok": True, "baseline": character_card.get_character_baseline(character)}


def create(request, character_card) -> dict:
    avatar = None
    if request.avatar_base64:
        try:
            avatar = base64.b64decode(request.avatar_base64.split(",", 1)[-1])
        except Exception as error:
            print(f"[CreateChar] Avatar decode warning: {error}")
    try:
        return character_card.create_character(
            name=request.name, persona=request.persona or "", personality=request.personality or "",
            scenario=request.scenario or "", first_mes=request.first_mes or "", avatar_bytes=avatar,
            gender=request.gender or "Female", age=request.age or "", status=request.status or "Single",
            role_goals=request.role_goals or "", sex_preference=request.sex_preference or "",
            likes_dislikes=request.likes_dislikes or "", communication_style=request.communication_style or "",
            char_summary=request.char_summary or "",
            outfits=character_card.build_imported_wardrobe("") if not getattr(request, "outfit_overrides", None) else {
                **character_card.default_character_outfits(),
                **{
                    k: {"active": True, "prompt": v if isinstance(v, str) else v.get("prompt", str(v))}
                    for k, v in (request.outfit_overrides or {}).items() if v
                }
            },
        )
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


def delete_avatar(char_name: str, safe_name) -> dict:
    character = safe_name(char_name)
    directory = os.path.join("characters", character)
    if not os.path.isdir(directory):
        raise HTTPException(status_code=404, detail="Character not found")
    try:
        avatar = os.path.join(directory, "avatar.png")
        if os.path.isfile(avatar):
            os.remove(avatar)
        card = os.path.join(directory, "card.json")
        if os.path.isfile(card):
            data = json.loads(open(card, encoding="utf-8").read())
            data = data.get("data", data)
            if isinstance(data, dict):
                data["avatar"] = "none"
                with open(card, "w", encoding="utf-8") as file:
                    json.dump(data, file, ensure_ascii=False, indent=2)
        return {"ok": True}
    except OSError as error:
        raise HTTPException(status_code=500, detail=f"Cannot delete Character Card image: {error}")


def pace_scene(char_name: str, payload: dict, user: str, character_card, scene_state, safe_name) -> dict:
    action = str((payload or {}).get("action", "")).strip().lower()
    if action not in {"advance", "ease", "aftercare", "end_scene"}:
        raise HTTPException(status_code=400, detail="Unknown pacing action")
    character = safe_name(char_name)
    state = character_card.get_user_character_state(user, character)
    updated = scene_state.pace(state.get("scene_state"), action)
    character_card.save_user_character_state(user, character, {"scene_state": updated})
    return {"ok": True, "scene_state": updated, "rejected": bool(updated.get("rejected", False))}
