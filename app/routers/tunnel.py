"""Cloudflare tunnel HTTP endpoints.

The process lifecycle remains in the legacy service during this migration; the
router boundary makes it possible to move that service independently.
"""

from typing import Callable

from fastapi import APIRouter, Depends


def build_router(current_user: Callable, status: Callable, start: Callable, stop: Callable):
    router = APIRouter()

    @router.get("/api/tunnel/status")
    def get_status(user: str = Depends(current_user)):
        return status()

    @router.post("/api/tunnel/start")
    def start_tunnel(user: str = Depends(current_user)):
        return start()

    @router.post("/api/tunnel/stop")
    def stop_tunnel(user: str = Depends(current_user)):
        return stop()

    return router
