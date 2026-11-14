"""Application settings endpoints."""

import json
import logging
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.system import SettingsUpdateRequest


def build_router(text_engine, current_user: Callable):
    router = APIRouter()

    @router.get("/api/settings")
    def get_settings(user: str = Depends(current_user)):
        try:
            with open("config.json", "r", encoding="utf-8") as file:
                config = json.load(file)
            engine_status = text_engine.built_in_engine.status()
            llm, comfy, tts, rvc = (config.get(key, {}) for key in ("llm", "comfy", "tts", "rvc"))
            return {
                "llm_provider": llm.get("provider", "builtin" if engine_status.get("state") == "ready" else "external"),
                "llm_api_url": llm.get("api_url", "http://127.0.0.1:5000/v1"), "llm_model": llm.get("model", "local"),
                "llm_temperature": llm.get("temperature", 0.7), "llm_top_p": llm.get("top_p", 0.9),
                "llm_repetition_penalty": llm.get("repetition_penalty", 1.1), "llm_max_tokens": llm.get("max_tokens", 512),
                "comfy_address": comfy.get("address", "http://127.0.0.1:8188"),
                "tts_voice": tts.get("default_voice", "th-TH-PremwadeeNeural"), "tts_rate": tts.get("rate", "+0%"),
                "tts_autoload": tts.get("autoload", False), "tts_autoplay": tts.get("autoplay", False),
                "rvc_enabled": rvc.get("enabled", False), "rvc_model": rvc.get("model_path", ""),
                "rvc_pitch": rvc.get("pitch", 0), "rvc_index": rvc.get("index_path", ""),
                "rvc_index_rate": rvc.get("index_rate", 0.75), "rvc_protect": rvc.get("protect", 0.33), "engine": engine_status,
            }
        except Exception as error:
            logging.exception("[Settings] Fetch settings failed for user=%s", user)
            raise HTTPException(status_code=500, detail=str(error))

    @router.post("/api/settings")
    def update_settings(req: SettingsUpdateRequest, user: str = Depends(current_user)):
        try:
            with open("config.json", "r", encoding="utf-8") as file:
                config = json.load(file)
            for section, field, config_key in (
                ("llm", "llm_provider", "provider"), ("llm", "llm_api_url", "api_url"), ("llm", "llm_model", "model"),
                ("llm", "llm_temperature", "temperature"), ("llm", "llm_top_p", "top_p"),
                ("llm", "llm_repetition_penalty", "repetition_penalty"), ("llm", "llm_max_tokens", "max_tokens"),
                ("comfy", "comfy_address", "address"), ("tts", "tts_voice", "default_voice"), ("tts", "tts_rate", "rate"),
                ("tts", "tts_autoload", "autoload"), ("tts", "tts_autoplay", "autoplay"),
                ("rvc", "rvc_enabled", "enabled"), ("rvc", "rvc_model", "model_path"), ("rvc", "rvc_pitch", "pitch"),
                ("rvc", "rvc_index", "index_path"), ("rvc", "rvc_index_rate", "index_rate"), ("rvc", "rvc_protect", "protect"),
            ):
                value = getattr(req, field)
                if value is not None:
                    config.setdefault(section, {})[config_key] = value.strip() if isinstance(value, str) else value
            if req.tts_autoplay:
                config.setdefault("tts", {})["autoload"] = True
            with open("config.json", "w", encoding="utf-8") as file:
                json.dump(config, file, indent=2, ensure_ascii=False)
            return {"ok": True, "settings": config}
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    return router
