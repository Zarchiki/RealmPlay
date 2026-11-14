"""Authentication, profile, and administrator endpoints."""

import json
import os
from typing import Callable

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse

from app.schemas.auth import (
    AdminCreateUserRequest,
    DeleteUserRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    RegistrationRequest,
    ResetPasswordRequest,
)


def build_router(auth_service, registration_service, rewards_service, current_user: Callable):
    """Build routes with explicit legacy-service dependencies."""
    router = APIRouter()

    def admin_user(user: str = Depends(current_user)) -> str:
        if not auth_service.is_admin_user(user):
            raise HTTPException(status_code=403, detail="Admin privileges required (ต้องเข้าสู่ระบบด้วยสิทธิ์ผู้ดูแล Zarch)")
        return user

    @router.post("/api/auth/register")
    def register(req: RegisterRequest):
        raise HTTPException(status_code=403, detail="สมัครบัญชีใหม่ผ่านคำขอและรอผู้ดูแลอนุมัติ")

    @router.post("/api/auth/registration-request")
    def submit_registration_request(req: RegistrationRequest):
        try:
            return registration_service.request_account(req.username, req.email)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/api/auth/login")
    def login(req: LoginRequest):
        result = auth_service.authenticate_user(req.username, req.password)
        if not result["ok"]:
            raise HTTPException(status_code=401, detail=result["error"])
        return result

    @router.post("/api/auth/logout")
    def logout(authorization: str | None = Header(None), user: str = Depends(current_user)):
        auth_service.revoke_token(authorization.replace("Bearer ", "").strip())
        return {"ok": True}

    @router.get("/api/auth/me")
    def get_me(user: str = Depends(current_user)):
        settings_path = os.path.join("users", user, "settings.json")
        settings = {}
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as file:
                settings = json.load(file)
        profile = auth_service.get_user_profile(user)
        return {
            "username": user,
            "display_name": profile["display_name"],
            "persona": profile["persona"],
            "is_admin": auth_service.is_admin_user(user),
            "settings": settings,
            "rewards": rewards_service.get_player_rewards(user),
        }

    @router.post("/api/auth/profile")
    def update_profile(req: ProfileUpdateRequest, user: str = Depends(current_user)):
        if not auth_service.update_user_profile(user, display_name=req.display_name, persona=req.persona):
            raise HTTPException(status_code=400, detail="Failed to update profile")
        profile = auth_service.get_user_profile(user)
        return {"ok": True, "display_name": profile["display_name"], "persona": profile["persona"]}

    @router.get("/admin")
    def serve_admin():
        admin_file = "static/admin.html"
        if os.path.exists(admin_file):
            return FileResponse(admin_file)
        raise HTTPException(status_code=404, detail="Admin page not found")

    @router.get("/api/admin/users")
    def get_admin_users(admin: str = Depends(admin_user)):
        return {"users": auth_service.list_users_details(), "admin_user": admin}

    @router.post("/api/admin/reset-password")
    def reset_password(req: ResetPasswordRequest, admin: str = Depends(admin_user)):
        result = auth_service.reset_password(req.username, req.new_password)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to reset password"))
        return result

    @router.post("/api/admin/create-user")
    def create_user(req: AdminCreateUserRequest, admin: str = Depends(admin_user)):
        result = auth_service.register_user(req.username, req.password, display_name=req.display_name)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create user"))
        return result

    @router.post("/api/admin/delete-user")
    def delete_user(req: DeleteUserRequest, admin: str = Depends(admin_user)):
        result = auth_service.delete_user(req.username)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to delete user"))
        return result

    return router
