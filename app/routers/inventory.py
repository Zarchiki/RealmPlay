"""HTTP boundary for character inventory mutations."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.character import InventoryActionRequest


def build_router(current_user: Callable, mutate: Callable, read: Callable):
    router = APIRouter()

    @router.post("/api/characters/{char_name}/inventory")
    def mutate_endpoint(char_name: str, req: InventoryActionRequest, user: str = Depends(current_user)):
        return mutate(char_name, req, user)

    @router.get("/api/characters/{char_name}/inventory")
    def read_endpoint(char_name: str, user: str = Depends(current_user)):
        return read(char_name, user)

    return router
