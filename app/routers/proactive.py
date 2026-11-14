"""HTTP boundary for proactive-character scheduling."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.character import CharacterTimingRequest, ProactiveHeartbeatRequest, ProactiveTriggerRequest


def build_router(current_user: Callable, heartbeat: Callable, status: Callable, timings: Callable, set_timing: Callable, trigger: Callable):
    router = APIRouter()

    @router.post("/api/proactive/heartbeat")
    def heartbeat_endpoint(req: ProactiveHeartbeatRequest, user: str = Depends(current_user)):
        return heartbeat(req, user)

    @router.get("/api/proactive/status")
    def status_endpoint(character_name: str, user: str = Depends(current_user)):
        return status(character_name, user)

    @router.get("/api/proactive/timings")
    def timings_endpoint(user: str = Depends(current_user)):
        return timings(user)

    @router.post("/api/proactive/character-timing")
    def set_timing_endpoint(req: CharacterTimingRequest, user: str = Depends(current_user)):
        return set_timing(req, user)

    @router.post("/api/proactive/trigger")
    async def trigger_endpoint(req: ProactiveTriggerRequest, user: str = Depends(current_user)):
        return await trigger(req, user)

    return router
