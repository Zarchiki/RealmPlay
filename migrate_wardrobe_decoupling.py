import json
import re
import os
import shutil

USERS_DIR = "users"
CATALOG_PATH = "data/wardrobe_catalog.json"
BACKUP_CATALOG = "data/wardrobe_catalog.json.bak_underwear"

EXACT_MAP = {
    "cute animal ear lace bralette with a fluffy tail accent and matching panties": {
        "top_inner": "Cute animal ear lace bralette with a fluffy tail accent",
        "bottom_inner": "matching panties with a fluffy tail accent",
    },
    "bunny ear lace bralette with a fluffy tail accent and matching panties": {
        "top_inner": "Bunny ear lace bralette with a fluffy tail accent",
        "bottom_inner": "matching panties with a fluffy tail accent",
    },
    "bear ear lace bralette with a fluffy tail accent and matching panties": {
        "top_inner": "Bear ear lace bralette with a fluffy tail accent",
        "bottom_inner": "matching panties with a fluffy tail accent",
    },
    "bunny face embroidered bralette with a fluffy pom-pom tail and matching thong": {
        "top_inner": "Bunny face embroidered bralette",
        "bottom_inner": "matching thong with a fluffy pom-pom tail",
    },
    "high-cut bikini with cheeky bottoms and a tie-front top": {
        "top_inner": "tie-front bikini top",
        "bottom_inner": "high-cut cheeky bikini bottoms",
        "top": "tie-front bikini top",
        "bottom": "high-cut cheeky bikini bottoms",
    },
    "high-cut bikini with cheeky bottoms and a tie-front detail": {
        "top_inner": "tie-front detail bikini top",
        "bottom_inner": "high-cut cheeky bikini bottoms",
    },
    "crochet bikini with a halter-neck top and matching bottoms": {
        "top_inner": "Crochet halter-neck bikini top",
        "bottom_inner": "matching crochet bikini bottoms",
    },
    "crochet bikini with a high-neck top and matching bottoms": {
        "top_inner": "Crochet high-neck bikini top",
        "bottom_inner": "matching crochet bikini bottoms",
    },
    "high-waisted lace panties with a matching bralette and garter belt": {
        "top_inner": "lace bralette with garter belt",
        "bottom_inner": "High-waisted lace panties",
    },
    "seamless hipster panties with a scalloped lace waistband and a seamless bralette": {
        "top_inner": "seamless bralette",
        "bottom_inner": "Seamless hipster panties with a scalloped lace waistband",
    },
    "brazilian cut panties with lace trim": {
        "top_inner": "lace trim bralette",
        "bottom_inner": "Brazilian cut panties with lace trim",
    },
    "sheer mesh bra and thong set with delicate embroidery": {
        "top_inner": "Sheer mesh bra with delicate embroidery",
        "bottom_inner": "matching sheer mesh thong with delicate embroidery",
    },
    "seamless bra and thong set with a fun pattern": {
        "top_inner": "Seamless bra with a fun pattern",
        "bottom_inner": "matching seamless thong with a fun pattern",
    },
    "cute animal-themed bralette set with matching panties": {
        "top_inner": "Cute animal-themed bralette",
        "bottom_inner": "matching cute animal-themed panties",
    },
    "chunky cable-knit aran sweater with a denim skirt and ankle boots": {
        "top": "Chunky cable-knit Aran sweater",
        "bottom": "denim skirt",
    },
    "aran sweater poncho worn over a striped top and skinny jeans": {
        "top": "Aran sweater poncho worn over a striped top",
        "bottom": "skinny jeans",
    },
    "aran sweater vest layered over a chambray shirt and distressed jeans with ankle booties": {
        "top": "Aran sweater vest layered over a chambray shirt",
        "bottom": "distressed jeans",
    },
    "button-down frilled shirt tied at the waist, paired with a printed boho long skirt and sandals": {
        "top": "Button-down frilled shirt tied at the waist",
        "bottom": "printed boho long skirt",
        "head_acc": "hair ribbon",
        "accessories": "boho sandals",
    },
    "striped collared shirt half-tucked into a solid color flared skirt, accessorized with a statement belt and ankle boots.": {
        "top": "Striped collared shirt half-tucked",
        "bottom": "solid color flared skirt",
        "neck_acc": "statement belt",
        "accessories": "statement belt",
    },
    "oversized white collared shirt worn off-the-shoulder, tucked into a pleated satin flared skirt with slingback pumps.": {
        "top": "Oversized white collared shirt worn off-the-shoulder",
        "bottom": "pleated satin flared skirt",
        "neck_acc": "slingback pumps",
        "accessories": "slingback pumps",
    },
    "whimsical pastels: a collared shirt in pastel shades, featuring whimsical prints like unicorns or clouds, combined with a soft-colored flared skirt. add a sprinkle of glitter with metallic accessories.": {
        "top": "Collared shirt in pastel shades with whimsical cloud prints",
        "bottom": "soft-colored flared skirt",
        "neck_acc": "metallic accessories",
        "accessories": "metallic accessories",
    },
    "modern retro: a retro-inspired collared shirt in a bold color paired with a high-waisted flared skirt featuring a matching pattern. complete the look with retro sunglasses and platform heels.": {
        "top": "Retro-inspired collared shirt in a bold color",
        "bottom": "high-waisted flared skirt with matching pattern",
        "neck_acc": "retro sunglasses",
        "accessories": "retro sunglasses",
    },
    "utility jumpsuit, platform sneakers": {
        "head_acc": "stylish hairpin",
        "accessories": "platform sneakers",
        "top": "Utility jumpsuit",
    },
    "(well dressed), (spread legs:1.4)": {
        "head_acc": "delicate hair ribbon",
        "accessories": "stylish hair clip",
    },
    "lace overlay sheath dress": {
        "head_acc": "lace hair accessory",
        "accessories": "lace hair accessory",
    },
}

