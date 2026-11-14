"""Manual proactive-message dispatch and persistence."""

import time


async def trigger(req, user: str, safe_name, character_card, emit_message) -> dict:
    character = safe_name(req.character_name)
    if req.message:
        state = character_card.get_user_character_state(user, character)
        history = list(state.get("history", []))
        message = {
            "role": "assistant", "content": req.message, "proactive": True,
            "timestamp": time.time(), "emotion": state.get("emotion", "neutral"),
        }
        history.append(message)
        character_card.save_user_character_state(user, character, {"history": history})
        from chat_inbox import summary
        return {"ok": True, "triggered": True, "character": character, "summary": summary(user, character), "message": message}
    sent = await emit_message(user, character)
    from chat_inbox import summary
    return {"ok": sent, "triggered": sent, "character": character, "summary": summary(user, character)}
