"""Async OpenAI client wrapper for generating narrative text."""

from __future__ import annotations

import importlib
import os
from typing import Optional

_openai_spec = importlib.util.find_spec("openai")
if _openai_spec:  # pragma: no cover - optional dependency
    from openai import AsyncOpenAI
else:  # pragma: no cover - optional dependency
    AsyncOpenAI = None  # type: ignore


class LLMUnavailableError(RuntimeError):
    """Raised when the OpenAI client cannot be initialized."""


def _client() -> AsyncOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMUnavailableError("OPENAI_API_KEY is not configured")
    if AsyncOpenAI is None:
        raise LLMUnavailableError("openai package is not installed")
    return AsyncOpenAI(api_key=api_key)


async def generate_section_text(
    system_prompt: str, user_prompt: str, max_tokens: int = 800, model: Optional[str] = None
) -> str:
    """Generate text for a report section using the OpenAI chat completions API."""

    client = _client()
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        result = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
    except Exception as exc:  # pragma: no cover - network interaction
        raise LLMUnavailableError(str(exc)) from exc

    content = result.choices[0].message.content if result.choices else ""
    return (content or "").strip()
