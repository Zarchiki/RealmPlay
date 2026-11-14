# -*- coding: utf-8 -*-
"""
EVA Set-Theoretic & Logical Operator Engine for RealmPlay (`logic_set_engine.py`)
=================================================================================
Implements formal Set Algebra (`UNION`, `INTERSECTION`, `SUBTRACT`/`DIFFERENCE`,
`SYMMETRIC_DIFF`, `COMPLEMENT`) and Logical Operators (`IF`, `ELIF`, `ELSE`,
`AND`, `OR`, `NOT`) across RealmPlay's:
1. Context & Knowledge Node Graph Router (with Spreading Activation)
2. Ordered Visual / Danbooru Tag Set Algebra (preserving insertion order while
   enforcing set union, intersection, difference, and universe complement)
3. Wardrobe Slot Set Algebra (active set, blocked set, allowed transitions,
   diff, and complement)
4. Markdown Conditional Rule Specification (`IF / ELSE / AND / OR / Set Ops`)
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union


# ===========================================================================
# 1. ORDERED TAG SET ALGEBRA (UNION, INTERSECTION, SUBTRACT, DIFF, COMPLEMENT)
# ===========================================================================

class OrderedTagSet:
    """Case-insensitive, order-preserving Set of Danbooru / visual / state tags.

    Supports full Set Algebra:
    - `union` (`|`): $A \\cup B$ — combine tags without case-insensitive duplicates
    - `intersection` (`&`): $A \\cap B$ — keep only tags present in both sets
    - `subtract` / `difference` (`-`): $A \\setminus B$ — remove tags in $B$ from $A$
    - `symmetric_diff` / `diff` (`^`): $A \\triangle B = (A \\setminus B) \\cup (B \\setminus A)$
    - `complement` (`~` against a `universe`): $U \\setminus A$
    """

    def __init__(self, items: Optional[Union[str, Iterable[str], "OrderedTagSet"]] = None) -> None:
        self._items: List[str] = []
        self._keys: Set[str] = set()
        if items is not None:
            self._extend(items)

    @staticmethod
    def _split_raw(raw: Union[str, Iterable[str], "OrderedTagSet"]) -> List[str]:
        if isinstance(raw, OrderedTagSet):
            return list(raw._items)
        if isinstance(raw, str):
            return [chunk.strip(" .\t\r\n") for chunk in re.split(r"[,;\n|]+", raw) if chunk.strip(" .\t\r\n")]
        result: List[str] = []
        for elem in raw:
            if isinstance(elem, str):
                for sub in re.split(r"[,;\n|]+", elem):
                    clean = sub.strip(" .\t\r\n")
                    if clean:
                        result.append(clean)
        return result

    def _extend(self, items: Union[str, Iterable[str], "OrderedTagSet"]) -> None:
        for tag in self._split_raw(items):
            key = tag.casefold()
            if key and key not in self._keys:
                self._keys.add(key)
                self._items.append(tag)

    def add(self, tag: str) -> "OrderedTagSet":
        self._extend(tag)
        return self

    def union(self, *others: Union[str, Iterable[str], "OrderedTagSet"]) -> "OrderedTagSet":
        """Set Union ($A \\cup B$): combine all unique tags in deterministic order."""
        out = OrderedTagSet(self)
        for other in others:
            out._extend(other)
        return out

    def intersection(self, *others: Union[str, Iterable[str], "OrderedTagSet"]) -> "OrderedTagSet":
        """Set Intersection ($A \\cap B$): retain only tags whose normalized key exists in all sets."""
        other_key_sets = [OrderedTagSet(o)._keys for o in others]
        if not other_key_sets:
            return OrderedTagSet(self)
        common_keys = set(self._keys).intersection(*other_key_sets)
        return OrderedTagSet(t for t in self._items if t.casefold() in common_keys)

    def subtract(self, *others: Union[str, Iterable[str], "OrderedTagSet"]) -> "OrderedTagSet":
        """Set Subtraction / Relative Complement ($A \\setminus B$): remove any tag present in `others`."""
        remove_keys: Set[str] = set()
        for other in others:
            remove_keys.update(OrderedTagSet(other)._keys)
        return OrderedTagSet(t for t in self._items if t.casefold() not in remove_keys)

    # Alias for standard set terminology
    difference = subtract

    def diff(self, other: Union[str, Iterable[str], "OrderedTagSet"]) -> "OrderedTagSet":
        """Symmetric Difference ($A \\triangle B = (A \\setminus B) \\cup (B \\setminus A)$)."""
        other_set = OrderedTagSet(other)
        left_only = self.subtract(other_set)
        right_only = other_set.subtract(self)
        return left_only.union(right_only)

    symmetric_difference = diff

    def complement(self, universe: Union[str, Iterable[str], "OrderedTagSet"]) -> "OrderedTagSet":
        """Set Complement ($A^c = U \\setminus A$) relative to the given `universe` $U$."""
        return OrderedTagSet(universe).subtract(self)

    def subtract_patterns(self, patterns: Sequence[Union[str, re.Pattern[str]]]) -> "OrderedTagSet":
        """Set Subtraction by regex/substring predicates: $A \\setminus \\{x \\in A \\mid P(x)\\}$."""
        compiled = [re.compile(p, re.I) if isinstance(p, str) else p for p in patterns]
        kept = [t for t in self._items if not any(rx.search(t) for rx in compiled)]
        return OrderedTagSet(kept)

    def filter_by(self, predicate: Callable[[str], bool]) -> "OrderedTagSet":
        """Set Comprehension ($\\{x \\in A \\mid P(x)\\}$)."""
        return OrderedTagSet(t for t in self._items if predicate(t))

    # Python operator overloads
    def __or__(self, other: Union[str, Iterable[str], "OrderedTagSet"]) -> "OrderedTagSet":
        return self.union(other)

    def __and__(self, other: Union[str, Iterable[str], "OrderedTagSet"]) -> "OrderedTagSet":
        return self.intersection(other)

    def __sub__(self, other: Union[str, Iterable[str], "OrderedTagSet"]) -> "OrderedTagSet":
        return self.subtract(other)

    def __xor__(self, other: Union[str, Iterable[str], "OrderedTagSet"]) -> "OrderedTagSet":
        return self.diff(other)

    def __contains__(self, item: str) -> bool:
        return str(item or "").strip().casefold() in self._keys

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def __iter__(self):
        return iter(self._items)

    def to_list(self) -> List[str]:
        return list(self._items)

    def to_prompt(self, sep: str = ", ") -> str:
        return sep.join(self._items)

    def __repr__(self) -> str:
        return f"OrderedTagSet({self._items!r})"


# Functional helpers for Set Operations
def set_union(*sources: Union[str, Iterable[str], OrderedTagSet]) -> OrderedTagSet:
    return OrderedTagSet().union(*sources)


def set_intersection(first: Union[str, Iterable[str], OrderedTagSet], *others: Union[str, Iterable[str], OrderedTagSet]) -> OrderedTagSet:
    return OrderedTagSet(first).intersection(*others)


def set_subtract(source: Union[str, Iterable[str], OrderedTagSet], *forbidden: Union[str, Iterable[str], OrderedTagSet]) -> OrderedTagSet:
    return OrderedTagSet(source).subtract(*forbidden)


def set_diff(left: Union[str, Iterable[str], OrderedTagSet], right: Union[str, Iterable[str], OrderedTagSet]) -> OrderedTagSet:
    return OrderedTagSet(left).diff(right)


def set_complement(subset: Union[str, Iterable[str], OrderedTagSet], universe: Union[str, Iterable[str], OrderedTagSet]) -> OrderedTagSet:
    return OrderedTagSet(subset).complement(universe)


# ===========================================================================
# 2. LOGICAL OPERATORS ENGINE (IF, ELIF, ELSE, AND, OR, NOT)
# ===========================================================================

def logic_and(*conditions: Any) -> bool:
    """Logical Conjunction (`AND`): True iff all conditions evaluate to True."""
    return all(bool(c) for c in conditions)


def logic_or(*conditions: Any) -> bool:
    """Logical Disjunction (`OR`): True iff at least one condition evaluates to True."""
    return any(bool(c) for c in conditions)


def logic_not(condition: Any) -> bool:
    """Logical Negation (`NOT` / Complement of boolean truth value)."""
    return not bool(condition)


def logic_if_else(condition: Any, then_val: Any, else_val: Any = None) -> Any:
    """Conditional Branch (`IF condition THEN then_val ELSE else_val`)."""
    res = then_val if bool(condition) else else_val
    return res() if callable(res) else res


def evaluate_if_elif_else(
    branches: Sequence[Tuple[Any, Any]],
    default_else: Any = None,
) -> Any:
    """Deterministic `IF ... ELIF ... ELSE` chain evaluator."""
    for cond, outcome in branches:
        triggered = cond() if callable(cond) else bool(cond)
        if triggered:
            return outcome() if callable(outcome) else outcome
    return default_else() if callable(default_else) else default_else


def matches_query_logic(
    text: str,
    *,
    or_keywords: Sequence[str] = (),
    and_conditions: Sequence[Sequence[str]] = (),
    not_keywords: Sequence[str] = (),
) -> Dict[str, Any]:
    """Evaluate `OR`, `AND`, and `NOT` (Complement) keyword logic against `text`."""
    folded = (text or "").casefold()
    negated = [kw for kw in not_keywords if kw.casefold() in folded]
    if negated:
        return {"matched": False, "or_hits": [], "and_hits": [], "blocked_by_not": negated}

    or_hits = [kw for kw in or_keywords if kw.casefold() in folded]
    and_hits = [
        list(group)
        for group in and_conditions
        if group and all(tok.casefold() in folded for tok in group)
    ]
    return {
        "matched": logic_or(bool(or_hits), bool(and_hits)),
        "or_hits": or_hits,
        "and_hits": and_hits,
        "blocked_by_not": [],
    }


# ===========================================================================
# 3. EVA-STYLE NODE LOGIC & SPREADING ACTIVATION ROUTER
# ===========================================================================

REALMPLAY_LOGIC_NODE_GRAPH: Dict[str, Dict[str, Any]] = {
    "memory": {
        "or_keywords": [
            "memory", "remember", "relationship", "secret", "promise", "history", "past",
            "จำ", "จำได้ไหม", "จำเรื่อง", "เคย", "อดีต", "ประวัติ", "สัญญา", "ความลับ", "ความสัมพันธ์", "ชื่ออะไร", "ของโปรด", "แพ้",
        ],
        "and_conditions": [
            ["จำ", "ได้ไหม"], ["เรื่อง", "ของเรา"], ["สัญญา", "กัน"], ["ความ", "ลับ"], ["เคย", "บอก"], ["ชอบ", "กิน"],
        ],
        "not_keywords": ["forget this turn only"],
        "if_else": {
            "if_present": ["จำได้ไหม", "จำเรื่อง", "สัญญาของเรา", "ความลับ", "remember when", "remember our"],
            "then_boost": 25.0,
            "else_boost": 0.0,
        },
        "links": ["emotion"],
        "weight": 0.65,
    },
    "wardrobe": {
        "or_keywords": [
            "outfit", "wardrobe", "clothes", "wearing", "dress", "undress", "strip", "remove", "bra", "panties", "skirt", "shirt",
            "แต่งตัว", "ชุด", "เสื้อ", "กางเกง", "กระโปรง", "บรา", "ชั้นใน", "กางเกงใน", "แพนตี้", "ถอด", "ใส่", "สวม", "แก้ผ้า", "เปลือย", "ปลดกระดุม",
        ],
        "and_conditions": [
            ["ถอด", "เสื้อ"], ["ถอด", "กางเกง"], ["ถอด", "ชุด"], ["ใส่", "ชุด"], ["เปลี่ยน", "ชุด"], ["ปลด", "กระดุม"], ["แก้", "ผ้า"], ["เลิก", "กระโปรง"],
        ],
        "not_keywords": [],
        "if_else": {
            "if_present": ["ใส่ชุดอะไร", "ถอดหมด", "แก้ผ้า", "เปลี่ยนชุด", "เปลือย", "what are you wearing", "naked", "nude"],
            "then_boost": 25.0,
            "else_boost": 0.0,
        },
        "links": ["appearance", "h_mode"],
        "weight": 0.75,
    },
    "appearance": {
        "or_keywords": [
            "appearance", "look", "face", "eyes", "hair", "body", "figure", "skin", "selfie", "photo", "image",
            "รูปลักษณ์", "หน้าตา", "ลักษณะ", "สีตา", "ทรงผม", "รูปร่าง", "ผิว", "ขอดู", "ถ่ายรูป", "เซลฟี่", "รูป", "ภาพ",
        ],
        "and_conditions": [
            ["หน้าตา", "ยังไง"], ["สี", "ตา"], ["ถ่าย", "รูป"], ["ขอ", "ดู"],
        ],
        "not_keywords": [],
        "if_else": {
            "if_present": ["หน้าตาเป็นยังไง", "รูปลักษณ์เป็น", "what do you look like", "ถ่ายรูป", "เซลฟี่", "ขอรูป"],
            "then_boost": 25.0,
            "else_boost": 0.0,
        },
        "links": ["wardrobe", "emotion"],
        "weight": 0.70,
    },
    "emotion": {
        "or_keywords": [
            "emotion", "feel", "feeling", "angry", "sad", "happy", "afraid", "shy", "blush", "love", "care", "tired", "stressed",
            "กลัว", "โกรธ", "เศร้า", "ดีใจ", "เขิน", "อาย", "รู้สึก", "อารมณ์", "เหนื่อย", "เครียด", "เหงา", "คิดถึง", "ปลอบ", "ร้องไห้",
        ],
        "and_conditions": [
            ["รู้สึก", "ยังไง"], ["ทำไม", "โกรธ"], ["ทำไม", "เศร้า"], ["เหนื่อย", "จัง"], ["กอด", "หน่อย"], ["ใจ", "เต้น"],
        ],
        "not_keywords": [],
        "if_else": {
            "if_present": ["รู้สึกยังไง", "อารมณ์เป็นยังไง", "how do you feel", "เหนื่อย", "คิดถึง", "ปลอบ"],
            "then_boost": 20.0,
            "else_boost": 0.0,
        },
        "links": ["memory"],
        "weight": 0.65,
    },
    "story_time": {
        "or_keywords": [
            "time", "date", "weather", "morning", "night", "evening", "afternoon", "sleep", "sleepy", "bedtime", "tired", "exhausted", "wake", "good morning", "good night",
            "เวลา", "กี่โมง", "วัน", "อากาศ", "เช้า", "สาย", "บ่าย", "เย็น", "ค่ำ", "ดึก", "กลางคืน",
            "ง่วง", "ง่วงนอน", "เข้านอน", "ไปนอน", "อยากนอน", "เหนื่อย", "เพลีย", "ฝันดี", "อรุณสวัสดิ์", "ตื่นนอน",
        ],
        "and_conditions": [
            ["กี่", "โมง"], ["วัน", "อะไร"], ["อากาศ", "ยังไง"], ["ง่วง", "นอน"], ["อยาก", "นอน"], ["ไป", "นอน"], ["เหนื่อย", "อยากพัก"],
        ],
        "not_keywords": [],
        "if_else": {
            "if_present": [
                "ตอนนี้กี่โมง", "วันนี้วันอะไร", "what time is it", "ง่วงนอน", "เข้านอน", "ไปนอนกัน", "ฝันดี", "อรุณสวัสดิ์",
                "want to sleep", "so tired", "go to bed", "good morning", "good night",
            ],
            "then_boost": 25.0,
            "else_boost": 0.0,
        },
        "links": [],
        "weight": 0.55,
    },
    "location": {
        "or_keywords": [
            "location", "where", "place", "room", "go to", "move to", "walk to", "head to", "arrive",
            "ที่ไหน", "อยู่ที่ไหน", "ไปที่", "ย้ายไป", "พาไป", "เดินไป", "เข้าห้อง", "ออกไป", "ห้องนอน", "ห้องน้ำ", "ห้องนั่งเล่น", "ห้องครัว", "ระเบียง",
        ],
        "and_conditions": [
            ["อยู่", "ที่ไหน"], ["ไป", "ที่ไหน"], ["พา", "ไป"], ["ย้าย", "ไป"], ["เข้า", "ห้อง"],
        ],
        "not_keywords": [],
        "if_else": {
            "if_present": ["อยู่ที่ไหน", "ที่นี่ที่ไหน", "where are we", "พาไปที่", "ย้ายไปที่", "ไปที่ห้อง"],
            "then_boost": 25.0,
            "else_boost": 0.0,
        },
        "links": [],
        "weight": 0.55,
    },
    "h_mode": {
        "or_keywords": [
            "sex", "intimate", "touch", "kiss", "caress", "lick", "suck", "penetrate", "thrust", "moan", "climax", "orgasm",
            "จูบ", "กอด", "ซุกไซร้", "ลูบไล้", "คลึง", "บีบ", "ดูด", "เลีย", "อม", "สอดใส่", "กระแทก", "ขย่ม", "ขึ้นคร่อม", "เสียว", "คราง", "แตก", "เสร็จ",
        ],
        "and_conditions": [
            ["จูบ", "ปาก"], ["ลูบ", "ขา"], ["สอด", "ใส่"], ["ขึ้น", "ขย่ม"], ["อม", "ลำเอ็น"], ["ดูด", "นม"],
        ],
        "not_keywords": ["หยุดเดี๋ยวนี้", "พอแล้วหยุด", "ไม่เอาแล้วหยุด"],
        "if_else": {
            "if_present": ["สอดใส่", "ขย่ม", "อมควย", "อมลำเอ็น", "เลียหี", "เสียว", "คราง", "แตกใน"],
            "then_boost": 30.0,
            "else_boost": 0.0,
        },
        "links": ["wardrobe", "emotion", "appearance"],
        "weight": 0.75,
    },
}


def evaluate_node_logic(node_name: str, meta: Dict[str, Any], query_text: str) -> Dict[str, Any]:
    """Evaluate `OR`, `AND`, `NOT` (Complement), and `IF-ELSE` logic for a context/knowledge node.

    - `NOT` (Complement Guard): If any `not_keywords` match, score is immediately `0.0`.
    - `OR` (Disjunction): `+10.0` per matched keyword in `or_keywords`.
    - `AND` (Conjunction): `+15.0` per matched tuple in `and_conditions` where ALL tokens are present.
    - `IF-ELSE` (Conditional Branching): If any `if_present` phrase matches -> `+then_boost`, else -> `+else_boost`.
    """
    q_lower = (query_text or "").casefold()
    logic_res = matches_query_logic(
        q_lower,
        or_keywords=meta.get("or_keywords", ()),
        and_conditions=meta.get("and_conditions", ()),
        not_keywords=meta.get("not_keywords", ()),
    )
    if logic_res["blocked_by_not"]:
        return {
            "node": node_name,
            "raw_score": 0.0,
            "legacy_score": 0,
            "matched": [],
            "or_hits": [],
            "and_hits": [],
            "if_triggered": False,
            "blocked_by_not": logic_res["blocked_by_not"],
        }

    raw_score = float(len(logic_res["or_hits"]) * 10.0 + len(logic_res["and_hits"]) * 15.0)
    if_else = meta.get("if_else") or {}
    if_present = if_else.get("if_present") or ()
    if_triggered = any(tok.casefold() in q_lower for tok in if_present)
    raw_score += logic_if_else(
        if_triggered,
        float(if_else.get("then_boost", 15.0)),
        float(if_else.get("else_boost", 0.0)),
    )

    # Concise short query boost (e.g. "อารมณ์?", "ชุด?")
    if logic_res["or_hits"] and len(q_lower.strip()) <= 20:
        raw_score = max(raw_score, 20.0)

    matched_terms = OrderedTagSet(logic_res["or_hits"]).union(
        ["+".join(g) for g in logic_res["and_hits"]],
        [tok for tok in if_present if tok.casefold() in q_lower],
    ).to_list()

    # Map raw_score to legacy threshold scale (where >= 2 activates the node)
    legacy_score = int(round(raw_score / 10.0))
    return {
        "node": node_name,
        "raw_score": raw_score,
        "score": legacy_score,
        "matched": matched_terms,
        "or_hits": logic_res["or_hits"],
        "and_hits": logic_res["and_hits"],
        "if_triggered": if_triggered,
        "blocked_by_not": [],
    }


def evaluate_graph_with_spreading_activation(
    query_text: str,
    graph: Optional[Dict[str, Dict[str, Any]]] = None,
    *,
    activation_threshold: float = 15.0,
) -> Dict[str, Dict[str, Any]]:
    """Evaluate all nodes with `AND / OR / IF-ELSE` and propagate activation along `links`.

    Also computes Set Operations over node sets:
    - `direct_active_set`: $D = \\{n \\mid \\text{raw\\_score}(n) \\ge \\tau\\}$
    - `propagated_active_set`: $P = \\{n \\mid \\text{total\\_score}(n) \\ge \\tau\\}$
    - `spreading_diff_set`: $P \\setminus D$ (nodes activated purely via synaptic graph links)
    - `inactive_complement_set`: $U \\setminus P$ (complement relative to universe $U$ of all graph nodes)
    """
    g = graph or REALMPLAY_LOGIC_NODE_GRAPH
    universe = OrderedTagSet(g.keys())
    evaluations: Dict[str, Dict[str, Any]] = {}

    for node_name, meta in g.items():
        evaluations[node_name] = evaluate_node_logic(node_name, meta, query_text)
        evaluations[node_name]["propagated_score"] = evaluations[node_name]["raw_score"]
        evaluations[node_name]["activated_by"] = []

    # Spreading Activation along synaptic links: IF direct_score > 0 THEN propagate(score * weight)
    for node_name, ev in list(evaluations.items()):
        base_score = ev["raw_score"]
        if base_score <= 0:
            continue
        meta = g.get(node_name) or {}
        weight = float(meta.get("weight", 0.6))
        for linked in meta.get("links", ()):
            if linked in evaluations and not evaluations[linked]["blocked_by_not"]:
                boost = round(base_score * weight, 2)
                evaluations[linked]["propagated_score"] = round(
                    evaluations[linked]["propagated_score"] + boost, 2
                )
                evaluations[linked]["activated_by"].append(f"{node_name}(+{boost})")
                evaluations[linked]["score"] = max(
                    evaluations[linked]["score"],
                    int(round(evaluations[linked]["propagated_score"] / 10.0)),
                )

    direct_set = OrderedTagSet(n for n, ev in evaluations.items() if ev["raw_score"] >= activation_threshold)
    active_set = OrderedTagSet(n for n, ev in evaluations.items() if ev["propagated_score"] >= activation_threshold)
    spreading_only = active_set.subtract(direct_set)
    complement_set = active_set.complement(universe)

    for n, ev in evaluations.items():
        ev["set_membership"] = {
            "in_direct_set": n in direct_set,
            "in_active_union": n in active_set,
            "in_spreading_diff": n in spreading_only,
            "in_inactive_complement": n in complement_set,
        }
    return evaluations


# ===========================================================================
# 4. WARDROBE & VISUAL SLOT SET OPERATIONS
# ===========================================================================

WARDROBE_UNIVERSE_SLOTS = OrderedTagSet([
    "outer", "outer_outfit", "top", "top_outfit", "top_inner", "bra",
    "bottom", "bottom_inner", "panties", "socks", "shoes", "head",
    "head_acc", "neck_acc", "hand_acc", "leg_acc", "accessory", "accessories",
])


def compute_wardrobe_slot_sets(outfits: Optional[Dict[str, Any]]) -> Dict[str, OrderedTagSet]:
    """Compute Set Algebra over a character's `outfits` state dictionary.

    Returns:
    - `universe`: $U$ — all standard wardrobe slots
    - `defined_slots`: $D$ — slots present in `outfits` with a prompt
    - `active_slots`: $A \\subseteq D$ — currently worn (`active=True`) slots
    - `removed_complement`: $D \\setminus A$ — known garments currently taken off (`active=False`)
    - `unequipped_complement`: $U \\setminus A$ — all slots in $U$ not currently worn
    - `active_prompts`: OrderedTagSet of prompt strings for $A$
    - `removed_prompts`: OrderedTagSet of prompt strings for $D \\setminus A$ (used for Set Subtraction from image prompts!)
    """
    outfits = outfits if isinstance(outfits, dict) else {}
    defined = OrderedTagSet()
    active = OrderedTagSet()
    active_prompts = OrderedTagSet()
    removed_prompts = OrderedTagSet()

    for raw_slot, val in outfits.items():
        slot = str(raw_slot or "").strip().casefold()
        if not slot or slot == "naked":
            continue
        if isinstance(val, dict):
            prompt = str(val.get("prompt") or val.get("name") or "").strip()
            is_act = bool(val.get("active", False)) and bool(prompt)
            if prompt:
                defined.add(slot)
                if is_act:
                    active.add(slot)
                    active_prompts.add(prompt)
                else:
                    removed_prompts.add(prompt)
        elif isinstance(val, str) and val.strip():
            defined.add(slot)
            active.add(slot)
            active_prompts.add(val.strip())
        elif isinstance(val, bool):
            defined.add(slot)
            if val:
                active.add(slot)

    # Ensure removed_prompts never subtracts a tag that is still worn in another active slot:
    # Effective Forbidden Tags = RemovedPrompts \ ActivePrompts
    strict_removed_prompts = removed_prompts.subtract(active_prompts)

    return {
        "universe": WARDROBE_UNIVERSE_SLOTS,
        "defined_slots": defined,
        "active_slots": active,
        "removed_complement": defined.subtract(active),       # D \ A
        "unequipped_complement": active.complement(WARDROBE_UNIVERSE_SLOTS),  # U \ A
        "active_prompts": active_prompts,
        "removed_prompts": strict_removed_prompts,            # R \ A
    }


def diff_wardrobe_states(
    before_outfits: Optional[Dict[str, Any]],
    after_outfits: Optional[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """Compute Set Operations between two wardrobe states ($A_{\\text{before}}$ vs $A_{\\text{after}}$):
    - `union_worn`: $A_{\\text{before}} \\cup A_{\\text{after}}$
    - `intersection_kept`: $A_{\\text{before}} \\cap A_{\\text{after}}$
    - `subtracted_removed`: $A_{\\text{before}} \\setminus A_{\\text{after}}$ (newly removed slots)
    - `added_equipped`: $A_{\\text{after}} \\setminus A_{\\text{before}}$ (newly equipped slots)
    - `symmetric_diff_changed`: $A_{\\text{before}} \\triangle A_{\\text{after}}$ (all toggled slots)
    """
    s1 = compute_wardrobe_slot_sets(before_outfits)["active_slots"]
    s2 = compute_wardrobe_slot_sets(after_outfits)["active_slots"]
    return {
        "union_worn": s1.union(s2).to_list(),
        "intersection_kept": s1.intersection(s2).to_list(),
        "subtracted_removed": s1.subtract(s2).to_list(),
        "added_equipped": s2.subtract(s1).to_list(),
        "symmetric_diff_changed": s1.diff(s2).to_list(),
    }
