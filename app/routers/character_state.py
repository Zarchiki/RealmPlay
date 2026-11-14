"""HTTP boundary for per-user character state changes."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.character import UpdateStateRequest
from app.schemas.chat import ChatReadRequest


def build_router(current_user: Callable, mark_read: Callable, update_state: Callable):
    router = APIRouter()

    @router.post("/api/characters/{char_name}/read")
    def read_endpoint(char_name: str, req: ChatReadRequest, user: str = Depends(current_user)):
        return mark_read(char_name, req, user)

    @router.post("/api/characters/{char_name}/state")
    def update_endpoint(char_name: str, req: UpdateStateRequest, user: str = Depends(current_user)):
        return update_state(char_name, req, user)

    return router
