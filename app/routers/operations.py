"""Operational status, cancellation, and restart endpoints."""

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException


def build_router(activity, current_user: Callable, restart: Callable, rules_snapshot: Callable):
    router = APIRouter()

    @router.get("/api/rules")
    def inspect_rules(user: str = Depends(current_user)):
        return rules_snapshot(user)

    @router.get("/api/activity")
    def inspect_activity(user: str = Depends(current_user)):
        return activity.snapshot(user)

    @router.get("/api/statistics")
    def inspect_statistics(user: str = Depends(current_user)):
        return activity.statistics(user)

    @router.post("/api/activity/{run_id}/cancel")
    def cancel_activity(run_id: str, user: str = Depends(current_user)):
        if not activity.request_cancel(run_id, user):
            raise HTTPException(status_code=404, detail="The active task was not found")
        return {"ok": True, "run_id": run_id, "status": "cancellation requested"}

    @router.post("/api/system/restart")
    def restart_realmplay(user: str = Depends(current_user)):
        return restart(user)

    return router
