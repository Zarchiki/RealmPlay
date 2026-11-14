"""Built-in LLM engine endpoints."""

import json
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.system import StartEngineRequest


def build_router(text_engine, current_user: Callable):
    router = APIRouter()
    engine = text_engine.built_in_engine

    @router.get("/api/engine/status")
    def get_status(user: str = Depends(current_user)):
        return engine.status()

    @router.get("/api/engine/models")
    def get_models(user: str = Depends(current_user)):
        executable = engine.get_server_exe()
        return {"models": engine.list_models(), "has_server_exe": bool(executable), "exe_path": str(executable) if executable else ""}

    @router.get("/api/engine/vision_models")
    def get_vision_models(user: str = Depends(current_user)):
        return {"models": engine.list_vision_models()}

    @router.post("/api/engine/start")
    def start(req: StartEngineRequest, user: str = Depends(current_user)):
        try:
            engine_status = engine.start(
                model_name=req.model_name, mmproj=req.mmproj, context=req.context or 4096,
                gpu_layers=req.gpu_layers if req.gpu_layers is not None else 99,
                threads=req.threads or 8, batch_size=req.batch_size or 512,
                cache_type_k=req.cache_type_k or "q8_0", cache_type_v=req.cache_type_v or "q8_0",
            )
            try:
                with open("config.json", "r", encoding="utf-8") as file:
                    config = json.load(file)
                config.setdefault("llm", {})["provider"] = "builtin"
                config["llm"]["model"] = req.model_name
                if req.mmproj:
                    config["llm"]["mmproj"] = req.mmproj
                config["llm"]["cache_type_k"] = req.cache_type_k or "q8_0"
                config["llm"]["cache_type_v"] = req.cache_type_v or "q8_0"
                with open("config.json", "w", encoding="utf-8") as file:
                    json.dump(config, file, indent=2, ensure_ascii=False)
            except Exception as error:
                print(f"[Engine] Could not update config.json: {error}")
            return {"ok": True, "status": engine_status}
        except Exception as error:
            raise HTTPException(status_code=400, detail=str(error))

    @router.post("/api/engine/stop")
    def stop(user: str = Depends(current_user)):
        try:
            engine.stop()
            return {"ok": True, "status": engine.status()}
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    return router
