"""Player Reward & RPG Progression System for RealmPlay.

Manages:
- Player RPG stats: LV, EXP, Coins, Stat Points, Skill Points, Allocated Stats, Skills
- Rewards for chatting / roleplaying
- Shop for purchasing Special Items / Gifts
- Gacha system to pull for rare/special gifts & items
- Giving items to characters
"""
import json
import os
import random
import time
from typing import Dict, Any, List, Optional

REWARDS_FILE_NAME = "rewards.json"
MAX_LEVEL = 999

# Base EXP requirement formula: level * 100
def get_exp_for_level(level: int) -> int:
    return max(100, int(level * 100))

# Pre-defined Shop Catalog
SHOP_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "item_sweet_candy",
        "name": "ลูกอมรสหวาน",
        "type": "consumable",
        "price": 20,
        "rarity": "Common",
        "icon": "🍬",
        "desc": "ลูกอมรสผลไม้หอมหวาน เพิ่มความสดชื่นและความผูกพันเล็กน้อย"
    },
    {
        "id": "item_hot_coffee",
        "name": "กาแฟลาเต้อุ่น",
        "type": "consumable",
        "price": 50,
        "rarity": "Common",
        "icon": "☕",
        "desc": "กาแฟหอมกรุ่น ช่วยให้ตื่นตัวและผ่อนคลาย"
    },
    {
        "id": "item_flower_bouquet",
        "name": "ช่อดอกไม้สด",
        "type": "gift",
        "price": 120,
        "rarity": "Uncommon",
        "icon": "💐",
        "desc": "ดอกไม้สดสวยงาม สื่อถึงความรู้สึกดีและความประทับใจ"
    },
    {
        "id": "item_music_box",
        "name": "กล่องดนตรีโบราณ",
        "type": "special",
        "price": 300,
        "rarity": "Rare",
        "icon": "🎵",
        "desc": "กล่องดนตรีไขลาน บรรเลงบทเพลงแสนอบอุ่นในค่ำคืน"
    },
    {
        "id": "item_silk_ribbon",
        "name": "ริบบิ้นผ้าไหมชั้นดี",
        "type": "accessory",
        "price": 250,
        "rarity": "Rare",
        "icon": "🎀",
        "desc": "ริบบิ้นผ้าไหมเนื้อเนียนสวยงาม เหมาะสำหรับมอบเป็นของขวัญประดับกาย"
    },
    {
        "id": "item_scented_candle",
        "name": "เทียนหอมอโรมาผ่อนคลาย",
        "type": "special",
        "price": 180,
        "rarity": "Uncommon",
        "icon": "🕯️",
        "desc": "กระจายกลิ่นหอมชวนเคลิบเคลิ้ม ช่วยสร้างบรรยากาศโรแมนติกเป็นกันเอง"
    },
    {
        "id": "item_starlight_pendant",
        "name": "จี้ไข่มุกประกายดาว",
        "type": "special",
        "price": 800,
        "rarity": "Super Rare",
        "icon": "✨",
        "desc": "เครื่องประดับล้ำค่า ส่องแสงเรืองรองอย่างน่าหลงใหลเมื่อต้องแสงไฟ"
    },
    {
        "id": "item_love_letter",
        "name": "จดหมายสารภาพความในใจ",
        "type": "gift",
        "price": 150,
        "rarity": "Uncommon",
        "icon": "💌",
        "desc": "จดหมายลายมือที่เขียนความรู้สึกอย่างจริงใจ"
    }
]

