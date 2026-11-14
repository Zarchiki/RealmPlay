"""Aggregate runtime-status endpoint."""

from typing import Callable

from fastapi import APIRouter, Depends


def build_router(current_user: Callable, status: Callable):
    router = APIRouter()

    @router.get("/api/status/all")
    def status_endpoint(user: str = Depends(current_user)):
        return status(user)

    return router
