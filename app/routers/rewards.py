"""HTTP boundary for player rewards and RPG progression."""

from typing import Callable

from fastapi import APIRouter, Depends

from app.schemas.system import AllocateStatRequest, BuyItemRequest, GachaPullRequest, GiveGiftRequest, UpgradeSkillRequest, UseHItemRequest


def build_router(current_user: Callable, profile: Callable, shop: Callable, stat: Callable, skill: Callable, buy: Callable, gacha: Callable, gift: Callable, use_h_item: Callable):
    router = APIRouter()

    @router.get("/api/rewards/profile")
    def profile_endpoint(user: str = Depends(current_user)):
        return profile(user)

    @router.get("/api/rewards/shop")
    def shop_endpoint(category: str = "general", slot: str | None = None, q: str | None = None,
                      limit: int = 60, offset: int = 0, user: str = Depends(current_user)):
        return shop(user, category, slot, q, limit, offset)

    @router.post("/api/rewards/stat")
    def stat_endpoint(req: AllocateStatRequest, user: str = Depends(current_user)):
        return stat(req, user)

    @router.post("/api/rewards/skill")
    def skill_endpoint(req: UpgradeSkillRequest, user: str = Depends(current_user)):
        return skill(req, user)

    @router.post("/api/rewards/buy")
    def buy_endpoint(req: BuyItemRequest, user: str = Depends(current_user)):
        return buy(req, user)

    @router.post("/api/rewards/gacha")
    def gacha_endpoint(req: GachaPullRequest, user: str = Depends(current_user)):
        return gacha(req, user)

    @router.post("/api/rewards/give_gift")
    async def gift_endpoint(req: GiveGiftRequest, user: str = Depends(current_user)):
        return await gift(req, user)

    @router.post("/api/rewards/use_h_item")
    def use_h_item_endpoint(req: UseHItemRequest, user: str = Depends(current_user)):
        return use_h_item(req, user)

    return router