# Gacha Pool with weights
GACHA_POOL: List[Dict[str, Any]] = [
    # Common (50%)
    {"name": "ลูกอมรสหวาน", "type": "consumable", "rarity": "Common", "icon": "🍬", "desc": "ลูกอมรสผลไม้หอมหวาน", "weight": 25},
    {"name": "คุกกี้เนยสด", "type": "consumable", "rarity": "Common", "icon": "🍪", "desc": "คุกกี้อบกรอบหอมกรุ่น", "weight": 25},
    {"name": "ชาร้อนกลิ่นมะลิ", "type": "consumable", "rarity": "Common", "icon": "🍵", "desc": "น้ำชากลิ่นหอมละมุน", "weight": 20},
    
    # Uncommon (30%)
    {"name": "ช่อดอกกุหลาบแดง", "type": "gift", "rarity": "Uncommon", "icon": "🌹", "desc": "กุหลาบแดงช่อโตแสดงความรัก", "weight": 15},
    {"name": "ตุ๊กตาหมีขนนุ่ม", "type": "gift", "rarity": "Uncommon", "icon": "🧸", "desc": "ตุ๊กตาหมีน่ากอดอบอุ่น", "weight": 15},
    {"name": "สมุดบันทึกล็อคกุญแจ", "type": "special", "rarity": "Uncommon", "icon": "📔", "desc": "สมุดบันทึกความทรงจำลับเฉพาะสองเรา", "weight": 10},

    # Rare (15%)
    {"name": "น้ำหอมกลิ่นดอกไม้ราตรี", "type": "special", "rarity": "Rare", "icon": "🌸", "desc": "น้ำหอมเสน่ห์ดึงดูด ชวนหลงใหลอย่างลึกซึ้ง", "weight": 8},
    {"name": "สร้อยคอคริสตัลเงิน", "type": "special", "rarity": "Rare", "icon": "💎", "desc": "สร้อยคอเปล่งประกายงดงาม", "weight": 7},

    # Super Rare / SSR (5%)
    {"name": "แหวนสัญญาแห่งดวงดาว", "type": "special", "rarity": "SSR", "icon": "💍", "desc": "แหวนแห่งพันธสัญญาพิเศษ มอบให้เพื่อแทนใจนิรันดร์", "weight": 3},
    {"name": "ชุดนอนผ้าซาตินเย้ายวน", "type": "special", "rarity": "SSR", "icon": "👗", "desc": "ชุดนอนผ้าซาตินบางเบา เพิ่มความใกล้ชิดและความเสน่หาอย่างเร่าร้อน", "weight": 2}
]

DEFAULT_SKILLS = [
    {
        "id": "charisma",
        "name": "Charisma (เสน่ห์วาจา)",
        "level": 0,
        "max_level": 5,
        "desc": "เพิ่มโบนัสค่าความสัมพันธ์และ EXP เมื่อคุยกับตัวละคร"
    },
    {
        "id": "bargain",
        "name": "Bargaining (ต่อรองราคา)",
        "level": 0,
        "max_level": 5,
        "desc": "รับส่วนลดเมื่อซื้อของในร้านค้า 5% ต่อเลเวล"
    },
    {
        "id": "lucky_charm",
        "name": "Lucky Charm (โชคลาภ)",
        "level": 0,
        "max_level": 5,
        "desc": "เพิ่มโอกาสได้รับไอเทมหายากจากตู้สุ่มกาชา"
    },
    {
        "id": "sweet_talk",
        "name": "Sweet Talk (คำหวานสะกดใจ)",
        "level": 0,
        "max_level": 5,
        "desc": "เพิ่มความพึงพอใจและโอกาสได้รับคำตอบสุดพิเศษจากตัวละคร"
    }
]

def get_player_rewards_path(username: str) -> str:
    user_dir = os.path.join("users", username)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, REWARDS_FILE_NAME)

def get_player_rewards(username: str) -> Dict[str, Any]:
    path = get_player_rewards_path(username)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure all required keys exist
            _ensure_reward_defaults(data)
            return data
        except Exception:
            pass

    # Default initial player reward profile
    initial = {
        "level": 1,
        "exp": 0,
        "next_exp": get_exp_for_level(1),
        "coins": 100,  # Starting money
        "stat_points": 5,
        "skill_points": 1,
        "stats": {
            "str": 10,  # Strength
            "agi": 10,  # Agility
            "int": 10,  # Intelligence
            "luk": 10,  # Luck
            "cha": 10   # Charisma
        },
        "skills": [dict(s) for s in DEFAULT_SKILLS],
        "inventory": [
            {"name": "ลูกอมรสหวาน", "qty": 3, "desc": "ลูกอมรสผลไม้หอมหวาน", "icon": "🍬", "type": "consumable"}
        ],
        "chat_count": 0,
        "gacha_count": 0,
        "last_reward_time": 0
    }
    save_player_rewards(username, initial)
    return initial

