"""HTTP routes for chat-attached image generation and management."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.chat import ContextImageRequest, DeleteImageRequest


def build_router(current_user: Callable, generate: Callable, stop: Callable, preview: Callable, delete: Callable):
    router = APIRouter()

    @router.post("/api/chat/generate_context_image")
    async def generate_endpoint(req: ContextImageRequest, user: str = Depends(current_user)):
        return await generate(req, user)

    @router.post("/api/image/stop")
    async def stop_endpoint(user: str = Depends(current_user)):
        return await stop(user)

    @router.post("/api/chat/image-intent-preview")
    async def preview_endpoint(req: ContextImageRequest, user: str = Depends(current_user)):
        return await preview(req, user)

    @router.post("/api/chat/delete_image")
    async def delete_endpoint(req: DeleteImageRequest, user: str = Depends(current_user)):
        return await delete(req, user)

    return router
