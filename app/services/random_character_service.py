"""Random character-card generation orchestration."""

import asyncio
import logging
import shutil
from pathlib import Path

from fastapi import HTTPException


async def generate(req, user: str, query_llm_func, generator, comfy_client) -> dict:
    try:
        mode = (req.theme if req else "fantasy").lower()
        if mode not in {"highschool", "normal", "monster", "fantasy"}:
            raise HTTPException(status_code=400, detail="Invalid random character mode")
        age_mode = (req.age_mode if req else "auto").lower()
        if age_mode not in {"auto", "custom"}:
            raise HTTPException(status_code=400, detail="Invalid age selection mode")
        if age_mode == "custom" and req.age is None:
            raise HTTPException(status_code=400, detail="Custom age requires an age value")
        try:
            overrides = req.outfit_overrides if (req and getattr(req, "outfit_overrides", None)) else None
            matrix = generator.sample_rpg_female_wildcard_matrix(
                mode=mode, specific_age=req.age if age_mode == "custom" else None,
                overrides=overrides,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        character = generator.synthesize_complete_character_card(matrix, query_llm_func=query_llm_func)
        saved = generator.save_character_to_realmplay(character, user=user)
        avatar = {"generated": False}
        if req is None or req.generate_avatar:
            prompt = str(character.get("avatar_prompt") or character.get("image_appearance") or "").strip()
            if not prompt:
                avatar = {"generated": False, "error": "The generated character has no avatar prompt"}
            else:
                try:
                    image = await comfy_client.generate_character_image(
                        prompt, width=640, height=960,
                        context={"appearance": str(character.get("image_appearance") or ""), "emotion": "neutral expression"},
                        timeout=180,
                    )
                    shutil.copyfile(image, Path("characters") / saved["character_name"] / "avatar.png")
                    avatar = {"generated": True, "aspect_ratio": "2:3"}
                except Exception as exc:
                    logging.warning("Random character avatar generation failed: %s", exc)
                    avatar = {"generated": False, "error": str(exc)}
        return {"ok": True, "character": saved, "avatar": avatar}
    except HTTPException:
        raise
    except Exception as error:
        logging.exception("Failed to generate random character")
        raise HTTPException(status_code=500, detail=f"Failed to generate random character: {error}")
