"""Request schemas for rewards, media, settings, and local engine APIs."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class AllocateStatRequest(BaseModel):
    stat_name: str
    amount: Optional[int] = 1


class UpgradeSkillRequest(BaseModel):
    skill_id: str


class BuyItemRequest(BaseModel):
    item_id: str
    qty: Optional[int] = 1
    color: Optional[str] = None


class GachaPullRequest(BaseModel):
    pull_count: Optional[int] = 1
    pool_type: Optional[str] = "gift"


class GiveGiftRequest(BaseModel):
    character_name: str
    item_name: str
    qty: Optional[int] = 1


class UseHItemRequest(BaseModel):
    character_name: str
    item_name: str


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "th-TH-PremwadeeNeural"
    pitch: Optional[int] = 0
    rate: Optional[str] = "+0%"
    rvc_model: Optional[str] = None
    rvc_index: Optional[str] = None
    rvc_index_rate: Optional[float] = None
    rvc_protect: Optional[float] = None


class SaveVoiceParamsRequest(BaseModel):
    model_path: str
    pitch: Optional[int] = 0
    index_file: Optional[str] = ""
    index_rate: Optional[float] = 0.75
    protect: Optional[float] = 0.33
    extra_params: Optional[Dict[str, Any]] = None


class GenerateImageRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    width: Optional[int] = None
    height: Optional[int] = None
    character_name: Optional[str] = None
    outfit: Optional[str] = None


class SettingsUpdateRequest(BaseModel):
    llm_provider: Optional[str] = None
    llm_api_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_top_p: Optional[float] = None
    llm_repetition_penalty: Optional[float] = None
    llm_max_tokens: Optional[int] = None
    comfy_address: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_rate: Optional[str] = None
    tts_autoload: Optional[bool] = None
    tts_autoplay: Optional[bool] = None
    rvc_enabled: Optional[bool] = None
    rvc_model: Optional[str] = None
    rvc_pitch: Optional[int] = None
    rvc_index: Optional[str] = None
    rvc_index_rate: Optional[float] = None
    rvc_protect: Optional[float] = None


class StartEngineRequest(BaseModel):
    model_name: str
    mmproj: Optional[str] = None
    context: Optional[int] = 8192
    gpu_layers: Optional[int] = 99
    threads: Optional[int] = 8
    batch_size: Optional[int] = 512
    cache_type_k: Optional[str] = "q8_0"
    cache_type_v: Optional[str] = "q8_0"
