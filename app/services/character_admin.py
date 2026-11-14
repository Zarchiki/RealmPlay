"""Global character-administration operations."""

from fastapi import HTTPException


def delete_everywhere(char_name: str, user: str, safe_name, delete_character) -> dict:
    if user.strip().casefold() != "zarch":
        raise HTTPException(status_code=403, detail="Only the Zarch profile can delete characters")
    try:
        return {"ok": True, **delete_character(safe_name(char_name))}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Character not found")
    except OSError as error:
        raise HTTPException(status_code=500, detail=f"Cannot delete character data: {error}")
