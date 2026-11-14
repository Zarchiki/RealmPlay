"""Character import, generation, and global administration routes."""

from typing import Callable

from fastapi import APIRouter, Depends, File, UploadFile

from app.schemas.character import RandomCharacterRequest


def build_router(current_user: Callable, delete_global: Callable, import_card: Callable, generate_random: Callable):
    router = APIRouter()

    @router.delete("/api/admin/characters/{char_name}")
    def delete_global_endpoint(char_name: str, user: str = Depends(current_user)):
        return delete_global(char_name, user)

    @router.post("/api/characters/import_png")
    async def import_endpoint(file: UploadFile = File(...), user: str = Depends(current_user)):
        return await import_card(file, user)

    @router.post("/api/characters/random-generate")
    async def random_endpoint(req: RandomCharacterRequest | None = None, user: str = Depends(current_user)):
        return await generate_random(req, user)

    return router
