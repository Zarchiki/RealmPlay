"""Small, dependency-free input utilities shared by API modules."""

import re
from fastapi import HTTPException


def safe_name(name: str) -> str:
    """Validate a user supplied name before it is used in a filesystem path."""
    if (
        not name
        or name in (".", "..")
        or any(char in name for char in ("/", "\\", "\x00"))
        or ".." in name
    ):
        raise HTTPException(status_code=400, detail="Invalid name")
    return name


def response_language(text: str) -> str:
    """Detect the response language from a user's message."""
    raw = text or ""
    thai_count = len(re.findall(r"[\u0E00-\u0E7F]", raw))
    jp_kana = len(re.findall(r"[\u3040-\u309F\u30A0-\u30FF]", raw))
    cjk_ideographs = len(re.findall(r"[\u4E00-\u9FFF]", raw))
    latin_count = len(re.findall(r"[A-Za-zÀ-ÿ]", raw))

    if jp_kana > 0:
        return "japanese"
    if cjk_ideographs > 0 and cjk_ideographs > latin_count:
        return "chinese"
    latin_words = re.findall(r"[A-Za-zÀ-ÿ]+", raw)
    if thai_count > 0 and (thai_count >= latin_count or thai_count >= 3 or thai_count >= len(latin_words)):
        return "thai"

    if latin_count > 0:
        lower = raw.casefold()
        french_markers = len(re.findall(
            r"\b(je|tu|il|elle|nous|vous|ils|elles|le|la|les|un|une|des|est|sont|dans|pour|avec|pas|ce|cette|mon|ma|mes|ton|ta|tes|son|sa|ses|qui|que|quoi|mais|ou|et|donc|or|ni|car|bonjour|salut|merci|comment|allez|faire|oui|non)\b|[éèêëàâùûîïôçœæ]",
            lower,
        ))
        spanish_markers = len(re.findall(
            r"\b(yo|tú|él|ella|nosotros|vosotros|ellos|ellas|el|la|los|las|un|una|unos|unas|es|son|en|por|para|con|no|este|esta|estos|estas|mi|mis|tu|tus|su|sus|que|qué|pero|como|cómo|del|al|hola|gracias|amigo|amiga|bien|estás)\b|[áéíóúüñ¿¡]",
            lower,
        ))
        if french_markers > spanish_markers and french_markers >= 1:
            return "french"
        if spanish_markers > french_markers and spanish_markers >= 1:
            return "spanish"

    return "english"
