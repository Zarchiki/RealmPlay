# -*- coding: utf-8 -*-
"""Comprehensive curated voice list for RealmPlay across 7 international languages."""

CURATED_TTS_VOICES = [
    # English (US)
    {"id": "en-US-AvaNeural", "name": "Ava (Female)", "gender": "Female", "locale": "en-US", "language": "English (US)"},
    {"id": "en-US-EmmaNeural", "name": "Emma (Female)", "gender": "Female", "locale": "en-US", "language": "English (US)"},
    {"id": "en-US-JennyNeural", "name": "Jenny (Female)", "gender": "Female", "locale": "en-US", "language": "English (US)"},
    {"id": "en-US-AriaNeural", "name": "Aria (Female)", "gender": "Female", "locale": "en-US", "language": "English (US)"},
    {"id": "en-US-AndrewNeural", "name": "Andrew (Male)", "gender": "Male", "locale": "en-US", "language": "English (US)"},
    {"id": "en-US-BrianNeural", "name": "Brian (Male)", "gender": "Male", "locale": "en-US", "language": "English (US)"},
    {"id": "en-US-GuyNeural", "name": "Guy (Male)", "gender": "Male", "locale": "en-US", "language": "English (US)"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher (Male)", "gender": "Male", "locale": "en-US", "language": "English (US)"},

    # English (UK)
    {"id": "en-GB-SoniaNeural", "name": "Sonia (Female)", "gender": "Female", "locale": "en-GB", "language": "English (UK)"},
    {"id": "en-GB-LibbyNeural", "name": "Libby (Female)", "gender": "Female", "locale": "en-GB", "language": "English (UK)"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (Male)", "gender": "Male", "locale": "en-GB", "language": "English (UK)"},
    {"id": "en-GB-ThomasNeural", "name": "Thomas (Male)", "gender": "Male", "locale": "en-GB", "language": "English (UK)"},

    # Japanese
    {"id": "ja-JP-NanamiNeural", "name": "Nanami (七海 - Female)", "gender": "Female", "locale": "ja-JP", "language": "Japanese"},
    {"id": "ja-JP-KeitaNeural", "name": "Keita (圭太 - Male)", "gender": "Male", "locale": "ja-JP", "language": "Japanese"},

    # Chinese (Mandarin Simplified)
    {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao (晓晓 - Female)", "gender": "Female", "locale": "zh-CN", "language": "Chinese (Mandarin)"},
    {"id": "zh-CN-XiaoyiNeural", "name": "Xiaoyi (晓依 - Female)", "gender": "Female", "locale": "zh-CN", "language": "Chinese (Mandarin)"},
    {"id": "zh-CN-YunjianNeural", "name": "Yunjian (云健 - Male)", "gender": "Male", "locale": "zh-CN", "language": "Chinese (Mandarin)"},
    {"id": "zh-CN-YunxiNeural", "name": "Yunxi (云希 - Male)", "gender": "Male", "locale": "zh-CN", "language": "Chinese (Mandarin)"},

    # French
    {"id": "fr-FR-VivienneMultilingualNeural", "name": "Vivienne (Female)", "gender": "Female", "locale": "fr-FR", "language": "French"},
    {"id": "fr-FR-DeniseNeural", "name": "Denise (Female)", "gender": "Female", "locale": "fr-FR", "language": "French"},
    {"id": "fr-FR-EloiseNeural", "name": "Eloise (Female)", "gender": "Female", "locale": "fr-FR", "language": "French"},
    {"id": "fr-FR-RemyMultilingualNeural", "name": "Remy (Male)", "gender": "Male", "locale": "fr-FR", "language": "French"},
    {"id": "fr-FR-HenriNeural", "name": "Henri (Male)", "gender": "Male", "locale": "fr-FR", "language": "French"},

    # Spanish
    {"id": "es-ES-XimenaNeural", "name": "Ximena (Female)", "gender": "Female", "locale": "es-ES", "language": "Spanish"},
    {"id": "es-ES-ElviraNeural", "name": "Elvira (Female)", "gender": "Female", "locale": "es-ES", "language": "Spanish"},
    {"id": "es-ES-AlvaroNeural", "name": "Alvaro (Male)", "gender": "Male", "locale": "es-ES", "language": "Spanish"},

    # Thai
    {"id": "th-TH-PremwadeeNeural", "name": "Premwadee (เปรมวดี - Female)", "gender": "Female", "locale": "th-TH", "language": "Thai"},
    {"id": "th-TH-NiwatNeural", "name": "Niwat (นิวัฒน์ - Male)", "gender": "Male", "locale": "th-TH", "language": "Thai"}
]

def get_available_voices():
    """Return the curated list of voices grouped by language."""
    return CURATED_TTS_VOICES
