"""Configuration and request-payload construction for local LLM calls."""

import json


def load_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def payload(model: str, messages: list, sampling_values: dict, normalize, stream: bool = False) -> dict:
    result = {"model": model, "messages": normalize(messages), **sampling_values}
    if stream:
        result["stream"] = True
    return result


def trim_for_context_retry(messages: list, clip, limit: int = 3000) -> list:
    trimmed = [
        {**message, "content": clip(content, limit)} if isinstance((content := message.get("content", "")), str) and len(content) > limit else message
        for message in messages
    ]
    return [trimmed[0], *trimmed[-2:]] if len(trimmed) > 2 else trimmed
