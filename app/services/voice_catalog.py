"""Voice catalog lookup independent of HTTP handlers."""


def available_voices() -> list:
    import tts_voices
    return tts_voices.get_available_voices()