def _ensure_reward_defaults(data: Dict[str, Any]):
    if "level" not in data or data["level"] < 1:
        data["level"] = 1
    elif data["level"] > MAX_LEVEL:
        data["level"] = MAX_LEVEL
    if "exp" not in data:
        data["exp"] = 0
    if data["level"] >= MAX_LEVEL:
        data["next_exp"] = get_exp_for_level(MAX_LEVEL)
        if data["exp"] > data["next_exp"]:
            data["exp"] = data["next_exp"]
    else:
        data["next_exp"] = get_exp_for_level(data["level"])
    if "coins" not in data:
        data["coins"] = 100
    if "stat_points" not in data:
        data["stat_points"] = 0
    if "skill_points" not in data:
        data["skill_points"] = 0
    if "stats" not in data or not isinstance(data["stats"], dict):
        data["stats"] = {"str": 10, "agi": 10, "int": 10, "luk": 10, "cha": 10}
    for s_key in ["str", "agi", "int", "luk", "cha"]:
        if s_key not in data["stats"]:
            data["stats"][s_key] = 10
    if "inventory" not in data or not isinstance(data["inventory"], list):
        data["inventory"] = []
    if "skills" not in data or not isinstance(data["skills"], list):
        data["skills"] = [dict(s) for s in DEFAULT_SKILLS]
    else:
        # Merge any missing skill
        existing_ids = {s.get("id") for s in data["skills"] if isinstance(s, dict)}
        for default_s in DEFAULT_SKILLS:
            if default_s["id"] not in existing_ids:
                data["skills"].append(dict(default_s))

def save_player_rewards(username: str, data: Dict[str, Any]):
    # Absolute limiter: Level can never exceed MAX_LEVEL
    if data.get("level", 1) >= MAX_LEVEL:
        data["level"] = MAX_LEVEL
        data["next_exp"] = get_exp_for_level(MAX_LEVEL)
        data["exp"] = data["next_exp"]  # Locked at 100% full bar
    path = get_player_rewards_path(username)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def award_chat_activity(username: str) -> Dict[str, Any]:
    """Awards player EXP & Coins for chatting with characters."""
    profile = get_player_rewards(username)
    
    # Calculate bonus from Charisma skill / stat
    cha_stat = profile["stats"].get("cha", 10)
    charisma_skill = next((s for s in profile.get("skills", []) if s.get("id") == "charisma"), None)
    cha_level = charisma_skill.get("level", 0) if charisma_skill else 0

    base_exp = 15 + random.randint(5, 10)
    base_coins = 10 + random.randint(2, 6)

    # Bonuses
    bonus_exp = int(base_exp * (cha_level * 0.1 + (cha_stat - 10) * 0.02))
    bonus_coins = int(base_coins * (cha_level * 0.05))

    total_exp = base_exp + max(0, bonus_exp)
    total_coins = base_coins + max(0, bonus_coins)

    leveled_up = False
    levels_gained = 0

    if profile["level"] >= MAX_LEVEL:
        profile["level"] = MAX_LEVEL
        profile["next_exp"] = get_exp_for_level(MAX_LEVEL)
        profile["exp"] = profile["next_exp"]  # Locked at max exp (100%)
    else:
        profile["exp"] += total_exp
        # Level Up Check
        while profile["level"] < MAX_LEVEL and profile["exp"] >= profile["next_exp"]:
            profile["exp"] -= profile["next_exp"]
            profile["level"] += 1
            levels_gained += 1
            profile["stat_points"] += 3
            profile["skill_points"] += 1
            profile["next_exp"] = get_exp_for_level(profile["level"])
            leveled_up = True

        if profile["level"] >= MAX_LEVEL:
            profile["level"] = MAX_LEVEL
            profile["next_exp"] = get_exp_for_level(MAX_LEVEL)
            profile["exp"] = profile["next_exp"]

    profile["coins"] += total_coins
    profile["chat_count"] = profile.get("chat_count", 0) + 1
    profile["last_reward_time"] = time.time()

    save_player_rewards(username, profile)
    return {
        "earned_exp": total_exp,
        "earned_coins": total_coins,
        "leveled_up": leveled_up,
        "new_level": profile["level"],
        "levels_gained": levels_gained,
        "profile": profile
    }

def allocate_stat(username: str, stat_name: str, amount: int = 1) -> Dict[str, Any]:
    profile = get_player_rewards(username)
    stat_name = stat_name.lower().strip()
    if stat_name not in profile["stats"]:
        return {"ok": False, "error": f"Invalid stat name: {stat_name}"}
    if profile["stat_points"] < amount:
        return {"ok": False, "error": "Not enough stat points"}

    profile["stat_points"] -= amount
    profile["stats"][stat_name] += amount
    save_player_rewards(username, profile)
    return {"ok": True, "profile": profile}

