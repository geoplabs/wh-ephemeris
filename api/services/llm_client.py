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
    
    # Optional: Organization ID for team/organization accounts
    org_id = os.getenv("OPENAI_ORG_ID")
    
    # Set a longer timeout for complex requests (default is 600 seconds / 10 minutes)
    timeout = float(os.getenv("OPENAI_TIMEOUT", "600"))
    
    if org_id:
        return AsyncOpenAI(api_key=api_key, organization=org_id, timeout=timeout)
    else:
        return AsyncOpenAI(api_key=api_key, timeout=timeout)


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
        # Provide more specific error messages
        error_msg = str(exc)
        error_type = type(exc).__name__
        
        if "rate_limit" in error_msg.lower():
            raise LLMUnavailableError(f"OpenAI rate limit exceeded: {error_msg}") from exc
        elif "invalid_api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            raise LLMUnavailableError(f"Invalid OpenAI API key: {error_msg}") from exc
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower() or error_type == "TimeoutError":
            timeout_val = os.getenv("OPENAI_TIMEOUT", "600")
            raise LLMUnavailableError(
                f"OpenAI API error: Request timed out. "
                f"Current timeout: {timeout_val}s. "
                f"Consider increasing OPENAI_TIMEOUT environment variable."
            ) from exc
        elif "insufficient_quota" in error_msg.lower():
            raise LLMUnavailableError(f"OpenAI quota exceeded: {error_msg}") from exc
        else:
            raise LLMUnavailableError(f"OpenAI API error: {error_msg}") from exc

    content = result.choices[0].message.content if result.choices else ""
    return (content or "").strip()
