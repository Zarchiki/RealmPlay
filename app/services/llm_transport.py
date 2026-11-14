"""Low-level HTTP transport for OpenAI-compatible local LLM endpoints."""

import json
import urllib.request


def open_completion(url: str, payload: dict, timeout: int = 90):
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"},
    )
    return urllib.request.urlopen(request, timeout=timeout)
