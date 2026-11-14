"""Context-inspection and local-model discovery endpoints."""

from typing import Callable

from fastapi import APIRouter, Depends


def build_router(current_user: Callable, context_usage: Callable, models: Callable):
    router = APIRouter()

    @router.get("/api/chat/context_usage")
    async def context_usage_endpoint(character_name: str, user: str = Depends(current_user)):
        return await context_usage(character_name, user)

    @router.get("/api/models/list")
    def models_endpoint(user: str = Depends(current_user)):
        return models(user)

    return router
