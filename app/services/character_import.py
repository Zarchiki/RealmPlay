"""Safe import workflow for PNG and JSON character cards."""

import os
import time

from fastapi import HTTPException, UploadFile


async def import_card(file: UploadFile, character_card) -> dict:
    if not (file.filename or "").lower().endswith((".png", ".json")):
        raise HTTPException(status_code=400, detail="Character card must be a PNG or JSON file")
    suffix = ".json" if (file.filename or "").lower().endswith(".json") else ".png"
    temporary_path = os.path.join("data", f"temp_character_{time.time_ns()}{suffix}")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Character card exceeds the 25 MB limit")
    with open(temporary_path, "wb") as target:
        target.write(content)
    try:
        return character_card.import_character_card(temporary_path)
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Import failed: {error}")
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
