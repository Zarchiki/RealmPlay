"""HTTP routes for editing and removing chat history."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.chat import DeleteMessageRequest, DeleteMessagesRequest, EditMessageRequest


def build_router(current_user: Callable, delete_many: Callable, edit: Callable, delete_one: Callable):
    router = APIRouter()

    @router.post("/api/chat/delete_messages")
    async def delete_many_endpoint(req: DeleteMessagesRequest, user: str = Depends(current_user)):
        return await delete_many(req, user)

    @router.post("/api/chat/edit_message")
    @router.post("/api/chat/edit")
    async def edit_endpoint(req: EditMessageRequest, user: str = Depends(current_user)):
        return await edit(req, user)

    @router.post("/api/chat/delete_message")
    async def delete_one_endpoint(req: DeleteMessageRequest, user: str = Depends(current_user)):
        return await delete_one(req, user)

    return router
