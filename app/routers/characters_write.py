"""Focused character-card mutation endpoints."""

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.character import CreateCharacterRequest, UpdateCharacterCardRequest
from app.services import character_write


def build_router(character_card, scene_state, current_user: Callable, safe_name: Callable):
    router = APIRouter()

    @router.post("/api/characters/{char_name}/card")
    def update_card(char_name: str, req: UpdateCharacterCardRequest, user: str = Depends(current_user)):
        return character_write.update_card(char_name, req, character_card, safe_name)

    @router.post("/api/characters/create")
    def create_character(req: CreateCharacterRequest, user: str = Depends(current_user)):
        return character_write.create(req, character_card)

    @router.post("/api/characters/{char_name}/scene/pacing")
    def update_scene_pacing(char_name: str, payload: dict, user: str = Depends(current_user)):
        return character_write.pace_scene(char_name, payload, user, character_card, scene_state, safe_name)

    @router.delete("/api/characters/{char_name}/avatar")
    def delete_avatar(char_name: str, user: str = Depends(current_user)):
        return character_write.delete_avatar(char_name, safe_name)

    return router