def decouple_garment(slot: str, name: str) -> str:
    s = name.strip()
    nl = s.lower()

    if nl in EXACT_MAP and slot in EXACT_MAP[nl]:
        return EXACT_MAP[nl][slot]

    # Slot = top / top_inner: We want only the top half
    if slot in ("top", "top_inner"):
        # 1. Starts with bottom: e.g. '<bottom> with a matching <top>'
        m_rev = re.search(r"^(?:.*?)(?:boyshorts|panties|thong|briefs?|bottoms?)\s+(?:with|and)\s+(?:a\s+)?(?:matching\s+)?(.*)$", s, re.IGNORECASE)
        if m_rev and any(w in m_rev.group(1).lower() for w in ["bralette", "bra", "top", "camisole"]):
            top_part = m_rev.group(1).strip()
            top_part = re.sub(r"\s+and\s+garter\s+belt.*$", "", top_part, flags=re.IGNORECASE).strip()
            return top_part

        # 2. '<top> with/and [modifiers] <bottom>'
        m_norm = re.search(r"^(.*?)\s+(?:and|with)\s+(?:a\s+)?(?:matching\s+)?(?:[a-zA-Z-]+\s+)*(?:panties|panty|thong|bottoms?|boyshorts?|briefs?|skirt|jeans|leggings|shorts|skort|pants)\b.*$", s, re.IGNORECASE)
        if m_norm:
            cand = m_norm.group(1).strip()
            if cand and not any(w in cand.lower() for w in ["panties", "panty", "thong", "boyshorts"]):
                return cand

        # 3. '<top> and matching ...'
        s = re.sub(r"\s+and\s+matching\s+.*$", "", s, flags=re.IGNORECASE).strip()

    # Slot = bottom / bottom_inner: We want only the bottom half
    elif slot in ("bottom", "bottom_inner"):
        # 1. Starts with bottom: e.g. '<bottom> with a matching <top>'
        m_rev = re.search(r"^(.*?boyshorts|.*?panties|.*?thong|.*?briefs?|.*?bottoms?)\s+(?:with|and)\s+.*$", s, re.IGNORECASE)
        if m_rev and not any(w in m_rev.group(1).lower() for w in ["bra", "bralette", "camisole", "top"]):
            return m_rev.group(1).strip()

        # 2. '<top> and/with matching <bottom>'
        m_match = re.search(r"\b(?:and|with)\s+(?:a\s+)?matching\s+([a-zA-Z -]+(?:panties|panty|thong|bottoms?|boyshorts?|briefs?|skirt|pants|jeans|boyshorts))\b", s, re.IGNORECASE)
        if m_match:
            return "matching " + m_match.group(1).strip()

        # 3. '<top> with/and [modifiers] <bottom>'
        m_bottom = re.search(r"\b(?:and|with)\s+(?:a\s+)?((?:[a-zA-Z-]+\s+)*(?:panties|panty|thong|bottoms?|boyshorts?|briefs?))\b", s, re.IGNORECASE)
        if m_bottom:
            b_part = m_bottom.group(1).strip()
            if not b_part.startswith("a "):
                return b_part

        # 4. If has 'bra/bralette' and 'thong/panties/bottoms'
        m_tail = re.search(r"\b((?:[a-zA-Z-]+\s+)*(?:thong|panty|panties|boyshorts?|briefs?|bottoms?))\b", s, re.IGNORECASE)
        if m_tail:
            return "matching " + m_tail.group(1).strip()

    return s


