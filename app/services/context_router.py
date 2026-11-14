"""Context and rule selection independent from API endpoints."""

import re
from typing import Any, Callable, Dict

from .context_intents import score_context_intents
from .context_utils import clip_context, prune_memory_facts


# These rules establish identity, policy, and state boundaries.  They always
# remain first; user ordering may only arrange the remaining reply preferences.
ESSENTIAL_RULE_ORDER = (
    "system_instruction",
    "language_adaptation",
    "self_recognition",
    "content_policy_local_model",
    "prohibitions",
    "proactive_state",
)


def route_context_nodes(
    state: Dict[str, Any], input_text: str, operation: str,
    resolve_outfit_prompt: Callable[[dict], str],
) -> Dict[str, Any]:
    """Return small, explainable context nodes for an LLM/image/TTS operation."""
    intents = score_context_intents(input_text)
    selected_intent = lambda node: intents[node]["score"] >= 2
    selected, reasons = {
        "status": clip_context(state.get("status") or "Normal", 750),
        "situation": clip_context(state.get("scenario") or "Default scene", 520),
    }, {"status": "core continuity", "situation": "core continuity"}
    clock = state.get("time_state") or {}
    clock_text = " | ".join(
        str(clock.get(key) or "").strip()
        for key in ("date", "day", "time", "period", "timezone")
        if str(clock.get(key) or "").strip()
    )
    if clock_text:
        selected["system_time"] = clip_context(clock_text, 120)
        reasons["system_time"] = "fresh host-system clock"
    if clock_text and (operation == "image" or selected_intent("story_time")):
        selected["story_time"] = clip_context(clock_text, 220)
        reasons["story_time"] = (
            "system time requested for image continuity" if operation == "image"
            else f"system time requested; intent score {intents['story_time']['score']}: {', '.join(intents['story_time']['matched'])}"
        )
    detail = state.get("emotion_detail") or {}
    emotion_name = str(detail.get("name") or state.get("emotion") or "neutral").strip().lower()
    if operation == "image":
        selected["emotion"] = emotion_name
        reasons["emotion"] = "image expression"
    elif selected_intent("emotion"):
        emotion_text = emotion_name
        if detail.get("intensity"):
            emotion_text += f" ({detail.get('intensity')}%)"
        if detail.get("cause"):
            emotion_text += f", cause: {detail.get('cause')}"
        selected["emotion"] = clip_context(emotion_text, 180)
        reasons["emotion"] = f"intent score {intents['emotion']['score']}: {', '.join(intents['emotion']['matched'])}"
    if selected_intent("memory"):
        selected["memory"] = clip_context(prune_memory_facts(state.get("memory", ""), max_facts=3), 520)
        reasons["memory"] = f"intent score {intents['memory']['score']}: {', '.join(intents['memory']['matched'])}"
    visual_request = (
        operation == "image"
        or any(term in (input_text or "").casefold() for term in ("รูป", "ภาพ", "image", "photo"))
        or selected_intent("appearance") or selected_intent("wardrobe")
    )
    if visual_request:
        selected["appearance"] = clip_context(state.get("appearance") or "Not specified", 420)
        selected["wardrobe"] = clip_context(resolve_outfit_prompt(state.get("outfits", {})) or "Default attire", 300)
        visual_reason = "image continuity" if operation == "image" else "visual/image intent"
        reasons.update({"appearance": visual_reason, "wardrobe": visual_reason})
    return {"nodes": selected, "reasons": reasons, "intent_scores": intents, "operation": operation}


def route_rule_instructions(
    all_overrides: Dict[str, str], routed_context: Dict[str, Any], input_text: str,
    operation: str = "chat", rule_priority=None,
) -> Dict[str, Any]:
    """Select configured rule blocks that match already-routed context."""
    # Keep this local fallback so the router remains independently testable and
    # usable by small tools that load only this function.
    essential_rule_order = globals().get("ESSENTIAL_RULE_ORDER", (
        "system_instruction", "language_adaptation", "self_recognition",
        "content_policy_local_model", "prohibitions", "proactive_state",
    ))
    nodes = routed_context.get("nodes", {})
    selected = {
        "system_instruction", "language_adaptation", "self_recognition",
        "non_literal_writing", "proactive_character_behavior", "loop_guard",
        "prohibitions", "pronoun", "content_policy_local_model", "proactive_state",
    }
    reasons = {rule: "core visible-reply rule" for rule in selected}
    if "memory" in nodes:
        reasons["proactive_state"] = "memory node selected"
    if "emotion" in nodes:
        selected.update(("emotional_clarity", "expressive_vocalization"))
        reasons.update({"emotional_clarity": "emotion node selected", "expressive_vocalization": "emotion node selected"})
    if "story_time" in nodes:
        selected.add("time_recognition")
        reasons["time_recognition"] = "story-time node selected"
    if "appearance" in nodes or "wardrobe" in nodes:
        selected.update(("image_context", "wardrobe"))
        reasons.update({"image_context": "visual node selected", "wardrobe": "wardrobe/appearance node selected"})
    image_requested = operation == "image" or bool(re.search(
        r"(?:^\s*/image\b|\[\[image\s*:|สร้างรูป|สร้างภาพ|ขอรูป|ขอภาพ|generate (?:an )?image|create (?:an )?image)",
        input_text or "", re.I,
    ))
    if image_requested:
        selected.update(("image_trigger", "image_context", "wardrobe"))
        reasons.update({"image_trigger": "explicit image intent", "image_context": "image operation", "wardrobe": "image operation"})
    if operation == "tts":
        selected.add("tts_dialogue")
        reasons["tts_dialogue"] = "tts operation"
    # Keep saved installations from before the policy rule rename working. The
    # public rule id is deliberately explicit: it is not an image ``nsfw`` tag.
    normalized_overrides = dict(all_overrides or {})
    if (
        not str(normalized_overrides.get("content_policy_local_model") or "").strip()
        and str(normalized_overrides.get("nsfw") or "").strip()
    ):
        normalized_overrides["content_policy_local_model"] = normalized_overrides["nsfw"]
    default_order = [*essential_rule_order, "non_literal_writing", "proactive_character_behavior", "loop_guard", "pronoun"]
    default_order.extend(sorted(selected - set(default_order)))
    movable_priority = [
        rule for rule in (rule_priority or [])
        if isinstance(rule, str) and rule in selected and rule not in essential_rule_order
    ]
    ordered_rule_ids = [*essential_rule_order]
    ordered_rule_ids.extend(dict.fromkeys(movable_priority))
    ordered_rule_ids.extend(rule for rule in default_order if rule in selected and rule not in ordered_rule_ids)
    overrides = {
        rule: normalized_overrides[rule]
        for rule in ordered_rule_ids
        if isinstance(normalized_overrides.get(rule), str) and normalized_overrides[rule].strip()
    }
    return {"overrides": overrides, "rule_ids": ordered_rule_ids, "reasons": reasons}
