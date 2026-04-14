from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from openai import OpenAI

from .settings import settings
from .utils import parse_json_object


def _build_client() -> OpenAI | None:
    if not settings.OXLO_API_KEY:
        return None
    return OpenAI(base_url=settings.OXLO_BASE_URL, api_key=settings.OXLO_API_KEY)


_client = _build_client()


def _chat_completion_sync(model: str, messages: List[Dict[str, str]], max_tokens: int = 512) -> str:
    if _client is None:
        raise RuntimeError("OXLO_API_KEY is not configured")

    response = _client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


async def chat_completion(model: str, messages: List[Dict[str, str]], max_tokens: int = 512) -> str:
    return await asyncio.to_thread(_chat_completion_sync, model, messages, max_tokens)


# JSON parsing utility moved to `app.utils.parse_json_object`