def migrate_catalog():
    print("--- Migrating wardrobe_catalog.json ---")
    if not os.path.exists(BACKUP_CATALOG):
        shutil.copyfile(CATALOG_PATH, BACKUP_CATALOG)
        print(f"Backup created at: {BACKUP_CATALOG}")

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        cat = json.load(f)

    slots = cat.get("slots", {})

    # 1. Clean top_inner
    cleaned_top = []
    seen_top = set()
    for it in slots.get("top_inner", []):
        orig = it.get("name", "")
        cl = decouple_garment("top_inner", orig)
        if cl.lower() not in seen_top:
            seen_top.add(cl.lower())
            new_it = dict(it)
            new_it["name"] = cl
            new_it["prompt"] = cl
            cleaned_top.append(new_it)

    # 2. Clean bottom_inner
    cleaned_bot = []
    seen_bot = set()
    for it in slots.get("bottom_inner", []):
        orig = it.get("name", "")
        cl = decouple_garment("bottom_inner", orig)
        if cl.lower() not in seen_bot:
            seen_bot.add(cl.lower())
            new_it = dict(it)
            new_it["name"] = cl
            new_it["prompt"] = cl
            cleaned_bot.append(new_it)

    slots["top_inner"] = cleaned_top
    slots["bottom_inner"] = cleaned_bot

    cat["slots"] = slots
    if "stats" in cat:
        cat["stats"]["top_inner"] = len(cleaned_top)
        cat["stats"]["bottom_inner"] = len(cleaned_bot)

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(cat, f, indent=2, ensure_ascii=False)

    print(f"Catalog updated! top_inner: {len(cleaned_top)}, bottom_inner: {len(cleaned_bot)}")


