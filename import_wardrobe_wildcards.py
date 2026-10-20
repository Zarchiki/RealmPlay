"""Import and index attire wildcards from Stable Diffusion into RealmPlay."""
import os
import shutil
import json
import glob
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WILDCARDS_LOCAL_ROOT = os.path.join(BASE_DIR, "data", "wildcards")
SOURCE_DIR = os.path.join(WILDCARDS_LOCAL_ROOT, "attire")
ROOT_WILDCARDS_DIR = WILDCARDS_LOCAL_ROOT
TARGET_DIR = os.path.join(WILDCARDS_LOCAL_ROOT, "attire")
CATALOG_FILE = os.path.join(BASE_DIR, "data", "wardrobe_catalog.json")


ROOT_CLOTHING_FILES = [
    "bikini.txt",
    "female clothes.txt",
    "female outfit sets.txt",
    "clothes.txt",
    "clothesA.txt",
    "clothesB.txt",
    "dress-state.txt"
]

SLOT_MAPPINGS = [
    # Patterns for outer slot
    (r"(?:jacket|blazer|coat|overfit|parka|outer)", "outer"),
    # Top inner / underwear / bikini
    (r"(?:underwear|swimsuit|bodysuit|bra|bikini)", "top_inner"),
    # Top wear
    (r"(?:shirts_and_topwear|t-shirt|knit|sweater)", "top"),
    # Bottom wear
    (r"(?:pants_and_bottomwear|shorts|jeans)", "bottom"),
    # Footwear & legwear
    (r"(?:shoes_and_footwear|shoes)", "shoes"),
    (r"(?:legs_and_feet|socks|stocking)", "socks"),
    # Head & accessories
    (r"(?:headwear|hat)", "head"),
    (r"(?:neck_and_shoulders|neck|choker|collar)", "neck"),
    (r"(?:limbs|hands|gloves)", "hands"),
    (r"(?:jewelry|accessories)", "accessories"),
    # Complete outfit presets
    (r"(?:one-piece|sundress|wedding|stewardess|korean|luxauly|two-piece|traning|uniform|female outfit sets)", "preset")
]

def classify_item(prompt: str, default_slot: str) -> list:
    """Classify prompt into one or more appropriate slots."""
    p_lower = prompt.lower()
    slots = set()

    # Underwear fine separation
    is_bottom_inner = any(k in p_lower for k in ["panty", "panties", "thong", "brief", "g-string", "boyshort", "bikini bottom", "boxer"])
    is_top_inner = any(k in p_lower for k in ["bra", "bralette", "bikini top", "corset", "camisole", "bustier"])

    if default_slot == "top_inner" or "underwear" in p_lower:
        if is_bottom_inner and is_top_inner:
            slots.add("top_inner")
            slots.add("bottom_inner")
        elif is_bottom_inner:
            slots.add("bottom_inner")
        elif is_top_inner:
            slots.add("top_inner")
        else:
            slots.add("top_inner")
    else:
        slots.add(default_slot)

    return list(slots)

def map_slot(filename: str, rel_path: str) -> str:
    path_lower = (rel_path + " " + filename).lower()
    for pattern, slot in SLOT_MAPPINGS:
        if re.search(pattern, path_lower):
            return slot
    return "accessories"


def run_import():
    print(f"Reading wildcards from: {SOURCE_DIR}")
    if not os.path.exists(SOURCE_DIR):
        print(f"ERROR: Source directory not found: {SOURCE_DIR}")
        return

    os.makedirs(TARGET_DIR, exist_ok=True)
    txt_files = glob.glob(os.path.join(SOURCE_DIR, "**", "*.txt"), recursive=True)
    
    # Add selected root clothing files (including bikini.txt)
    for root_file in ROOT_CLOTHING_FILES:
        full_root_path = os.path.join(ROOT_WILDCARDS_DIR, root_file)
        if os.path.exists(full_root_path) and full_root_path not in txt_files:
            txt_files.append(full_root_path)

    print(f"Found {len(txt_files)} total wildcard files to import.")

    catalog = {
        "slots": {
            "outer": [],
            "top": [],
            "top_inner": [],
            "bottom": [],
            "bottom_inner": [],
            "socks": [],
            "shoes": [],
            "head": [],
            "neck": [],
            "hands": [],
            "accessories": [],
            "preset": []
        },
        "stats": {
            "total_items": 0,
            "total_files": len(txt_files)
        }
    }

    seen_prompts = set()

    for file_path in txt_files:
        rel_path = os.path.relpath(file_path, SOURCE_DIR)
        dest_path = os.path.join(TARGET_DIR, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(file_path, dest_path)

        filename = os.path.basename(file_path)
        base_slot = map_slot(filename, rel_path)
        category_name = os.path.dirname(rel_path) or "General"

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

        for line in lines:
            norm_prompt = line.strip()
            norm_prompt = re.sub(r"\s+", " ", norm_prompt)
            if not norm_prompt:
                continue

            target_slots = classify_item(norm_prompt, base_slot)
            for s in target_slots:
                if s not in catalog["slots"]:
                    s = "accessories"
                catalog["slots"][s].append({
                    "name": norm_prompt,
                    "prompt": norm_prompt,
                    "category": category_name,
                    "file": rel_path
                })
            seen_prompts.add(norm_prompt.lower())

    catalog["stats"]["total_items"] = len(seen_prompts)

    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"Successfully imported {len(seen_prompts)} unique wardrobe items into {CATALOG_FILE}!")
    for slot, items in catalog["slots"].items():
        print(f" - Slot '{slot}': {len(items)} items")

if __name__ == "__main__":
    run_import()
