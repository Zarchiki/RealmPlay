"""Request schemas for conversation and message-media APIs."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    character_name: str
    message: str
    image_base64: Optional[str] = None
    stream: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    # UI wardrobe controls are system events: the resulting visible action
    # belongs to the character, not to a user chat bubble.
    manual_wardrobe: bool = False


class ChatReadRequest(BaseModel):
    through: float = Field(default=0.0, ge=0, allow_inf_nan=False)


class RegenerateRequest(BaseModel):
    character_name: str
    message_index: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class EditMessageRequest(BaseModel):
    character_name: str
    index: int
    content: str


class DeleteMessageRequest(BaseModel):
    character_name: str
    index: int


class DeleteMessagesRequest(BaseModel):
    character_name: str
    indices: List[int]


class ContinueRequest(BaseModel):
    character_name: str
    message_index: Optional[int] = None


class DeleteImageRequest(BaseModel):
    image_url: str
    character_name: Optional[str] = None
    message_index: Optional[int] = None


class ContextImageRequest(BaseModel):
    character_name: str
    message_index: Optional[int] = None
    custom_instruction: Optional[str] = None
    prompt_override: Optional[str] = Field(default=None, max_length=6000)
    outfit: Optional[str] = None