def upgrade_skill(username: str, skill_id: str) -> Dict[str, Any]:
    profile = get_player_rewards(username)
    if profile["skill_points"] < 1:
        return {"ok": False, "error": "Not enough skill points"}

    target_skill = next((s for s in profile.get("skills", []) if s.get("id") == skill_id), None)
    if not target_skill:
        return {"ok": False, "error": f"Skill not found: {skill_id}"}

    if target_skill["level"] >= target_skill.get("max_level", 5):
        return {"ok": False, "error": "Skill already at max level"}

    profile["skill_points"] -= 1
    target_skill["level"] += 1
    save_player_rewards(username, profile)
    return {"ok": True, "profile": profile}

def buy_shop_item(username: str, item_id: str, qty: int = 1) -> Dict[str, Any]:
    if qty < 1:
        qty = 1
    item = next((i for i in SHOP_CATALOG if i["id"] == item_id), None)
    if not item:
        return {"ok": False, "error": f"Item {item_id} not in catalog"}

    profile = get_player_rewards(username)

    # Calculate discount from Bargaining skill
    bargain_skill = next((s for s in profile.get("skills", []) if s.get("id") == "bargain"), None)
    bargain_level = bargain_skill.get("level", 0) if bargain_skill else 0
    discount_multiplier = max(0.6, 1.0 - (bargain_level * 0.05))

    single_price = max(1, int(item["price"] * discount_multiplier))
    total_cost = single_price * qty

    if profile["coins"] < total_cost:
        return {"ok": False, "error": f"Coins ไม่เพียงพอ (ต้องการ {total_cost} Coins แต่มี {profile['coins']} Coins)"}

    profile["coins"] -= total_cost

    # Add to player inventory
    inv = profile.get("inventory", [])
    found = False
    for existing in inv:
        if existing.get("name") == item["name"]:
            existing["qty"] = int(existing.get("qty", 1)) + qty
            found = True
            break
    if not found:
        inv.append({
            "name": item["name"],
            "qty": qty,
            "desc": item.get("desc", ""),
            "icon": item.get("icon", "🎁"),
            "type": item.get("type", "item"),
            "rarity": item.get("rarity", "Common")
        })
    profile["inventory"] = inv
    save_player_rewards(username, profile)

    return {
        "ok": True,
        "message": f"ซื้อ {item['name']} x{qty} สำเร็จ! (ใช้ {total_cost} Coins)",
        "profile": profile,
        "item": item
    }

def pull_gacha(username: str, pull_count: int = 1) -> Dict[str, Any]:
    if pull_count not in (1, 10):
        pull_count = 1
    cost_per_pull = 50
    total_cost = (cost_per_pull * 10 - 50) if pull_count == 10 else cost_per_pull  # 10 pulls discount to 450 coins

    profile = get_player_rewards(username)
    if profile["coins"] < total_cost:
        return {"ok": False, "error": f"Coins ไม่พอสำหรับการสุ่ม (ต้องการ {total_cost} Coins มี {profile['coins']} Coins)"}

    # Luck stat & Lucky Charm skill bonus
    luk_stat = profile["stats"].get("luk", 10)
    lucky_skill = next((s for s in profile.get("skills", []) if s.get("id") == "lucky_charm"), None)
    lucky_level = lucky_skill.get("level", 0) if lucky_skill else 0
    rare_multiplier = 1.0 + (lucky_level * 0.1) + ((luk_stat - 10) * 0.02)

    profile["coins"] -= total_cost
    profile["gacha_count"] = profile.get("gacha_count", 0) + pull_count

    won_items = []
    for _ in range(pull_count):
        # Build weighted pool with luck adjustment
        pool_weights = []
        for it in GACHA_POOL:
            w = it["weight"]
            if it.get("rarity") in ("Rare", "SSR"):
                w = int(w * rare_multiplier)
            pool_weights.append(w)

        chosen = random.choices(GACHA_POOL, weights=pool_weights, k=1)[0]
        won_items.append(dict(chosen))

        # Add to player inventory
        inv = profile.get("inventory", [])
        found = False
        for existing in inv:
            if existing.get("name") == chosen["name"]:
                existing["qty"] = int(existing.get("qty", 1)) + 1
                found = True
                break
        if not found:
            inv.append({
                "name": chosen["name"],
                "qty": 1,
                "desc": chosen.get("desc", ""),
                "icon": chosen.get("icon", "🎁"),
                "type": chosen.get("type", "item"),
                "rarity": chosen.get("rarity", "Common")
            })
        profile["inventory"] = inv

    save_player_rewards(username, profile)
    return {
        "ok": True,
        "items": won_items,
        "cost": total_cost,
        "profile": profile
    }
