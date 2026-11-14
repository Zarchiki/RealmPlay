"""Read-only catalogs exposed to the user interface."""

import json
from typing import Callable

from fastapi import APIRouter, Depends


def build_router(comfy_client, current_user: Callable):
    router = APIRouter()

    @router.get("/api/emotions")
    def emotion_catalog(user: str = Depends(current_user)):
        try:
            with open("config.json", encoding="utf-8") as file:
                config = json.load(file)
        except (OSError, ValueError):
            config = {}
        comfy = config.get("comfy", {})
        custom = comfy.get("emotion_prompts", {})
        prompts = {**comfy_client.DEFAULT_EMOTION_PROMPTS, **(custom if isinstance(custom, dict) else {})}
        configured = comfy.get("emotion_categories", comfy_client.DEFAULT_EMOTION_CATEGORIES)
        categories = configured if isinstance(configured, dict) else comfy_client.DEFAULT_EMOTION_CATEGORIES
        category_for = {
            str(emotion): str(category) for category, emotions in categories.items()
            for emotion in (emotions if isinstance(emotions, (list, tuple)) else [])
        }
        return {"ok": True, "emotions": [
            {"id": key, "label": key.replace("_", " ").title(), "category": category_for.get(key, "general"), "prompt": value}
            for key, value in prompts.items()
        ]}

    return router
