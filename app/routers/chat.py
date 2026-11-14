"""HTTP boundary for primary chat generation flows."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.chat import ChatMessageRequest, ContinueRequest, RegenerateRequest


def build_router(current_user: Callable, send: Callable, regenerate: Callable, continue_chat: Callable):
    router = APIRouter()

    @router.post("/api/chat/send")
    async def send_endpoint(req: ChatMessageRequest, user: str = Depends(current_user)):
        return await send(req, user)

    @router.post("/api/chat/regenerate")
    async def regenerate_endpoint(req: RegenerateRequest, user: str = Depends(current_user)):
        return await regenerate(req, user)

    @router.post("/api/chat/continue")
    async def continue_endpoint(req: ContinueRequest, user: str = Depends(current_user)):
        return await continue_chat(req, user)

    return router