def migrate_user_data():
    print("--- Migrating users/ character data ---")
    migrated_files_count = 0
    migrated_items_count = 0

    for u in os.listdir(USERS_DIR):
        up = os.path.join(USERS_DIR, u)
        if not os.path.isdir(up):
            continue
        for c in os.listdir(up):
            cp = os.path.join(up, c)
            if not os.path.isdir(cp):
                continue

            # 1. outfits.json
            outfits_p = os.path.join(cp, "outfits.json")
            if os.path.exists(outfits_p):
                try:
                    with open(outfits_p, "r", encoding="utf-8") as f:
                        d = json.load(f)
                    changed = False
                    for slot, info in d.items():
                        if isinstance(info, dict):
                            orig_name = info.get("name") or info.get("prompt") or ""
                            clean_name = decouple_garment(slot, orig_name)
                            if clean_name != orig_name:
                                info["name"] = clean_name
                                info["prompt"] = clean_name
                                changed = True
                                migrated_items_count += 1
                                print(f"[{u}/{c}/outfits] {slot}: '{orig_name}' -> '{clean_name}'")
                    if changed:
                        with open(outfits_p, "w", encoding="utf-8") as f:
                            json.dump(d, f, indent=2, ensure_ascii=False)
                        migrated_files_count += 1
                except Exception as e:
                    print(f"Error migrating {outfits_p}: {e}")

            # 2. wardrobe_inventory.json
            inv_p = os.path.join(cp, "wardrobe_inventory.json")
            if os.path.exists(inv_p):
                try:
                    with open(inv_p, "r", encoding="utf-8") as f:
                        inv = json.load(f)
                    changed = False
                    if isinstance(inv, list):
                        for item in inv:
                            if isinstance(item, dict):
                                slot = item.get("slot") or ""
                                orig_name = item.get("name") or item.get("prompt") or ""
                                clean_name = decouple_garment(slot, orig_name)
                                if clean_name != orig_name:
                                    item["name"] = clean_name
                                    item["prompt"] = clean_name
                                    changed = True
                                    migrated_items_count += 1
                                    print(f"[{u}/{c}/wardrobe_inv] {slot}: '{orig_name}' -> '{clean_name}'")
                    if changed:
                        with open(inv_p, "w", encoding="utf-8") as f:
                            json.dump(inv, f, indent=2, ensure_ascii=False)
                        migrated_files_count += 1
                except Exception as e:
                    print(f"Error migrating {inv_p}: {e}")

            # 3. turn_metadata.json
            meta_p = os.path.join(cp, "turn_metadata.json")
            if os.path.exists(meta_p):
                try:
                    with open(meta_p, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    changed = False

                    # Check current_datablock
                    cdb = meta.get("current_datablock")
                    if isinstance(cdb, dict):
                        outfits = cdb.get("outfits")
                        if isinstance(outfits, dict):
                            for slot, info in outfits.items():
                                if isinstance(info, dict):
                                    orig_name = info.get("name") or info.get("prompt") or ""
                                    clean_name = decouple_garment(slot, orig_name)
                                    if clean_name != orig_name:
                                        info["name"] = clean_name
                                        info["prompt"] = clean_name
                                        changed = True
                        inv_w = cdb.get("inventory_wardrobe")
                        if isinstance(inv_w, list):
                            for item in inv_w:
                                if isinstance(item, dict):
                                    slot = item.get("slot") or ""
                                    orig_name = item.get("name") or item.get("prompt") or ""
                                    clean_name = decouple_garment(slot, orig_name)
                                    if clean_name != orig_name:
                                        item["name"] = clean_name
                                        item["prompt"] = clean_name
                                        changed = True

                    # Check turn_records
                    for rec in meta.get("turn_records", []):
                        if isinstance(rec, dict) and isinstance(rec.get("datablock"), dict):
                            db = rec["datablock"]
                            outfits = db.get("outfits")
                            if isinstance(outfits, dict):
                                for slot, info in outfits.items():
                                    if isinstance(info, dict):
                                        orig_name = info.get("name") or info.get("prompt") or ""
                                        clean_name = decouple_garment(slot, orig_name)
                                        if clean_name != orig_name:
                                            info["name"] = clean_name
                                            info["prompt"] = clean_name
                                            changed = True
                            inv_w = db.get("inventory_wardrobe")
                            if isinstance(inv_w, list):
                                for item in inv_w:
                                    if isinstance(item, dict):
                                        slot = item.get("slot") or ""
                                        orig_name = item.get("name") or item.get("prompt") or ""
                                        clean_name = decouple_garment(slot, orig_name)
                                        if clean_name != orig_name:
                                            item["name"] = clean_name
                                            item["prompt"] = clean_name
                                            changed = True

                    if changed:
                        with open(meta_p, "w", encoding="utf-8") as f:
                            json.dump(meta, f, indent=2, ensure_ascii=False)
                        migrated_files_count += 1
                        print(f"[{u}/{c}/turn_metadata] Migrated active snapshot & turn records.")
                except Exception as e:
                    print(f"Error migrating {meta_p}: {e}")

    print(f"Migration complete! Files modified: {migrated_files_count}, Items decoupled: {migrated_items_count}")


if __name__ == "__main__":
    migrate_catalog()
    migrate_user_data()
