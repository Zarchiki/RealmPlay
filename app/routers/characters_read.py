"""Read-only character and media endpoints."""

import json
import os
import re
import urllib.parse
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response

from app.services import gallery


def build_router(character_card, turn_metadata, current_user: Callable, safe_name: Callable, touch_proactive: Callable, scene_state=None):
    router = APIRouter()

    @router.get("/api/characters")
    def list_characters(user: str = Depends(current_user)):
        from chat_inbox import summary
        characters = []
        if os.path.exists("characters"):
            for name in os.listdir("characters"):
                if os.path.isdir(os.path.join("characters", name)):
                    characters.append({**character_card.get_character_baseline(name), **summary(user, name)})
        return sorted(characters, key=lambda character: character["last_message_at"], reverse=True)

    @router.get("/api/characters/{char_name}/gallery")
    def get_gallery(char_name: str, user: str = Depends(current_user)):
        safe_char = safe_name(char_name)
        char_dir = Path("characters") / safe_char
        if not char_dir.is_dir():
            raise HTTPException(status_code=404, detail="Character not found")
        state = character_card.get_user_character_state(user, safe_char)
        items = gallery.generated_images(state.get("history") or [])
        avatar = char_dir / "avatar.png"
        if avatar.is_file():
            items.insert(0, {"kind": "profile", "url": f"/api/characters/{urllib.parse.quote(safe_char, safe='')}/avatar?v={avatar.stat().st_mtime_ns}", "turn_id": ""})
        return {"items": items}

    @router.get("/api/characters/{char_name}/state")
    def get_state(char_name: str, user: str = Depends(current_user)):
        try:
            safe_char = safe_name(char_name)
            touch_proactive(user, safe_char)
            st = character_card.get_user_character_state(user, safe_char)
            if not st.get("scene_state"):
                history = st.get("history") or []
                for hist_msg in reversed(history):
                    if hist_msg.get("role") == "assistant":
                        snap_sc = ((hist_msg.get("metadata") or {}).get("snapshot") or {}).get("scene_state")
                        if isinstance(snap_sc, dict):
                            st["scene_state"] = snap_sc
                            break
                if not st.get("scene_state") and scene_state is not None:
                    st["scene_state"] = scene_state.normalize(None)
            return st
        except Exception as error:
            raise HTTPException(status_code=404, detail=str(error))

    @router.get("/api/characters/{char_name}/turn-media/{turn_id}")
    def get_turn_media(char_name: str, turn_id: str, user: str = Depends(current_user)):
        safe_char = safe_name(char_name)
        if not re.fullmatch(r"[a-f0-9]{32}", turn_id):
            raise HTTPException(status_code=404, detail="Media not found")
        path = turn_metadata.user_media_path(Path("users") / safe_name(user) / safe_char, turn_id)
        if not path:
            raise HTTPException(status_code=404, detail="Media not found")
        return FileResponse(path)

    @router.get("/api/characters/{char_name}/export")
    def export_png(char_name: str, user: str = Depends(current_user)):
        try:
            safe_char = safe_name(char_name)
            return Response(
                content=character_card.export_character_card_png(safe_char), media_type="image/png",
                headers={"Content-Disposition": f'attachment; filename="{safe_char}.png"'},
            )
        except Exception as error:
            raise HTTPException(status_code=400, detail=str(error))

    @router.get("/api/characters/{char_name}/avatar")
    def get_avatar(char_name: str):
        avatar_path = os.path.join("characters", safe_name(char_name), "avatar.png")
        if os.path.exists(avatar_path):
            return FileResponse(avatar_path, media_type="image/png")
        raise HTTPException(status_code=404, detail="Avatar not found")

    @router.get("/api/characters/{char_name}/sprites/{sprite_file}")
    def get_sprite(char_name: str, sprite_file: str):
        sprite_path = os.path.join("characters", safe_name(char_name), "sprites", safe_name(sprite_file))
        if os.path.exists(sprite_path):
            return FileResponse(sprite_path, media_type="image/png")
        raise HTTPException(status_code=404, detail="Sprite not found")

    @router.get("/api/characters/{char_name}/export-json")
    def export_json(char_name: str, user: str = Depends(current_user)):
        safe_char = safe_name(char_name)
        try:
            from realmplay_features import card_document
            return Response(
                content=json.dumps(card_document(safe_char, character_card), ensure_ascii=False, indent=2),
                media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{safe_char}.json"'},
            )
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=400, detail=str(error))

    return router
