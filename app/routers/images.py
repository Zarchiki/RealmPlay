"""Image-generation API boundary."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.system import GenerateImageRequest


def build_router(current_user: Callable, generate: Callable):
    router = APIRouter()

    @router.post("/api/image/generate")
    async def generate_image(req: GenerateImageRequest, user: str = Depends(current_user)):
        return await generate(req, user)

    return router
