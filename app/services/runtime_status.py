"""Aggregate health/status information for local RealmPlay services."""

import json
import urllib.request
from typing import Callable


def all_status(engine, tunnel_status: Callable, config_provider: Callable) -> dict:
    engine_status = engine.status()
    comfy_alive = False
    try:
        address = config_provider().get("comfy", {}).get("address", "http://127.0.0.1:8188")
        request = urllib.request.Request(address.rstrip("/") + "/system_stats")
        with urllib.request.urlopen(request, timeout=0.3) as response:
            comfy_alive = response.status == 200
    except Exception:
        pass
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
    except Exception:
        config = {}
    return {
        "engine": engine_status,
        "comfy": {"connected": comfy_alive, "address": config.get("comfy", {}).get("address", "http://127.0.0.1:8188")},
        "voice": {
            "tts_voice": config.get("tts", {}).get("default_voice", "th-TH-PremwadeeNeural"),
            "rvc_enabled": config.get("rvc", {}).get("enabled", False),
            "rvc_model": config.get("rvc", {}).get("model_path", ""),
        },
        "tunnel": tunnel_status(),
    }
