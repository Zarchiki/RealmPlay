"""Load visible-message formatting rules without embedding them in the server prompt."""
from pathlib import Path
import json
import re


_SMS_BRACKET = r"\[[A-Za-z0-9_\u0E00-\u0E7F\s]{1,30}\s*:\s*[\s\S]+?\]"
_SMS_MARKERS = (
    "ส่งไลน์", "ทักไลน์", "ในไลน์", "ในแชท", "ส่งแชท", "ส่งข้อความหา",
    "ทักแชท", "คุยไลน์", "texting", "on line", "sms", "chatting",
)
_VOICE_SMS_MARKERS = (
    "voice sms", "voice message", "voice chat", "ข้อความเสียง", "ส่งวอยซ์", "ส่งเสียง", "วอยซ์เมสเสจ",
)
_VOICE_SMS_ARRAY = re.compile(r'^\s*\[\s*"(?:[^"\\]|\\.)*"(?:\s*,\s*"(?:[^"\\]|\\.)*")*\s*\]\s*$', re.S)


def is_sms_input(text: str) -> bool:
    """Whether the newest user turn explicitly uses a phone-message channel."""
    if not text:
        return False
    import re
    value = text.strip()
    if any(marker in value.casefold() for marker in _VOICE_SMS_MARKERS) or _VOICE_SMS_ARRAY.match(value):
        return False
    return bool(re.search(_SMS_BRACKET, value)) or any(marker in value.casefold() for marker in _SMS_MARKERS)


def is_voice_sms_input(text: str) -> bool:
    """Recognize a requested voice-message payload represented as a JSON string array."""
    value = (text or "").strip()
    return bool(_VOICE_SMS_ARRAY.match(value)) or any(marker in value.casefold() for marker in _VOICE_SMS_MARKERS)


def format_sms_reply(reply: str, trigger: str, character: str) -> str:
    """Keep sent messages outside narration and preserve fenced state verbatim."""
    if not reply:
        return reply
    if is_voice_sms_input(trigger):
        parts = re.split(r"(```[\s\S]*?```)", reply)
        for index in range(0, len(parts), 2):
            visible = parts[index].strip()
            if not visible:
                continue
            if _VOICE_SMS_ARRAY.match(visible):
                continue
            quoted = re.findall(r'"([^"\n]+)"|“([^”\n]+)”', visible)
            messages = [next((item for item in pair if item), "").replace("*", "").strip() for pair in quoted]
            messages = [item for item in messages if item]
            if not messages:
                messages = [re.sub(r"\*[^*]*\*", "", visible).strip()]
            parts[index] = json.dumps(messages, ensure_ascii=False)
        return "\n\n".join(part for part in parts if part.strip())
    if not is_sms_input(trigger):
        return reply
    parts = re.split(r"(```[\s\S]*?```)", reply)
    # Match every sender bubble so an LLM cannot echo the user's incoming
    # message as if it were part of the character's reply.
    bubble = r"\[([A-Za-z0-9_\u0E00-\u0E7F\s]{1,30})\s*:\s*([^\]]+)\]"
    tokens = re.compile(bubble + r'|"([^"\n]+)"|“([^”\n]+)”')
    for index in range(0, len(parts), 2):
        visible = parts[index]
        matches = list(tokens.finditer(visible))
        if not matches:
            continue
        output = []
        cursor = 0
        for match in matches:
            narration = visible[cursor:match.start()].strip().strip('*').strip()
            if narration:
                output.append(f"*{narration}*")
            sender, bracket_message, straight_quote, curly_quote = match.groups()
            if sender is not None:
                cursor = match.end()
                if sender.strip().casefold() != character.strip().casefold():
                    # The incoming user bubble was already supplied in the
                    # prompt. Never repeat it inside the assistant response.
                    continue
                message = bracket_message
            else:
                message = straight_quote if straight_quote is not None else curly_quote
            message = message.replace('*', '').strip()
            output.append(f"[{character}: {message}]")
            cursor = match.end()
        narration = visible[cursor:].strip().strip('*').strip()
        if narration:
            output.append(f"*{narration}*")
        parts[index] = " ".join(output) + ("\n\n" if visible.endswith('\n\n') else "")
    return "".join(parts)


def _read(kind: str, language: str) -> str:
    filename = "Thai.md" if language == "thai" else "English.md"
    try:
        return (Path("rules") / kind / filename).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def rule_blocks(language: str, trigger: str, character: str, target_user: str) -> str:
    """Return the symbol baseline and SMS overlay only when the channel needs it."""
    tokens = {"{{char}}": character, "{{user}}": target_user}

    def render(value: str) -> str:
        for token, replacement in tokens.items():
            value = value.replace(token, replacement)
        return value

    blocks = []
    symbol = _read("symbol", language)
    if symbol:
        blocks.append(f"[Visible Symbol Rules]\n{render(symbol)}")
    if is_sms_input(trigger):
        sms = _read("sms", language)
        if sms:
            blocks.append(f"[SMS Channel Rules]\n{render(sms)}")
            blocks.append(
                f"SMS formatting takes precedence over normal spoken-dialogue formatting. "
                f"Write sent words only as [{character}: message]. Never wrap a message "
                "bubble in asterisks or put actions inside it. Keep narration in separate "
                "*...* spans outside the bubble; do not use quoted speech for sent words. "
                f"Never repeat or emit the incoming [{target_user}: ...] bubble. The newest "
                "SMS turn overrides stale face-to-face posture or touch in Status and Current "
                "Situation: describe only the character's private actions at her location and "
                "do not claim the user is physically present, touching, visible, or nearby."
            )
    if is_voice_sms_input(trigger):
        blocks.append(
            "[Voice SMS Format]\n"
            "The user requested a voice message. Output the spoken message as a JSON string array only, for example "
            '["ข้อความแรก", "ข้อความถัดไป"]. Each string is one voice clip and must contain only words to be read aloud. '
            "Do not include a sender label, narration, actions, state labels, or Markdown inside that array."
        )
    return "\n\n".join(blocks)
