import json
import logging
import os
import random
import time
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple

import redis
from jsonschema import Draft7Validator

from ..schemas.forecasts import DailyTemplatedResponse

try:  # pragma: no cover - optional dependency during tests
    from openai import OpenAI
except Exception:  # pragma: no cover - the SDK may be absent locally
    OpenAI = None  # type: ignore


logger = logging.getLogger(__name__)


TEMPLATE_VERSION = os.getenv("DAILY_TEMPLATE_VERSION", "v1.0")
TEMPLATE_LANG = os.getenv("DAILY_TEMPLATE_LANG", "en")
TEMPLATE_MODEL = os.getenv("DAILY_TEMPLATE_MODEL", "gpt-4.1")
CACHE_TTL_SECONDS = int(os.getenv("DAILY_TEMPLATE_CACHE_TTL", str(60 * 60 * 72)))
CACHE_CONTROL_HEADER = "private, max-age=300, stale-while-revalidate=600"
LOCK_TTL_SECONDS = 30


TEMPLATE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": [
        "profile_name",
        "date",
        "mood",
        "theme",
        "opening_summary",
        "morning_mindset",
        "career",
        "love",
        "health",
        "finance",
        "do_today",
        "avoid_today",
        "lucky",
        "one_line_summary",
    ],
    "properties": {
        "profile_name": {"type": "string"},
        "date": {"type": "string", "pattern": r"^\\d{4}-\\d{2}-\\d{2}$"},
        "mood": {"type": "string"},
        "theme": {"type": "string"},
        "opening_summary": {"type": "string"},
        "morning_mindset": {
            "type": "object",
            "required": ["paragraph", "mantra"],
            "properties": {
                "paragraph": {"type": "string"},
                "mantra": {"type": "string"},
            },
        },
        "career": {
            "type": "object",
            "required": ["paragraph", "bullets"],
            "properties": {
                "paragraph": {"type": "string"},
                "bullets": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            },
        },
        "love": {
            "type": "object",
            "required": ["paragraph", "attached", "single"],
            "properties": {
                "paragraph": {"type": "string"},
                "attached": {"type": "string"},
                "single": {"type": "string"},
            },
        },
        "health": {
            "type": "object",
            "required": ["paragraph", "good_options"],
            "properties": {
                "paragraph": {"type": "string"},
                "good_options": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            },
        },
        "finance": {
            "type": "object",
            "required": ["paragraph", "bullets"],
            "properties": {
                "paragraph": {"type": "string"},
                "bullets": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            },
        },
        "do_today": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "avoid_today": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "lucky": {
            "type": "object",
            "required": ["color", "time_window", "direction", "affirmation"],
            "properties": {
                "color": {"type": "string"},
                "time_window": {"type": "string"},
                "direction": {"type": "string"},
                "affirmation": {"type": "string"},
            },
        },
        "one_line_summary": {"type": "string"},
    },
}


TEMPLATE_VALIDATOR = Draft7Validator(TEMPLATE_SCHEMA)


_redis_client: Optional[redis.Redis] = None
_redis_initialized = False


def _get_redis_client() -> Optional[redis.Redis]:
    global _redis_initialized, _redis_client
    if _redis_initialized:
        return _redis_client

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            _redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        except Exception:  # pragma: no cover - connection errors logged but not fatal
            logger.exception("daily_template_redis_init_failed", extra={"redis_url": redis_url})
            _redis_client = None
    else:
        logger.info("daily_template_redis_url_missing")

    _redis_initialized = True
    return _redis_client


_openai_client: Optional["OpenAI"] = None
_openai_initialized = False


def _get_openai_client() -> Optional["OpenAI"]:
    global _openai_initialized, _openai_client
    if _openai_initialized:
        return _openai_client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        if api_key and OpenAI is None:
            logger.info("daily_template_openai_sdk_missing")
        elif not api_key:
            logger.info("daily_template_openai_key_missing")
        _openai_initialized = True
        _openai_client = None
        return _openai_client

    organization = os.getenv("OPENAI_ORG_ID")
    client_kwargs: Dict[str, Any] = {"api_key": api_key}
    if organization:
        client_kwargs["organization"] = organization

    try:
        _openai_client = OpenAI(**client_kwargs)
    except Exception:  # pragma: no cover - initialization failure logged
        logger.exception("daily_template_openai_init_failed")
        _openai_client = None

    _openai_initialized = True
    return _openai_client


