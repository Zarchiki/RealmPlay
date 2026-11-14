"""Authentication and profile request schemas."""

from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None


class RegistrationRequest(BaseModel):
    username: str
    email: str


class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str


class AdminCreateUserRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    display_name: str
    persona: Optional[str] = ""


class DeleteUserRequest(BaseModel):
    username: str
