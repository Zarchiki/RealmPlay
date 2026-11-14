"""HTTP routes for voice generation and RVC cache management."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.system import SaveVoiceParamsRequest, TTSRequest


def build_router(current_user: Callable, voices: Callable, speak: Callable, cache_status: Callable, clear_cache: Callable, save_params: Callable):
    router = APIRouter()

    @router.get("/api/voice/voices")
    def voices_endpoint(user: str = Depends(current_user)):
        return voices(user)

    @router.post("/api/voice/speak")
    async def speak_endpoint(req: TTSRequest, user: str = Depends(current_user)):
        return await speak(req, user)

    @router.get("/api/voice/cache")
    def cache_status_endpoint(user: str = Depends(current_user)):
        return cache_status(user)

    @router.delete("/api/voice/cache")
    def clear_cache_endpoint(user: str = Depends(current_user)):
        return clear_cache(user)

    @router.post("/api/voice/params/save")
    def save_params_endpoint(req: SaveVoiceParamsRequest, user: str = Depends(current_user)):
        return save_params(req, user)

    return router