def _title_case(value: Optional[str]) -> str:
    if not value:
        return "You"
    return " ".join(part.capitalize() for part in value.split()) or "You"


def _stable_bundle(daily: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
    bundle = {
        "daily_payload": daily,
        "lang": TEMPLATE_LANG,
        "template_v": TEMPLATE_VERSION,
        "model": TEMPLATE_MODEL,
    }
    stable_json = json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    content_hash = sha256(stable_json.encode("utf-8")).hexdigest()
    etag = f'W/"{content_hash}"'
    return bundle, content_hash, etag


def _validate_payload(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = [
        f"{'/'.join(str(p) for p in err.path)}: {err.message}"
        for err in TEMPLATE_VALIDATOR.iter_errors(payload)
    ]
    return not errors, errors


def _parse_response(raw: str) -> Optional[Dict[str, Any]]:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _build_fallback(daily: Dict[str, Any]) -> DailyTemplatedResponse:
    meta = daily.get("meta", {})
    top_events = sorted(
        daily.get("top_events", []),
        key=lambda item: (
            -float(item.get("score", 0.0)),
            abs(float(item.get("orb", 99.9))),
        ),
    )
    score = float(top_events[0].get("score", 0.0)) if top_events else 0.0
    mood = "motivated" if score >= 7 else "balanced"
    profile = _title_case(meta.get("profile_name"))
    date = meta.get("date") or time.strftime("%Y-%m-%d")

    fallback = {
        "profile_name": profile,
        "date": date,
        "mood": mood,
        "theme": "Focused Momentum",
        "opening_summary": "Channel your effort into one intentional move today.",
        "morning_mindset": {
            "paragraph": "Ground yourself before diving into the busiest parts of the day.",
            "mantra": "Small steps carry real power.",
        },
        "career": {
            "paragraph": "Lean on steady progress and keep communication direct.",
            "bullets": [
                "Complete one meaningful task",
                "Clarify expectations",
                "Review priority deadlines",
            ],
        },
        "love": {
            "paragraph": "Lead with sincerity and keep your tone warm.",
            "attached": "Offer one honest appreciation to your partner.",
            "single": "Let conversations unfold without rushing the outcome.",
        },
        "health": {
            "paragraph": "Balance focus with mindful breaks and hydration.",
            "good_options": [
                "Brisk walk",
                "Gentle strength work",
                "Breathwork",
                "Plenty of water",
            ],
        },
        "finance": {
            "paragraph": "Think long-term and sidestep impulse choices.",
            "bullets": [
                "Review a key number",
                "Delay big purchases",
                "Plan your next savings step",
            ],
        },
        "do_today": [
            "Focus on one priority",
            "Speak kindly",
            "Move your body",
            "Hydrate intentionally",
        ],
        "avoid_today": [
            "Overcommitting",
            "Power struggles",
            "Doomscrolling",
            "Impulse spending",
        ],
        "lucky": {
            "color": "Deep Red",
            "time_window": "10:00–12:00",
            "direction": "SE",
            "affirmation": "My focus is steady and encouraging.",
        },
        "one_line_summary": "Steady, grounded momentum keeps you aligned today.",
    }
    return DailyTemplatedResponse.model_validate(fallback)


def _render_with_llm(
    client: "OpenAI",
    daily_payload: Dict[str, Any],
    retry_payload: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[int]]:
    daily_json = json.dumps(daily_payload, ensure_ascii=False)
    system_prompt = (
        "You are a clear, supportive astrologer-writer. "
        "Write in warm, plain English with no fatalism or guarantees. "
        "Ground each section in the strongest events by score and tightest orb. "
        "Return valid JSON ONLY."
    )

    user_lines = [
        f"TEMPLATE_VERSION={TEMPLATE_VERSION}",
        f"LANG={TEMPLATE_LANG}",
        f"MODEL={TEMPLATE_MODEL}",
        "- Use meta.profile_name (Title Case) and meta.date.",
        "- Reference significant transits lightly; keep it readable.",
        "- If data is missing, stay honest and general—no fabrication.",
        "INPUT_DAILY_JSON:",
        daily_json,
    ]

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n".join(user_lines)},
    ]

    if retry_payload is not None:
        messages.append({"role": "assistant", "content": retry_payload["previous_raw"]})
        messages.append({"role": "user", "content": retry_payload["repair_message"]})

    try:
        response = client.chat.completions.create(
            model=TEMPLATE_MODEL,
            messages=messages,
            temperature=0.2,
        )
    except Exception:  # pragma: no cover - network failures
        logger.exception("daily_template_llm_call_failed")
        return None, None, None

    raw_content = (response.choices[0].message.content or "") if response.choices else ""
    total_tokens = getattr(response, "usage", None)
    token_count = getattr(total_tokens, "total_tokens", None)
    return _parse_response(raw_content), raw_content, token_count


def _describe_errors(errors: List[str]) -> str:
    return "Validation errors: " + "; ".join(errors)


@dataclass
class DailyTemplateResult:
    payload: Optional[Dict[str, Any]]
    etag: str
    not_modified: bool
    cache_hit: bool
    cache_control: str = CACHE_CONTROL_HEADER


def generate_daily_template(
    daily_payload: Dict[str, Any],
    request_headers: Mapping[str, str],
) -> DailyTemplateResult:
    _, content_hash, etag = _stable_bundle(daily_payload)
    date = daily_payload.get("meta", {}).get("date", "unknown")
    cache_key = f"dailyTpl:{date}:{TEMPLATE_LANG}:{TEMPLATE_VERSION}:{TEMPLATE_MODEL}:{content_hash}"
    lock_key = f"lock:{cache_key}"

    redis_client = _get_redis_client()
    cached_payload: Optional[Dict[str, Any]] = None
    cache_hit = False

    if redis_client is not None:
        try:
            cached_raw = redis_client.get(cache_key)
        except Exception:  # pragma: no cover - redis outage
            logger.exception("daily_template_cache_get_failed", extra={"cache_key": cache_key})
            cached_raw = None

        if cached_raw:
            parsed = _parse_response(cached_raw)
            if parsed:
                try:
                    cached_payload = DailyTemplatedResponse.model_validate(parsed).model_dump(mode="json")
                    cache_hit = True
                except Exception:
                    logger.exception("daily_template_cache_validation_failed", extra={"cache_key": cache_key})
                    cached_payload = None
                    try:
                        redis_client.delete(cache_key)
                    except Exception:
                        logger.exception("daily_template_cache_delete_failed", extra={"cache_key": cache_key})

            if cached_payload is not None:
                not_modified = request_headers.get("if-none-match") == etag
                logger.info(
                    "daily_template_cache_hit",
                    extra={"cache_key": cache_key, "hit": True, "etag": etag},
                )
                return DailyTemplateResult(
                    payload=None if not_modified else cached_payload,
                    etag=etag,
                    not_modified=not_modified,
                    cache_hit=True,
                )

    lock_acquired = False
    lock_wait_ms = 0
    if redis_client is not None and not cache_hit:
        try:
            lock_acquired = bool(redis_client.set(lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS))
        except Exception:
            logger.exception("daily_template_lock_failed", extra={"cache_key": cache_key})
            lock_acquired = False

        if not lock_acquired:
            wait_seconds = random.uniform(0.3, 0.8)
            time.sleep(wait_seconds)
            lock_wait_ms = int(wait_seconds * 1000)
            try:
                cached_raw = redis_client.get(cache_key)
            except Exception:
                logger.exception("daily_template_cache_retry_failed", extra={"cache_key": cache_key})
                cached_raw = None

            if cached_raw:
                parsed = _parse_response(cached_raw)
                if parsed:
                    try:
                        cached_payload = DailyTemplatedResponse.model_validate(parsed).model_dump(mode="json")
                        cache_hit = True
                    except Exception:
                        logger.exception("daily_template_cache_validation_failed", extra={"cache_key": cache_key})
                        cached_payload = None

            if cached_payload is not None:
                not_modified = request_headers.get("if-none-match") == etag
                logger.info(
                    "daily_template_cache_hit",
                    extra={
                        "cache_key": cache_key,
                        "hit": True,
                        "etag": etag,
                        "lock_wait_ms": lock_wait_ms,
                    },
                )
                return DailyTemplateResult(
                    payload=None if not_modified else cached_payload,
                    etag=etag,
                    not_modified=not_modified,
                    cache_hit=True,
                )

            try:
                lock_acquired = bool(redis_client.set(lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS))
            except Exception:
                logger.exception("daily_template_lock_second_attempt_failed", extra={"cache_key": cache_key})
                lock_acquired = False

    llm_client = _get_openai_client()
    validation_errors: List[str] = []
    llm_tokens: Optional[int] = None
    generated_payload: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None

    if llm_client is not None:
        parsed, raw_response, llm_tokens = _render_with_llm(llm_client, daily_payload)
        if parsed is not None:
            is_valid, validation_errors = _validate_payload(parsed)
            if is_valid:
                try:
                    generated_payload = DailyTemplatedResponse.model_validate(parsed).model_dump(mode="json")
                except Exception as exc:  # pragma: no cover - should be rare
                    validation_errors = [str(exc)]
                    generated_payload = None
            else:
                logger.warning(
                    "daily_template_validation_failed",
                    extra={"errors": validation_errors},
                )
        else:
            validation_errors = ["response was not valid JSON"]

        if generated_payload is None and raw_response is not None:
            if validation_errors:
                repair_message = _describe_errors(validation_errors) + " Please fix and return ONLY valid JSON."
            else:
                repair_message = "Previous response could not be parsed. Return valid JSON only."
            parsed_retry, raw_retry, retry_tokens = _render_with_llm(
                llm_client,
                daily_payload,
                {
                    "previous_raw": raw_response,
                    "repair_message": repair_message,
                },
            )
            if raw_retry is not None:
                raw_response = raw_retry
            if retry_tokens is not None:
                llm_tokens = retry_tokens
            if parsed_retry is not None:
                is_valid, validation_errors = _validate_payload(parsed_retry)
                if is_valid:
                    try:
                        generated_payload = DailyTemplatedResponse.model_validate(parsed_retry).model_dump(mode="json")
                        validation_errors = []
                    except Exception as exc:
                        validation_errors = [str(exc)]
                else:
                    logger.warning(
                        "daily_template_validation_failed_retry",
                        extra={"errors": validation_errors},
                    )

    if generated_payload is None:
        fallback = _build_fallback(daily_payload)
        generated_payload = fallback.model_dump(mode="json")
        if validation_errors:
            logger.error(
                "daily_template_fallback_used",
                extra={"cache_key": cache_key, "errors": validation_errors},
            )
        else:
            logger.warning("daily_template_llm_unavailable_fallback", extra={"cache_key": cache_key})

    if redis_client is not None and generated_payload is not None:
        try:
            redis_client.set(
                cache_key,
                json.dumps(generated_payload, separators=(",", ":"), ensure_ascii=False),
                ex=CACHE_TTL_SECONDS,
            )
        except Exception:
            logger.exception("daily_template_cache_set_failed", extra={"cache_key": cache_key})
        finally:
            if lock_acquired:
                try:
                    redis_client.delete(lock_key)
                except Exception:
                    logger.exception("daily_template_lock_release_failed", extra={"cache_key": cache_key})
    elif redis_client is not None and lock_acquired:
        try:
            redis_client.delete(lock_key)
        except Exception:
            logger.exception("daily_template_lock_release_failed", extra={"cache_key": cache_key})

    logger.info(
        "daily_template_generation_complete",
        extra={
            "cache_key": cache_key,
            "cache_hit": cache_hit,
            "etag": etag,
            "lock_wait_ms": lock_wait_ms,
            "validation_errors": validation_errors,
            "tokens": llm_tokens,
        },
    )

    not_modified = request_headers.get("if-none-match") == etag
    return DailyTemplateResult(
        payload=None if not_modified else generated_payload,
        etag=etag,
        not_modified=not_modified and cache_hit,
        cache_hit=cache_hit,
    )
