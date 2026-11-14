"""Server-side wardrobe transition rules for intimate scenes.

The model may describe a scene, but it must not mutate durable clothing state
without an action in the current turn that supports that mutation.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List


STANDARD_SLOTS = {
    "outer", "outer_outfit", "top", "top_outfit", "top_inner", "bra",
    "bottom", "bottom_inner", "panties", "socks", "shoes", "head",
    "head_acc", "neck_acc", "hand_acc", "leg_acc", "accessories", "naked",
}
CLOTHING_SLOTS = {"outer", "outer_outfit", "top", "top_outfit", "top_inner", "bra", "bottom", "bottom_inner", "panties"}


CORE_SLOTS = {"outer", "top", "bottom", "top_inner", "bottom_inner", "shoes", "socks", "accessory", "head", "head_acc", "neck_acc", "hand_acc", "leg_acc"}
LIGHT_SLOTS = {"outer", "shoes", "socks", "accessory", "head", "head_acc", "neck_acc", "hand_acc", "leg_acc"}

REMOVE_CUES = (
    "ถอด", "ปลด", "รูดลง", "เลิก", "เปิดกระดุม", "เปิดซิป", "ดึงออก", "เปลื้อง",
    "undress", "strip", "unbutton", "unzip", "take off", "takes off", "removed", "removes", "remove ", "slips off",
)
RESTORE_CUES = (
    "ใส่", "สวม", "แต่งตัว", "คลุม", "ติดกระดุม", "รูดขึ้น", "จัดเสื้อ", "ห่อตัว",
    "put on", "puts on", "get dressed", "dress", "wear ", "wears ", "cover up", "button up",
)

SLOT_CUES = {
    "outer": ("jacket", "coat", "cloak", "blazer", "cardigan", "hoodie", "เสื้อนอก", "เสื้อคลุม", "แจ็กเก็ต", "โค้ท"),
    "top": ("shirt", "blouse", "t-shirt", "tshirt", "dress", "gown", "เสื้อ", "เดรส", "ชุดกระโปรง"),
    "bottom": ("skirt", "pants", "trousers", "shorts", "jeans", "กระโปรง", "กางเกง"),
    "top_inner": ("bra", "bralette", "camisole", "เสื้อชั้นใน", "บรา"),
    "bottom_inner": ("panties", "underwear", "panty", "กางเกงใน", "แพนตี้"),
    "shoes": ("shoe", "boot", "sandal", "รองเท้า", "บูต"),
    "socks": ("sock", "stocking", "ถุงเท้า", "ถุงน่อง"),
    "head": ("hat", "cap", "hood", "headband", "หมวก", "ที่คาดผม"),
    "head_acc": ("hair ribbon", "hairband", "hairpin", "ริบบิ้นผม", "กิ๊บ", "โบว์ผม"),
    "neck_acc": ("necklace", "choker", "scarf", "tie", "สร้อย", "ผ้าพันคอ", "เนคไท"),
    "hand_acc": ("glove", "ring", "bracelet", "wristband", "ถุงมือ", "แหวน", "กำไล"),
    "leg_acc": ("garter", "leg strap", "thigh strap", "สายรัดต้นขา"),
    "accessory": ("glove", "scarf", "necklace", "choker", "belt", "ถุงมือ", "ผ้าพันคอ", "สร้อย", "เข็มขัด"),
}

ALL_CLOTHING_CUES = (
    "undress completely", "remove all clothes", "take off all clothes", "completely naked",
    "get dressed", "fully dressed", "all clothes", "ถอดเสื้อผ้าหมด", "เปลือยหมด",
    "ถอดให้หมด", "ถอดหมด", "ถอดทั้งหมด", "ถอดทุกอย่าง", "ถอดให้ดูหน่อยทั้งหมดเลย",
    "แก้ผ้า", "แต่งตัวเรียบร้อย", "ใส่เสื้อผ้าครบ",
)

FULL_NUDITY_CUES = (
    "naked", "nude", "undressed", "fully nude", "completely nude", "bare naked", "without clothes",
    "take everything off", "ถอดให้หมด", "ถอดหมด", "ถอดทั้งหมด", "ถอดทุกอย่าง", "ถอดให้ดูหน่อยทั้งหมดเลย",
    "เปลือยกาย", "เปลือยเปล่า", "เปลือยทั้งหมด", "เปลือยหมด", "แก้ผ้า",
)


@dataclass(frozen=True)
class TransitionResult:
    outfits: Dict[str, Any]
    wardrobe_inventory: List[Dict[str, Any]]
    character_inventory: List[Any]
    changed_slots: List[str]


class WardrobeTransition:
    """Single mutation path for every durable wardrobe transition.

    Callers may differ (USER action, CHAR action, UI control, regenerate), but
    they all submit a canonical slot payload here. This class never persists
    state itself; the enclosing chat/UI transaction owns persistence and any
    current/turn-record snapshot.
    """

    @staticmethod
    def apply(state: Dict[str, Any], payload: Dict[str, Any]) -> TransitionResult:
        outfits = deepcopy(state.get("outfits") or {}) if isinstance(state, dict) else {}
        wardrobe_inventory = [dict(item) for item in (state.get("inventory_wardrobe") or []) if isinstance(item, dict)] if isinstance(state, dict) else []
        character_inventory = [dict(item) if isinstance(item, dict) else item for item in ((state.get("inventory") or []) if isinstance(state, dict) else [])]
        if not isinstance(payload, dict):
            return TransitionResult(outfits, wardrobe_inventory, character_inventory, [])

        # Removal obeys the physical layer order, based on the intended final
        # state. One atomic request may still remove every blocking layer at
        # once, regardless of payload ordering. This centralizes the rule for
        # USER actions, CHAR actions, UI toggles, and regenerate.
        outer_worn = WardrobeTransition._any_layer_remains_active(outfits, payload, ("outer", "outer_outfit"))
        top_worn = WardrobeTransition._any_layer_remains_active(outfits, payload, ("top", "top_outfit"))
        # A requested top removal is not effective while outerwear remains.
        # Keep that top as a blocker for its inner layer too; otherwise one
        # payload could incorrectly remove only the bra through both layers.
        if outer_worn and WardrobeTransition._requested_active_layer_removal(outfits, payload, ("top", "top_outfit")):
            top_worn = True
        bottom_worn = WardrobeTransition._bottom_layer_blocks_inner_removal(outfits, payload)
        changed: List[str] = []
        for raw_slot, value in payload.items():
            slot = str(raw_slot or "").casefold().strip()
            if slot not in STANDARD_SLOTS and slot not in outfits:
                continue
            requested_inactive = value is False or (isinstance(value, dict) and value.get("active") is False)
            # Outerwear must come off before a top; a top must come off before
            # its inner layer. Wearing has no inverse prerequisite: a shirt
            # can be put on without a bra, and outerwear can be put on without
            # a top.
            if slot in {"top", "top_outfit"} and requested_inactive and outer_worn:
                continue
            if slot in {"top_inner", "bra"} and requested_inactive and top_worn:
                continue
            # Pants/shorts/jeans block underwear removal; skirts explicitly do
            # not. Neither pants nor skirts require underwear to be worn.
            if slot in {"bottom_inner", "panties"} and requested_inactive and bottom_worn:
                continue
            previous = outfits.get(slot)
            previous_prompt = previous.get("prompt", "") if isinstance(previous, dict) else (str(previous) if isinstance(previous, str) else "")
            if isinstance(value, bool):
                if isinstance(previous, dict) and bool(previous.get("active", False)) != value:
                    outfits[slot] = {**previous, "active": value}
                    changed.append(slot)
                elif isinstance(previous, bool) and previous != value:
                    outfits[slot] = value
                    changed.append(slot)
            elif isinstance(value, str) and value.strip():
                prompt = value.strip()[:150]
                if isinstance(previous, dict) and previous.get("active") and str(previous.get("prompt") or "").casefold() == prompt.casefold():
                    continue
                if previous_prompt and previous_prompt.casefold() != prompt.casefold():
                    WardrobeTransition._store_wardrobe_item(wardrobe_inventory, slot, previous_prompt, "stored")
                outfits[slot] = {"prompt": prompt, "active": True}
                WardrobeTransition._store_wardrobe_item(wardrobe_inventory, slot, prompt, "equipped")
                changed.append(slot)
            elif isinstance(value, dict):
                prompt = str(value.get("prompt") or previous_prompt or "").strip()[:150]
                active = bool(value.get("active", True))
                # Preserve catalog-facing fields (notably `name` and
                # `category`) while the transition engine owns `active` and
                # the prompt used by the renderer.
                next_value = {
                    **({k: deepcopy(v) for k, v in value.items() if k not in {"active", "prompt"}}),
                    "prompt": prompt or slot,
                    "active": active,
                }
                if isinstance(previous, dict) and bool(previous.get("active", False)) == active and str(previous.get("prompt") or "").strip() == next_value["prompt"]:
                    continue
                if previous_prompt and prompt and previous_prompt.casefold() != prompt.casefold():
                    WardrobeTransition._store_wardrobe_item(wardrobe_inventory, slot, previous_prompt, "stored")
                outfits[slot] = next_value
                changed.append(slot)

        if changed:
            WardrobeTransition._sync_naked(outfits)
            WardrobeTransition._return_removed_items(outfits, changed, character_inventory)
            WardrobeTransition._consume_equipped_items(outfits, changed, character_inventory)
            WardrobeTransition._sync_wardrobe_inventory_status(outfits, changed, wardrobe_inventory)
        return TransitionResult(outfits, wardrobe_inventory, character_inventory, changed)

    @staticmethod
    def _any_layer_remains_active(
        outfits: Dict[str, Any], payload: Dict[str, Any], slots: tuple[str, ...],
    ) -> bool:
        """Whether any slot in a layer family is active after this transition."""
        for slot in slots:
            previous = outfits.get(slot)
            active = bool(previous.get("active", False)) if isinstance(previous, dict) else bool(previous)
            requested = payload.get(slot)
            if requested is not None:
                if isinstance(requested, bool):
                    active = requested
                elif isinstance(requested, str):
                    active = bool(requested.strip())
                elif isinstance(requested, dict):
                    active = bool(requested.get("active", True))
            if active:
                return True
        return False

    @staticmethod
    def _requested_active_layer_removal(
        outfits: Dict[str, Any], payload: Dict[str, Any], slots: tuple[str, ...],
    ) -> bool:
        """Whether this payload tries to deactivate a currently worn layer."""
        for slot in slots:
            previous = outfits.get(slot)
            active = bool(previous.get("active", False)) if isinstance(previous, dict) else bool(previous)
            requested = payload.get(slot)
            requested_inactive = requested is False or (
                isinstance(requested, dict) and requested.get("active") is False
            )
            if active and requested_inactive:
                return True
        return False

    @staticmethod
    def _bottom_layer_blocks_inner_removal(outfits: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        """Whether an active trousers/shorts layer remains after this transition."""
        bottom = outfits.get("bottom")
        active = bool(bottom.get("active", False)) if isinstance(bottom, dict) else bool(bottom)
        prompt = str(bottom.get("prompt") or bottom.get("name") or "") if isinstance(bottom, dict) else ""
        requested = payload.get("bottom")
        if requested is not None:
            if isinstance(requested, bool):
                active = requested
            elif isinstance(requested, str) and requested.strip():
                active, prompt = True, requested.strip()
            elif isinstance(requested, dict):
                active = bool(requested.get("active", True))
                prompt = str(requested.get("prompt") or requested.get("name") or prompt)
        if not active:
            return False
        folded = prompt.casefold()
        return any(token in folded for token in (
            "pants", "trousers", "shorts", "jeans", "slacks", "กางเกง",
        )) and "กางเกงใน" not in folded

    @staticmethod
    def _store_wardrobe_item(inventory: List[Dict[str, Any]], slot: str, prompt: str, status: str) -> None:
        existing = next((item for item in inventory if str(item.get("prompt") or "").casefold() == prompt.casefold()), None)
        if existing:
            existing["status"] = status
            return
        inventory.append({"slot": slot, "prompt": prompt, "status": status})

    @staticmethod
    def _sync_naked(outfits: Dict[str, Any]) -> None:
        any_clothes = any(
            isinstance(outfits.get(slot), dict) and outfits[slot].get("active") and str(outfits[slot].get("prompt") or "").strip()
            for slot in CLOTHING_SLOTS
        )
        naked = outfits.get("naked")
        if not any_clothes:
            outfits["naked"] = {**naked, "prompt": str(naked.get("prompt") or "naked"), "active": True} if isinstance(naked, dict) else {"prompt": "naked", "active": True}
        elif isinstance(naked, dict):
            outfits["naked"] = {**naked, "active": False}

    @staticmethod
    def _return_removed_items(outfits: Dict[str, Any], changed: List[str], bag: List[Any]) -> None:
        for slot in changed:
            part = outfits.get(slot)
            if not isinstance(part, dict) or part.get("active", False):
                continue
            prompt = str(part.get("prompt") or part.get("name") or "").strip()
            if not prompt or prompt.casefold() == "naked":
                continue
            existing = next((item for item in bag if isinstance(item, dict) and (
                str(item.get("name") or "").casefold() == prompt.casefold()
                or str(item.get("prompt") or "").casefold() == prompt.casefold()
            )), None)
            if existing:
                existing["qty"] = int(existing.get("qty", 1) or 1) + 1
            else:
                bag.append({"name": prompt, "desc": f"ชุดที่ถอดเก็บจากส่วน {slot}", "slot": slot,
                            "prompt": prompt, "qty": 1, "type": "wearable"})

    @staticmethod
    def _consume_equipped_items(outfits: Dict[str, Any], changed: List[str], bag: List[Any]) -> None:
        """Move one matching wearable from the character bag into an active slot."""
        for slot in changed:
            part = outfits.get(slot)
            if not isinstance(part, dict) or not part.get("active", False):
                continue
            prompt = str(part.get("prompt") or part.get("name") or "").strip()
            if not prompt:
                continue
            for index, item in enumerate(bag):
                if not isinstance(item, dict) or str(item.get("type") or "").casefold() != "wearable":
                    continue
                same_item = (
                    str(item.get("name") or "").casefold() == prompt.casefold()
                    or str(item.get("prompt") or "").casefold() == prompt.casefold()
                )
                if not same_item:
                    continue
                quantity = int(item.get("qty", 1) or 1) - 1
                if quantity > 0:
                    item["qty"] = quantity
                else:
                    bag.pop(index)
                break

    @staticmethod
    def _sync_wardrobe_inventory_status(outfits: Dict[str, Any], changed: List[str], inventory: List[Dict[str, Any]]) -> None:
        for slot in changed:
            part = outfits.get(slot)
            if not isinstance(part, dict):
                continue
            prompt = str(part.get("prompt") or part.get("name") or "").strip()
            if not prompt:
                continue
            status = "equipped" if part.get("active", False) else "stored"
            WardrobeTransition._store_wardrobe_item(inventory, slot, prompt, status)


def _has_cue(text: str, cues: tuple[str, ...]) -> bool:
    folded = (text or "").casefold()
    return any(cue in folded for cue in cues)


def _active_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict) and "active" in value:
        return bool(value["active"])
    # A string is a new equipped clothing item.
    if isinstance(value, str) and value.strip():
        return True
    return None


def _slot_is_supported(slot: str, evidence: str) -> bool:
    folded = (evidence or "").casefold()
    return any(cue in folded for cue in ALL_CLOTHING_CUES) or any(
        cue in folded for cue in SLOT_CUES.get(slot, ())
    )


def strip_for_full_nudity(outfits: Dict[str, Any], evidence: str) -> Dict[str, bool]:
    """Remove every currently known garment when the turn explicitly says fully naked."""
    folded = (evidence or "").casefold()
    thai_full_nudity = "เปลือย" in folded and not any(
        partial in folded for partial in ("เปลือยอก", "เปลือยท่อนบน", "เปลือยช่วงบน")
    )
    if not thai_full_nudity and not any(cue in folded for cue in FULL_NUDITY_CUES):
        return {}
    updates: Dict[str, bool] = {}
    for raw_slot, value in (outfits or {}).items():
        slot = str(raw_slot or "").casefold().strip()
        if slot not in CORE_SLOTS:
            continue
        active = _active_value(value)
        if active:
            updates[slot] = False
    return updates


def event_updates(outfits: Dict[str, Any], evidence: str) -> Dict[str, bool]:
    """Return state changes caused directly by an unambiguous wardrobe event.

    This is intentionally independent of the model's optional wardrobe block:
    a narrated full-nudity event must toggle the durable wardrobe immediately.
    """
    return strip_for_full_nudity(outfits, evidence)


def allowed_update(
    stage: str,
    requested: Dict[str, Any],
    user_text: str = "",
    visible_reply: str = "",
) -> Dict[str, Any]:
    """Return only wardrobe changes justified by this turn and scene stage.

    * normal/intimacy: an explicit action may remove or put on any known slot
    * foreplay/explicit/climax: an explicit action may remove slots, never put
      them back on automatically
    * aftercare: no forced clothing change; explicit actions remain allowed
    """
    if not isinstance(requested, dict):
        return {}
    stage = (stage or "normal").casefold()
    evidence = f"{user_text}\n{visible_reply}"
    removal = _has_cue(evidence, REMOVE_CUES)
    restoration = _has_cue(evidence, RESTORE_CUES)
    accepted: Dict[str, Any] = {}

    for raw_slot, value in requested.items():
        slot = str(raw_slot or "").casefold().strip()
        if slot not in CORE_SLOTS:
            continue
        active = _active_value(value)
        if active is None:
            continue
        # A generic “remove/wear” verb is insufficient: the action must name
        # this garment slot (or explicitly address all clothing) so one action
        # cannot accidentally alter unrelated underwear or accessories.
        if not _slot_is_supported(slot, evidence):
            continue
        if stage in {"normal", "intimacy"}:
            if (not active and removal) or (active and restoration):
                accepted[slot] = value
        elif stage in {"foreplay", "explicit", "climax"}:
            # A direct, user-supported dressing request is a real wardrobe
            # event even during H-mode. Do not block it merely because the
            # stage normally prevents automatic restoration.
            if (not active and removal) or (active and restoration and _has_cue(evidence, ("ช่วย", "กรุณา", "please"))):
                accepted[slot] = value
        elif stage == "aftercare":
            if (not active and removal) or (active and restoration):
                accepted[slot] = value
    return accepted


def restore_for_normal(outfits: Dict[str, Any]) -> Dict[str, bool]:
    """Return only inactive known garments that should be restored on H-Mode exit."""
    restore: Dict[str, bool] = {}
    for raw_slot, value in (outfits or {}).items():
        slot = str(raw_slot or "").casefold().strip()
        if slot == "naked":
            if isinstance(value, dict) and value.get("active"):
                restore[slot] = False
            continue
        if slot not in CORE_SLOTS:
            continue
        if isinstance(value, dict) and value.get("prompt") and not value.get("active"):
            restore[slot] = True
        elif isinstance(value, bool) and not value:
            restore[slot] = True
    return restore


def prompt_rule(stage: str) -> str:
    """Short stage-specific rule for the model; enforcement remains server-side."""
    stage = (stage or "normal").casefold()
    rules = {
        "normal": "Normal: change only the exact garment supported by a dressing or undressing action in this turn.",
        "intimacy": "Intimacy: change only the exact garment supported by a dressing or undressing action in this turn.",
        "foreplay": "Foreplay: a confirmed action may remove the exact garment involved; do not put garments back on automatically.",
        "explicit": "Explicit: a confirmed action may remove the exact garment involved; do not put garments back on automatically.",
        "climax": "Climax: a confirmed action may remove the exact garment involved; do not put garments back on automatically.",
        "aftercare": "Aftercare: do not force a clothing change. Follow only a clear dressing or undressing action.",
    }
    return rules.get(stage, rules["normal"])
