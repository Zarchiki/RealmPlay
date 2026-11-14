"""Player rewards read operations."""


def profile(user: str, rewards) -> dict:
    return rewards.get_player_rewards(user)


def shop(user: str, rewards, category: str = "general", slot: str | None = None,
         q: str | None = None, limit: int = 60, offset: int = 0) -> dict:
    player = rewards.get_player_rewards(user)
    bargain = next((skill for skill in player.get("skills", []) if skill.get("id") == "bargain"), None)
    level = bargain.get("level", 0) if bargain else 0
    if str(category or "general").lower() == "wardrobe":
        catalog = rewards.wardrobe_shop_catalog(slot=slot, q=q, limit=limit, offset=offset)
        return {"catalog": catalog["items"], "total": catalog["total"], "slots": catalog["slots"],
                "category": "wardrobe", "limit": catalog["limit"], "offset": catalog["offset"],
                "discount_pct": level * 5, "coins": player.get("coins", 0)}
    if str(category or "general").lower() == "h_items":
        return {"catalog": list(rewards.H_ITEM_CATALOG), "total": len(rewards.H_ITEM_CATALOG), "slots": {},
                "category": "h_items", "discount_pct": level * 5, "coins": player.get("coins", 0)}
    return {"catalog": list(rewards.SHOP_CATALOG), "total": len(rewards.SHOP_CATALOG), "slots": {},
            "category": "general", "discount_pct": level * 5, "coins": player.get("coins", 0)}


def command(user: str, action: str, rewards, *args) -> dict:
    methods = {
        "stat": rewards.allocate_stat,
        "skill": rewards.upgrade_skill,
        "buy": rewards.buy_shop_item,
        "gacha": rewards.pull_gacha,
    }
    result = methods[action](user, *args)
    if not result["ok"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result["error"])
    return result


def gift_affection_boost(rarity: str, quantity: int, skills) -> int:
    base = {"Common": 3, "Uncommon": 6, "Rare": 12, "Super Rare": 20, "SSR": 25}.get(str(rarity), 4)
    boost = base * max(1, int(quantity))
    charisma = int(skills.get("charisma", 0)) if isinstance(skills, dict) else 0
    return int(boost * (1 + charisma * 0.1)) if charisma > 0 else boost
