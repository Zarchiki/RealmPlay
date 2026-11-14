"""HTTP routes for outfits and wardrobe catalogs."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.character import EquipPresetRequest, EquipSlotItemRequest, OutfitUpdateRequest


def build_router(current_user: Callable, get_outfits: Callable, set_outfit: Callable, preset: Callable, equip_item: Callable, catalog: Callable, items: Callable):
    router = APIRouter()

    @router.get("/api/characters/{char_name}/outfits")
    def outfits_endpoint(char_name: str, user: str = Depends(current_user)):
        return get_outfits(char_name, user)

    @router.post("/api/characters/{char_name}/outfits")
    def set_outfit_endpoint(char_name: str, req: OutfitUpdateRequest, user: str = Depends(current_user)):
        return set_outfit(char_name, req, user)

    @router.post("/api/characters/{char_name}/outfits/preset")
    def preset_endpoint(char_name: str, req: EquipPresetRequest, user: str = Depends(current_user)):
        return preset(char_name, req, user)

    @router.post("/api/characters/{char_name}/outfits/equip-item")
    def equip_endpoint(char_name: str, req: EquipSlotItemRequest, user: str = Depends(current_user)):
        return equip_item(char_name, req, user)

    @router.get("/api/wardrobe/catalog")
    def catalog_endpoint(user: str = Depends(current_user)):
        return catalog(user)

    @router.get("/api/wardrobe/items")
    def items_endpoint(
        slot: str | None = None, q: str | None = None, limit: int = 300,
        offset: int = 0, user: str = Depends(current_user),
    ):
        return items(slot, q, limit, offset, user)

    return router
