"""Request schemas for character, wardrobe, and proactive-character APIs."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class UpdateStateRequest(BaseModel):
    character_name: str
    scenario: Optional[str] = None
    memory: Optional[str] = None
    status: Optional[str] = None
    emotion: Optional[str] = None
    emotion_detail: Optional[Dict[str, Any]] = None
    time_state: Optional[Dict[str, Any]] = None
    appearance: Optional[str] = None
    character_profile: Optional[str] = None
    inventory: Optional[Any] = None
    current_outfit: Optional[str] = None


class InventoryActionRequest(BaseModel):
    action: str
    item: Dict[str, Any]


class OutfitUpdateRequest(BaseModel):
    current_outfit: Optional[str] = None
    outfit_id: Optional[str] = None
    outfit_name: Optional[str] = None
    outfit_prompt: Optional[str] = None
    outfits: Optional[Dict[str, Any]] = None


class EquipPresetRequest(BaseModel):
    preset_name: str
    preset_prompt: str
    category: Optional[str] = None


class EquipSlotItemRequest(BaseModel):
    slot: str
    item_name: str
    item_prompt: str
    category: Optional[str] = None


class ProactiveHeartbeatRequest(BaseModel):
    character_name: Optional[str] = ""
    activity: bool = False
    min_seconds: Optional[int] = None
    max_seconds: Optional[int] = None


class ProactiveTriggerRequest(BaseModel):
    character_name: str
    message: Optional[str] = None


class CharacterTimingRequest(BaseModel):
    character_name: str
    min_seconds: Optional[int] = None
    max_seconds: Optional[int] = None


class UpdateCharacterCardRequest(BaseModel):
    character_name: str
    persona: Optional[str] = None
    personality: Optional[str] = None
    scenario: Optional[str] = None
    first_mes: Optional[str] = None


class CreateCharacterRequest(BaseModel):
    name: str
    persona: Optional[str] = ""
    personality: Optional[str] = ""
    scenario: Optional[str] = ""
    first_mes: Optional[str] = ""
    avatar_base64: Optional[str] = None
    gender: Optional[str] = "Female"
    age: Optional[str] = ""
    status: Optional[str] = "Single"
    role_goals: Optional[str] = ""
    sex_preference: Optional[str] = ""
    likes_dislikes: Optional[str] = ""
    communication_style: Optional[str] = ""
    char_summary: Optional[str] = ""
    outfit_overrides: Optional[Dict[str, Any]] = None


class RandomCharacterRequest(BaseModel):
    gender: str = "female"
    theme: str = "fantasy"
    generate_avatar: bool = True
    age_mode: str = "auto"
    age: Optional[int] = None
    outfit_overrides: Optional[Dict[str, Any]] = None
