import json
import logging
import os
import random
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import Any, Dict, List, Optional, Sequence, Tuple

import redis
from jsonschema import Draft7Validator
from jinja2 import Environment, Template

from ..schemas.forecasts import DailyTemplatedResponse
from .option_b_cleaner.render import (
    build_context,
    collect_bullet_roots,
    normalize_avoid,
    normalize_bullets,
)
from .remedy_templates import remedy_templates_for_planet

try:  # pragma: no cover - optional dependency during tests
    from openai import OpenAI
except Exception:  # pragma: no cover - the SDK may be absent locally
    OpenAI = None  # type: ignore


logger = logging.getLogger(__name__)


TEMPLATE_VERSION = os.getenv("DAILY_TEMPLATE_VERSION", "v1.0")
TEMPLATE_LANG = os.getenv("DAILY_TEMPLATE_LANG", "en")
TEMPLATE_MODEL = os.getenv("DAILY_TEMPLATE_MODEL", "gpt-4o-mini")
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
        "caution_window",
        "remedies",
        "lucky",
        "one_line_summary",
    ],
    "properties": {
        "profile_name": {"type": "string"},
        "date": {"type": "string"},
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
                "bullets": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
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
                "good_options": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            },
        },
        "finance": {
            "type": "object",
            "required": ["paragraph", "bullets"],
            "properties": {
                "paragraph": {"type": "string"},
                "bullets": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            },
        },
        "do_today": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        "avoid_today": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        "caution_window": {
            "type": "object",
            "required": ["time_window", "note"],
            "properties": {
                "time_window": {"type": "string"},
                "note": {"type": "string"},
            },
        },
        "remedies": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
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


SANITIZED_LIST_LIMIT = 4

_SPECIAL_EVENT_PRIORITY = {
    "eclipse": 0,
    "lunar_phase": 1,
    "void_of_course": 2,
    "out_of_bounds": 3,
}


def _coerce_string(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _sanitize_string_list(value: Any, limit: int = SANITIZED_LIST_LIMIT) -> List[str]:
    if not isinstance(value, list):
        return []
    sanitized: List[str] = []
    for item in value:
        if len(sanitized) >= limit:
            break
        text = _coerce_string(item)
        if text:
            sanitized.append(text)
    return sanitized


def _sanitize_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _sanitize_payload(payload: Any) -> Dict[str, Any]:
    data = _sanitize_mapping(payload)

    morning_mindset = _sanitize_mapping(data.get("morning_mindset"))
    career = _sanitize_mapping(data.get("career"))
    love = _sanitize_mapping(data.get("love"))
    health = _sanitize_mapping(data.get("health"))
    finance = _sanitize_mapping(data.get("finance"))
    lucky = _sanitize_mapping(data.get("lucky"))
    caution_window = _sanitize_mapping(data.get("caution_window"))
    remedies = _sanitize_string_list(data.get("remedies"))

    sanitized_payload: Dict[str, Any] = {
        "profile_name": _coerce_string(data.get("profile_name")),
        "date": _coerce_string(data.get("date")),
        "mood": _coerce_string(data.get("mood")),
        "theme": _coerce_string(data.get("theme")),
        "opening_summary": _coerce_string(data.get("opening_summary")),
        "morning_mindset": {
            "paragraph": _coerce_string(morning_mindset.get("paragraph")),
            "mantra": _coerce_string(morning_mindset.get("mantra")),
        },
        "career": {
            "paragraph": _coerce_string(career.get("paragraph")),
            "bullets": _sanitize_string_list(career.get("bullets")),
        },
        "love": {
            "paragraph": _coerce_string(love.get("paragraph")),
            "attached": _coerce_string(love.get("attached")),
            "single": _coerce_string(love.get("single")),
        },
        "health": {
            "paragraph": _coerce_string(health.get("paragraph")),
            "good_options": _sanitize_string_list(health.get("good_options")),
        },
        "finance": {
            "paragraph": _coerce_string(finance.get("paragraph")),
            "bullets": _sanitize_string_list(finance.get("bullets")),
        },
        "do_today": _sanitize_string_list(data.get("do_today")),
        "avoid_today": _sanitize_string_list(data.get("avoid_today")),
        "caution_window": {
            "time_window": _coerce_string(caution_window.get("time_window")),
            "note": _coerce_string(caution_window.get("note")),
        },
        "remedies": remedies,
        "lucky": {
            "color": _coerce_string(lucky.get("color")),
            "time_window": _coerce_string(lucky.get("time_window")),
            "direction": _coerce_string(lucky.get("direction")),
            "affirmation": _coerce_string(lucky.get("affirmation")),
        },
        "one_line_summary": _coerce_string(data.get("one_line_summary")),
    }

    return sanitized_payload


def _ensure_sentence(value: Any) -> str:
    text = _coerce_string(value)
    if not text:
        return ""
    condensed = " ".join(text.split())
    if not condensed:
        return ""
    if condensed[-1] not in ".!?":
        condensed = f"{condensed}."
    return condensed


def _append_sentence(base: Any, addition: str) -> str:
    base_text = _coerce_string(base)
    addition_text = _ensure_sentence(addition)
    if not addition_text:
        return _ensure_sentence(base_text)

    normalized_addition = addition_text.rstrip(".!?").lower()
    if normalized_addition and normalized_addition in base_text.lower():
        return _ensure_sentence(base_text)

    if base_text:
        base_sentence = _ensure_sentence(base_text)
        return f"{base_sentence.rstrip()} {addition_text}"

    return addition_text


def _event_strength(event: Mapping[str, Any]) -> float:
    try:
        return abs(float(event.get("score", 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _event_type_label(event: Mapping[str, Any]) -> str:
    raw_type = _coerce_string(event.get("event_type"))
    if not raw_type:
        raw_type = _coerce_string(event.get("aspect"))
    return raw_type.lower()


def _format_special_event(event: Mapping[str, Any]) -> str:
    event_type = _event_type_label(event)
    note_sentence = _ensure_sentence(event.get("note"))

    if event_type == "lunar_phase":
        phase_name = _coerce_string(event.get("phase_name"))
        if not phase_name:
            lunar_info = _sanitize_mapping(event.get("lunar_phase_info"))
            phase_name = _coerce_string(lunar_info.get("phase_name"))
        phase_label = phase_name.replace("_", " ").title() if phase_name else "Lunar phase"

        special_moon = _sanitize_mapping(event.get("special_moon"))
        if special_moon.get("has_special_moon"):
            banner = _coerce_string(special_moon.get("banner"))
            if not banner:
                banner = _coerce_string(special_moon.get("type")).replace("_", " ").title()
            detail = note_sentence.rstrip(".!?") if note_sentence else ""
            if phase_label and detail.lower().startswith(phase_label.lower()):
                detail = detail[len(phase_label) :].lstrip(": ,")
            description = _coerce_string(special_moon.get("description"))
            if description:
                description = description.rstrip(".!?")
            details: List[str] = []
            if detail:
                details.append(detail)
            if description:
                details.append(description)
            combined = " – ".join(details) if details else ""
            label_parts = [part for part in (banner, phase_label) if part]
            label = " ".join(label_parts) if label_parts else "Special Moon"
            return _ensure_sentence(f"{label}: {combined}" if combined else label)

        if note_sentence:
            return note_sentence

        return _ensure_sentence(f"{phase_label} shapes the emotional tone today")

    if note_sentence:
        return note_sentence

    banner = _coerce_string(event.get("banner"))
    label = banner or event_type.replace("_", " ").title() or "Special sky event"
    tone_line = _coerce_string(event.get("tone_line"))
    description = _coerce_string(event.get("description"))
    impact = _coerce_string(event.get("impact_level"))
    detail = tone_line or description or impact or "Expect a noticeable shift today"
    return _ensure_sentence(f"{label}: {detail}")


def _special_event_mentions(events: Sequence[Mapping[str, Any]]) -> List[str]:
    candidates: List[Dict[str, Any]] = []
    for raw in events:
        event = _sanitize_mapping(raw)
        event_type = _event_type_label(event)
        special_moon = _sanitize_mapping(event.get("special_moon"))
        if event_type in _SPECIAL_EVENT_PRIORITY or special_moon.get("has_special_moon"):
            candidates.append(event)

    if not candidates:
        return []

    def _sort_key(item: Mapping[str, Any]) -> Tuple[int, float]:
        event_type = _event_type_label(item)
        priority = _SPECIAL_EVENT_PRIORITY.get(event_type, 99)
        return (priority, -_event_strength(item))

    candidates.sort(key=_sort_key)

    mentions: List[str] = []
    for event in candidates:
        sentence = _format_special_event(event)
        if sentence:
            mentions.append(sentence)
        if len(mentions) >= 2:
            break
    return mentions


def _summarize_special_mentions(mentions: Sequence[str]) -> str:
    if not mentions:
        return ""
    first = mentions[0].strip().rstrip(".!?")
    summary = f"Special sky watch: {first}."
    for extra in mentions[1:]:
        summary = f"{summary} {extra.strip()}"
    return summary


def _apply_special_sky_events(
    payload: Dict[str, Any],
    daily_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    events = daily_payload.get("events")
    if not isinstance(events, Sequence):
        events = daily_payload.get("top_events") or []

    mentions = _special_event_mentions(events) if events else []
    summary = _summarize_special_mentions(mentions)
    if not summary:
        return payload

    updated = dict(payload)
    updated["opening_summary"] = _append_sentence(updated.get("opening_summary"), summary)

    morning = _sanitize_mapping(updated.get("morning_mindset"))
    morning["paragraph"] = _append_sentence(morning.get("paragraph"), summary)
    updated["morning_mindset"] = morning

    updated["one_line_summary"] = _append_sentence(updated.get("one_line_summary"), summary)

    return updated


def _lower_first(value: Any) -> str:
    text = _coerce_string(value)
    if not text:
        return ""
    return text[0].lower() + text[1:]


def _guidance_clause(value: Any) -> str:
    text = _coerce_string(value)
    if not text:
        return ""
    normalized = " ".join(text.split())
    if not normalized:
        return ""
    normalized = re.sub(r"\bYou\b", "you", normalized)
    normalized = re.sub(r"\bYour\b", "your", normalized)
    normalized = re.sub(r"\bYou're\b", "you're", normalized)
    normalized = normalized.rstrip(" .!?")
    return _lower_first(normalized)


def _trim_for_display(
    value: Any,
    *,
    width: Optional[int] = None,
    fallback: str = "",
    ensure_sentence: bool = False,
) -> str:
    text = _coerce_string(value)
    if not text:
        text = fallback
    if not text:
        return ""

    normalized = " ".join(text.split())
    if not normalized:
        normalized = fallback
    if not normalized:
        return ""

    result = normalized
    if width and width > 0 and len(normalized) > width:
        candidate_result = ""
        for sentence in re.split(r"(?<=[.!?])\s+", normalized):
            candidate = sentence.strip()
            if candidate and len(candidate) <= width:
                candidate_result = candidate
                break
        if not candidate_result:
            words = normalized.split()
            trimmed: List[str] = []
            current_len = 0
            for word in words:
                additional = len(word) if not trimmed else len(word) + 1
                if current_len + additional > width:
                    break
                trimmed.append(word)
                current_len += additional
            candidate_result = " ".join(trimmed).rstrip(",;:-")
        if candidate_result:
            result = candidate_result
        else:
            result = normalized[:width].rstrip()
    if ensure_sentence:
        result = _ensure_sentence(result)
    return result


_jinja_env: Optional[Environment] = None


def _get_jinja_env() -> Environment:
    global _jinja_env
    if _jinja_env is None:
        env = Environment(autoescape=False, trim_blocks=True, lstrip_blocks=True)
        env.filters["lower_first"] = _lower_first
        _jinja_env = env
    return _jinja_env


@lru_cache(maxsize=128)
def _compile_template(source: str) -> Template:
    return _get_jinja_env().from_string(source)


def _render_from_templates(
    templates: Sequence[str],
    context: Dict[str, Any],
    fallback: str,
    *,
    ensure_sentence_output: bool = True,
) -> str:
    for template_source in templates:
        try:
            rendered = _compile_template(template_source).render(**context)
        except Exception:
            logger.exception(
                "daily_template_template_render_failed",
                extra={"template": template_source},
            )
            continue
        cleaned = _coerce_string(rendered)
        if not cleaned:
            continue
        cleaned = " ".join(cleaned.split())
        if ensure_sentence_output:
            cleaned = _ensure_sentence(cleaned)
        if cleaned:
            return cleaned
    fallback_cleaned = _coerce_string(fallback)
    if ensure_sentence_output:
        return _ensure_sentence(fallback_cleaned)
    return fallback_cleaned


OPENING_SUMMARY_TEMPLATES: Tuple[str, ...] = (
    "{{ summary }}",
    "{{ profile_ref }} can start {{ date }} with {{ theme|lower_first }} front and centre. {{ summary }}",
)

MORNING_PARAGRAPH_TEMPLATES: Tuple[str, ...] = (
    "{{ profile_ref }} can set the tone by taking one intentional pause before leaning into {{ theme|lower_first }}.",
    "Before the day accelerates, {{ profile_ref }} can breathe and let {{ theme|lower_first }} guide the first move.",
)

MORNING_MANTRA_TEMPLATES: Tuple[str, ...] = (
    "{{ affirmation }}",
    "I focus on {{ theme|lower_first }} with calm confidence",
)

FOCUS_PARAGRAPH_TEMPLATES: Dict[str, Tuple[str, ...]] = {
    "career": (
        "{{ profile_ref }} can turn today's {{ highlight|lower_first }} into deliberate progress at work.{% if guidance %} {{ guidance }}{% endif %}",
        "Professional momentum builds when {{ profile_ref }} honours {{ highlight|lower_first }}.{% if guidance %} {{ guidance }}{% endif %}",
    ),
    "finance": (
        "{{ profile_ref }} can let {{ highlight|lower_first }} inform smart money moves today.{% if guidance %} {{ guidance }}{% endif %}",
        "Steady resources flow when {{ profile_ref }} stays close to {{ highlight|lower_first }}.{% if guidance %} {{ guidance }}{% endif %}",
    ),
    "health": (
        "{{ profile_ref }} can balance energy by keeping {{ highlight|lower_first }} in mind.{% if guidance %} {{ guidance }}{% endif %}",
        "Wellness improves as {{ profile_ref }} listens to how {{ highlight|lower_first }} feels in the body.{% if guidance %} {{ guidance }}{% endif %}",
    ),
    "default": (
        "{{ profile_ref }} can stay aligned with {{ highlight|lower_first }}.{% if guidance %} {{ guidance }}{% endif %}",
    ),
}

LOVE_PARAGRAPH_TEMPLATES: Tuple[str, ...] = (
    "Heart matters: {{ highlight }}{% if guidance %}. {{ guidance }}{% endif %}",
    "{{ profile_ref }} can let relationships revolve around {{ highlight|lower_first }} today.{% if guidance %} {{ guidance }}{% endif %}",
)

LOVE_ATTACHED_TEMPLATES: Tuple[str, ...] = (
    "If you're attached, {{ guidance_clause or 'offer one honest appreciation to your partner' }}.",
    "If you're attached, keep the bond steady{% if guidance_clause %} and {{ guidance_clause }}{% else %} by sharing gratitude{% endif %}.",
)

LOVE_SINGLE_TEMPLATES: Tuple[str, ...] = (
    "If you're single, {{ guidance_clause or 'let conversations unfold without rushing the outcome' }}.",
    "If you're single, stay open{% if guidance_clause %} and {{ guidance_clause }}{% else %} by noticing genuine curiosity{% endif %}.",
)

DEFAULT_HEALTH_NOTES: Tuple[str, ...] = (
    "Brisk walk",
    "Gentle strength work",
    "Breathwork",
    "Plenty of water",
)

DEFAULT_MANTRA = "I choose what strengthens me."
SECONDARY_MANTRA = "I keep my presence clear and calm."
DISTINCT_PHRASE_FALLBACK = "I welcome steady clarity."


CHALLENGING_ASPECTS = {
    "square",
    "opposition",
    "quincunx",
    "retrograde",
    "semi-square",
    "sesquisquare",
}

CHALLENGING_KEYWORDS = {
    "pressure",
    "tension",
    "strain",
    "challenge",
    "caution",
    "warning",
    "delay",
    "stress",
    "conflict",
    "pushback",
}


def _strip_emdash(text: Optional[str]) -> str:
    if not isinstance(text, str):
        return ""
    return text.replace("—", "-").replace("–", "-")


def _normalize_for_compare(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip()).lower()


def _select_distinct_phrase(
    candidate: Optional[str], *, fallback: str, avoid: str, secondary: str
) -> str:
    options = [candidate, fallback, secondary, DISTINCT_PHRASE_FALLBACK]
    normalized_avoid = _normalize_for_compare(avoid)
    for option in options:
        if not option:
            continue
        stripped = option.strip()
        if not stripped:
            continue
        if _normalize_for_compare(stripped) != normalized_avoid:
            return stripped
    return fallback


def _dominant_body(events: Sequence[Mapping[str, Any]]) -> str:
    for event in events:
        if not isinstance(event, Mapping):
            continue
        for key in ("transit_body", "body", "planet"):
            candidate = _coerce_string(event.get(key))
            if candidate:
                return candidate
    return "Sun"


def _dominant_sign(events: Sequence[Mapping[str, Any]]) -> str:
    for event in events:
        if not isinstance(event, Mapping):
            continue
        for key in ("transit_sign", "sign", "natal_sign", "zodiac"):
            candidate = _coerce_string(event.get(key))
            if candidate:
                return candidate
    return "Leo"


def _is_challenging_event(event: Mapping[str, Any]) -> bool:
    aspect = _coerce_string(event.get("aspect")).lower()
    note = _coerce_string(event.get("note")).lower()
    if any(token in aspect for token in CHALLENGING_ASPECTS):
        return True
    return any(keyword in note for keyword in CHALLENGING_KEYWORDS)


def _event_time_window(event: Mapping[str, Any]) -> str:
    for key in ("time_window", "window", "time", "span", "range"):
        candidate = _strip_emdash(_coerce_string(event.get(key)))
        if candidate:
            return candidate
    start = _strip_emdash(_coerce_string(event.get("start_time")))
    end = _strip_emdash(_coerce_string(event.get("end_time")))
    if start and end:
        return f"{start}-{end}"
    return ""


def _build_caution_window(
    daily: Mapping[str, Any],
    top_events: Sequence[Mapping[str, Any]],
    *,
    fallback_time: str = "14:00-16:00 (afternoon)",
    fallback_note: str = "Use this span for careful review and gentler pacing.",
) -> Dict[str, str]:
    provided = _sanitize_mapping(daily.get("caution_window"))
    note = _strip_emdash(_coerce_string(provided.get("note")))
    time_window = _strip_emdash(_coerce_string(provided.get("time_window")))

    if not time_window or not note:
        candidate = next((event for event in top_events if _is_challenging_event(event)), None)
        if candidate is None and top_events:
            candidate = top_events[0]
        if candidate:
            if not time_window:
                time_window = _event_time_window(candidate)
            if not note:
                raw_note = _strip_emdash(_coerce_string(candidate.get("note")))
                note = _trim_for_display(raw_note, ensure_sentence=True)

    final_time = time_window or fallback_time
    final_note = note or fallback_note
    return {
        "time_window": final_time,
        "note": _ensure_sentence(final_note),
    }


def _format_remedy_text(template: str, *, sign: str, theme: str) -> str:
    tokens = {
        "sign": sign or "your sign",
        "theme": theme or "day",
    }
    text = template.format(**tokens)
    text = _strip_emdash(text)
    return _ensure_sentence(text)


def _fallback_remedies(
    daily: Mapping[str, Any],
    *,
    theme: str,
    top_events: Sequence[Mapping[str, Any]],
) -> List[str]:
    provided = daily.get("remedies")
    cleaned = _sanitize_string_list(provided) if provided else []
    if cleaned:
        return cleaned[:SANITIZED_LIST_LIMIT]

    dominant_body = _dominant_body(top_events)
    dominant_sign = _dominant_sign(top_events)
    theme_token = theme.lower().strip() if theme else "day"
    sign_token = dominant_sign or "your sign"
    templates = remedy_templates_for_planet(dominant_body)
    remedies: List[str] = []
    seen: set[str] = set()
    for template in templates:
        candidate = _format_remedy_text(
            template,
            sign=sign_token,
            theme=theme_token,
        )
        if candidate:
            lowered = candidate.lower()
            if lowered not in seen:
                remedies.append(candidate)
                seen.add(lowered)
        if len(remedies) >= SANITIZED_LIST_LIMIT:
            break
    if not remedies:
        remedies.append(_ensure_sentence("Ground yourself with three steady breaths."))
    return remedies


def _build_fallback(daily: Dict[str, Any]) -> DailyTemplatedResponse:
    meta = daily.get("meta", {})
    focus_areas = daily.get("focus_areas", [])
    top_events = sorted(
        daily.get("top_events", []),
        key=lambda item: (
            -float(item.get("score", 0.0)),
            abs(float(item.get("orb", 99.9))),
        ),
    )
    score = float(top_events[0].get("score", 0.0)) if top_events else 0.0
    mood = _coerce_string(daily.get("mood")) or ("energised" if score >= 7 else "balanced")
    profile = _title_case(meta.get("profile_name"))
    profile_ref = "You" if profile == "You" else profile
    date = meta.get("date") or time.strftime("%Y-%m-%d")

    lucky_details = _sanitize_mapping(daily.get("lucky"))
    lucky_affirmation = _strip_emdash(_coerce_string(lucky_details.get("affirmation")))
    fallback_lucky = {
        "color": _strip_emdash(_coerce_string(lucky_details.get("color"))) or "Deep Red",
        "time_window": _strip_emdash(_coerce_string(lucky_details.get("time_window")))
        or "10:00-12:00",
        "direction": _strip_emdash(_coerce_string(lucky_details.get("direction"))) or "SE",
        "affirmation": lucky_affirmation or "My focus is steady and encouraging.",
    }

    fallback_caution = _build_caution_window(daily, top_events)

    morning_details = _sanitize_mapping(daily.get("morning_mindset"))
    raw_mantra = _strip_emdash(_coerce_string(morning_details.get("mantra")))
    fallback_mantra = _select_distinct_phrase(
        raw_mantra,
        fallback=DEFAULT_MANTRA,
        avoid=fallback_lucky["affirmation"],
        secondary=SECONDARY_MANTRA,
    )

    summary_text = _coerce_string(daily.get("summary"))
    if summary_text:
        stripped_summary = summary_text
        lower_profile = profile.lower()
        lowered_summary = summary_text.lower()
        if lower_profile and lower_profile != "you" and lowered_summary.startswith(lower_profile):
            stripped_summary = summary_text[len(meta.get("profile_name", "")) :].lstrip(", :")
        cleaned_summary = _ensure_sentence(stripped_summary)
    else:
        cleaned_summary = "Stay grounded and move with purpose."
    summary_for_opening = (
        cleaned_summary.replace(profile, profile_ref) if profile != "You" else cleaned_summary
    )

    headline_source = next(
        (
            _coerce_string(area.get("headline"))
            for area in focus_areas
            if _coerce_string(area.get("headline"))
        ),
        "Focused Momentum",
    )
    theme = _trim_for_display(
        headline_source,
        fallback="Focused Momentum",
    ) or "Focused Momentum"

    fallback_remedies = _fallback_remedies(daily, theme=theme, top_events=top_events)

    focus_map: Dict[str, Dict[str, Any]] = {}
    for entry in focus_areas:
        area_key = _coerce_string(entry.get("area")).lower()
        if area_key:
            focus_map[area_key] = entry

    default_career_bullets = [
        "Complete one meaningful task",
        "Clarify expectations",
        "Review priority deadlines",
    ]
    default_finance_bullets = [
        "Review a key number",
        "Delay big purchases",
        "Plan your next savings step",
    ]

    def _focus_details(
        area_key: str,
        default_highlight: str,
        default_guidance: str,
    ) -> tuple[str, List[str], str, str]:
        area_data = focus_map.get(area_key, {})
        headline = _coerce_string(area_data.get("headline")) or default_highlight
        guidance_raw = _coerce_string(area_data.get("guidance")) or default_guidance
        events = area_data.get("events", []) if isinstance(area_data, Mapping) else []
        bullets: List[str] = []
        for event in events:
            if len(bullets) >= SANITIZED_LIST_LIMIT:
                break
            event_map = _sanitize_mapping(event)
            note = _coerce_string(event_map.get("note"))
            if note:
                formatted = _trim_for_display(note, ensure_sentence=True)
            else:
                transit = _coerce_string(event_map.get("transit_body"))
                aspect = _coerce_string(event_map.get("aspect"))
                natal = _coerce_string(event_map.get("natal_body"))
                formatted = f"{transit} {aspect} {natal}".strip()
            if formatted:
                bullets.append(formatted)
        paragraph_source = ". ".join([text for text in (headline, guidance_raw) if text])
        paragraph = _trim_for_display(paragraph_source, ensure_sentence=True)
        return paragraph, bullets, guidance_raw, headline

    career_paragraph_src, career_bullets, career_guidance_raw, career_headline = _focus_details(
        "career",
        theme,
        "Lean on steady progress and keep communication direct.",
    )
    finance_paragraph_src, finance_bullets, finance_guidance_raw, finance_headline = _focus_details(
        "finance",
        theme,
        "Think long-term and sidestep impulse choices.",
    )
    health_paragraph_src, health_notes, health_guidance_raw, health_headline = _focus_details(
        "health",
        theme,
        "Balance effort with rest and hydration.",
    )

    love_data = focus_map.get("love", {})
    love_headline = _coerce_string(love_data.get("headline")) or theme
    love_guidance_raw = _coerce_string(love_data.get("guidance")) or "Lead with sincerity and warmth."
    love_paragraph_src = _trim_for_display(
        ". ".join([text for text in (love_headline, love_guidance_raw) if text]),
        ensure_sentence=True,
    )

    if not health_notes:
        health_notes = list(DEFAULT_HEALTH_NOTES)

    positive_aspects = {"conjunction", "trine", "sextile"}
    challenging_aspects = {"square", "opposition", "quincunx"}
    do_today: List[str] = []
    avoid_today: List[str] = []
    for event in daily.get("events", []):
        if len(do_today) >= SANITIZED_LIST_LIMIT and len(avoid_today) >= SANITIZED_LIST_LIMIT:
            break
        event_map = _sanitize_mapping(event)
        aspect = _coerce_string(event_map.get("aspect")).lower()
        phrase = _coerce_string(event_map.get("note"))
        if not phrase:
            transit = _coerce_string(event_map.get("transit_body"))
            natal = _coerce_string(event_map.get("natal_body"))
            phrase = f"Focus on the {transit} {aspect} {natal} influence".strip()
        formatted_phrase = _trim_for_display(phrase, ensure_sentence=True)
        if aspect in positive_aspects and len(do_today) < SANITIZED_LIST_LIMIT:
            do_today.append(formatted_phrase)
        elif aspect in challenging_aspects and len(avoid_today) < SANITIZED_LIST_LIMIT:
            avoid_today.append(formatted_phrase)

    if not do_today:
        do_today = [
            "Focus on one priority",
            "Speak kindly",
            "Move your body",
            "Hydrate intentionally",
        ]
    if not avoid_today:
        avoid_today = [
            "Overcommitting",
            "Power struggles",
            "Doomscrolling",
            "Impulse spending",
        ]

    option_b_payload: Dict[str, Any] = {
        "profile_name": profile,
        "date": date,
        "mood": mood,
        "theme": theme,
        "opening_summary": summary_for_opening,
        "morning_mindset": {
            "paragraph": summary_for_opening,
            "mantra": fallback_mantra,
        },
        "career": {"paragraph": career_paragraph_src, "bullets": career_bullets},
        "love": {"paragraph": love_paragraph_src, "attached": "", "single": ""},
        "health": {"paragraph": health_paragraph_src, "good_options": health_notes[:SANITIZED_LIST_LIMIT]},
        "finance": {"paragraph": finance_paragraph_src, "bullets": finance_bullets},
        "do_today": do_today,
        "avoid_today": avoid_today,
        "lucky": fallback_lucky,
        "one_line_summary": summary_for_opening,
        "events": daily.get("events", []),
        "top_events": top_events,
        "focus_areas": focus_areas,
    }

    try:
        ctx = build_context(option_b_payload)
        career_story_bullets = list(ctx.get("career_bullets", [])) or career_bullets or default_career_bullets
        finance_story_bullets = list(ctx.get("finance_bullets", [])) or finance_bullets or default_finance_bullets
        health_story_options = list(ctx.get("health_opts", [])) or health_notes or list(DEFAULT_HEALTH_NOTES)
        love_attached_story = ctx.get("love_attached") or "If you're attached, you lean into rituals that feel supportive and sincere."
        love_single_story = ctx.get("love_single") or "If you're single, you follow conversations that feel naturally aligned."
        do_today_story = list(ctx.get("do_today", [])) or do_today
        avoid_today_story = list(ctx.get("avoid_today", [])) or avoid_today

        storylet_payload = {
            "profile_name": ctx.get("profile_name", profile),
            "date": ctx.get("date", date),
            "mood": ctx.get("mood", mood),
            "theme": ctx.get("theme", theme),
            "opening_summary": ctx.get("opening_summary", summary_for_opening),
            "morning_mindset": {
                "paragraph": ctx.get("morning_paragraph", summary_for_opening),
                "mantra": _select_distinct_phrase(
                    _strip_emdash(_coerce_string(ctx.get("mantra"))),
                    fallback=fallback_mantra,
                    avoid=fallback_lucky["affirmation"],
                    secondary=SECONDARY_MANTRA,
                ),
            },
            "career": {
                "paragraph": ctx.get("career_paragraph", career_paragraph_src),
                "bullets": career_story_bullets[:SANITIZED_LIST_LIMIT],
            },
            "love": {
                "paragraph": ctx.get("love_paragraph", love_paragraph_src),
                "attached": love_attached_story,
                "single": love_single_story,
            },
            "health": {
                "paragraph": ctx.get("health_paragraph", health_paragraph_src),
                "good_options": health_story_options[:SANITIZED_LIST_LIMIT],
            },
            "finance": {
                "paragraph": ctx.get("finance_paragraph", finance_paragraph_src),
                "bullets": finance_story_bullets[:SANITIZED_LIST_LIMIT],
            },
            "do_today": do_today_story[:SANITIZED_LIST_LIMIT],
            "avoid_today": avoid_today_story[:SANITIZED_LIST_LIMIT],
            "caution_window": ctx.get("caution_window") or fallback_caution,
            "remedies": (ctx.get("remedies") or fallback_remedies)[:SANITIZED_LIST_LIMIT],
            "lucky": ctx.get("lucky") or fallback_lucky,
            "one_line_summary": ctx.get("one_line_summary", summary_for_opening),
        }
        return DailyTemplatedResponse.model_validate(storylet_payload)
    except Exception:
        logger.exception(
            "daily_template_storylet_fallback_failed",
            extra={"profile": profile, "date": date},
        )

    love_guidance_clean = love_guidance_raw.replace("You", profile_ref)
    love_context = {
        "profile_ref": profile_ref,
        "highlight": love_headline,
        "guidance": love_guidance_clean,
        "guidance_clause": _guidance_clause(love_guidance_raw),
    }

    def _legacy_focus(area_key: str, headline: str, guidance_raw: str, default_paragraph: str) -> str:
        guidance_clean = guidance_raw.replace("You", profile_ref)
        return _render_from_templates(
            FOCUS_PARAGRAPH_TEMPLATES.get(area_key, FOCUS_PARAGRAPH_TEMPLATES["default"]),
            {
                "profile_ref": profile_ref,
                "area_label": area_key.capitalize(),
                "highlight": headline or theme,
                "guidance": guidance_clean,
                "guidance_clause": _guidance_clause(guidance_raw),
            },
            default_paragraph,
        )

    career_paragraph = _legacy_focus(
        "career",
        career_headline,
        career_guidance_raw,
        "Lean on steady progress and keep communication direct.",
    )
    finance_paragraph = _legacy_focus(
        "finance",
        finance_headline,
        finance_guidance_raw,
        "Think long-term and sidestep impulse choices.",
    )
    health_paragraph = _legacy_focus(
        "health",
        health_headline,
        health_guidance_raw,
        "Balance effort with rest and hydration.",
    )

    love_paragraph = _render_from_templates(
        LOVE_PARAGRAPH_TEMPLATES,
        love_context,
        "Lead with sincerity and warmth.",
    )
    love_attached = _render_from_templates(
        LOVE_ATTACHED_TEMPLATES,
        love_context,
        "If you're attached, offer one honest appreciation to your partner.",
    )
    love_single = _render_from_templates(
        LOVE_SINGLE_TEMPLATES,
        love_context,
        "If you're single, let conversations unfold without rushing the outcome.",
    )

    lucky_affirmation = fallback_lucky["affirmation"]
    mantra_source = fallback_mantra or DEFAULT_MANTRA
    opening_summary = _render_from_templates(
        OPENING_SUMMARY_TEMPLATES,
        {
            "profile_ref": profile_ref,
            "date": date,
            "theme": theme,
            "summary": summary_for_opening,
        },
        summary_for_opening,
    )
    morning_paragraph = _render_from_templates(
        MORNING_PARAGRAPH_TEMPLATES,
        {
            "profile_ref": profile_ref,
            "theme": theme,
        },
        f"{profile_ref} can set the tone by taking one intentional pause before the day begins.",
    )
    morning_mantra = _render_from_templates(
        MORNING_MANTRA_TEMPLATES,
        {
            "affirmation": mantra_source,
            "theme": theme,
        },
        mantra_source,
        ensure_sentence_output=False,
    ) or mantra_source

    one_line_summary = _trim_for_display(
        opening_summary,
        fallback=opening_summary,
        ensure_sentence=True,
    )

    career_bullet_lines = normalize_bullets(
        career_bullets or default_career_bullets,
        profile,
        area="career",
    ) or normalize_bullets(default_career_bullets, profile, area="career")

    finance_bullet_lines = normalize_bullets(
        finance_bullets or default_finance_bullets,
        profile,
        area="finance",
    ) or normalize_bullets(default_finance_bullets, profile, area="finance")

    health_option_lines = normalize_bullets(
        health_notes or list(DEFAULT_HEALTH_NOTES),
        profile,
        area="health",
    ) or normalize_bullets(list(DEFAULT_HEALTH_NOTES), profile, area="health")

    do_today_lines = normalize_bullets(
        do_today,
        profile,
        area="general",
    ) or normalize_bullets(
        [
            "Focus on one priority",
            "Speak kindly",
            "Move your body",
            "Hydrate intentionally",
        ],
        profile,
        area="general",
    )

    positive_roots = collect_bullet_roots(
        career_bullet_lines + health_option_lines + finance_bullet_lines + do_today_lines
    )

    avoid_today_lines = normalize_avoid(
        avoid_today,
        profile,
        area="general",
        forbidden_roots=positive_roots,
    )

    fallback_payload = {
        "profile_name": profile,
        "date": date,
        "mood": mood,
        "theme": theme,
        "opening_summary": opening_summary,
        "morning_mindset": {
            "paragraph": morning_paragraph,
            "mantra": morning_mantra,
        },
        "career": {
            "paragraph": career_paragraph,
            "bullets": career_bullet_lines,
        },
        "love": {
            "paragraph": love_paragraph,
            "attached": love_attached,
            "single": love_single,
        },
        "health": {
            "paragraph": health_paragraph,
            "good_options": health_option_lines,
        },
        "finance": {
            "paragraph": finance_paragraph,
            "bullets": finance_bullet_lines,
        },
        "do_today": do_today_lines,
        "avoid_today": avoid_today_lines,
        "caution_window": fallback_caution,
        "remedies": fallback_remedies,
        "lucky": fallback_lucky,
        "one_line_summary": one_line_summary,
    }
    return DailyTemplatedResponse.model_validate(fallback_payload)


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
        "Respond with a single JSON object that matches the required schema exactly. "
        "Do not add commentary, code fences, or explanations. "
        "Each list must contain no more than four concise items. "
        "If information is missing, acknowledge it honestly without fabrication."
    )

    user_lines = [
        f"TEMPLATE_VERSION={TEMPLATE_VERSION}",
        f"LANG={TEMPLATE_LANG}",
        f"MODEL={TEMPLATE_MODEL}",
        "- Respond with raw JSON only (no code fences).",
        "- Top-level keys must be exactly: profile_name, date, mood, theme, opening_summary,",
        "  morning_mindset, career, love, health, finance, do_today, avoid_today, caution_window, remedies, lucky, one_line_summary.",
        "- Use meta.profile_name (Title Case) and meta.date.",
        "- morning_mindset must be an object with: {paragraph: string, mantra: string}",
        "- career must be an object with: {paragraph: string, bullets: [up to 4 strings]}",
        "- love must be an object with: {paragraph: string, attached: string, single: string}",
        "- health must be an object with: {paragraph: string, good_options: [up to 4 strings]}",
        "- finance must be an object with: {paragraph: string, bullets: [up to 4 strings]}",
        "- do_today and avoid_today must be arrays with up to 4 short strings each.",
        "- caution_window must be an object with: {time_window: string, note: string}",
        "- remedies must be an array with up to 4 short strings.",
        "- lucky must be an object with: {color: string, time_window: string, direction: string, affirmation: string}",
        "- Use EXACTLY these field names. Do not use bullet_points, use bullets. Do not omit required fields.",
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
    use_ai: bool = False,
) -> DailyTemplateResult:
    _, content_hash, etag = _stable_bundle(daily_payload)
    date = daily_payload.get("meta", {}).get("date", "unknown")
    
    # Check for generation_mode parameter
    meta = daily_payload.get("meta", {})
    generation_mode = meta.get("generation_mode", "").strip().lower()
    
    # Determine if we should use AI mini composer
    use_ai_mini = (generation_mode == "ai_mini" and not use_ai)
    
    # DEBUG: Log AI mini composer decision
    logger.info(f"AI mini composer check: generation_mode={generation_mode!r}, use_ai={use_ai}, use_ai_mini={use_ai_mini}")
    
    # Update cache key to include generation mode
    mode_suffix = ":ai_mini" if use_ai_mini else (":ai_full" if use_ai else ":template")
    cache_key = f"dailyTpl:{date}:{TEMPLATE_LANG}:{TEMPLATE_VERSION}:{TEMPLATE_MODEL}:{content_hash}{mode_suffix}"
    lock_key = f"lock:{cache_key}"

    use_ai_pref = meta.get("use_ai")
    if isinstance(use_ai_pref, str):
        normalized = use_ai_pref.strip().lower()
        use_ai = normalized in {"1", "true", "yes", "on"}
    elif use_ai_pref is None:
        use_ai = True
    else:
        use_ai = bool(use_ai_pref)

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

    llm_client = _get_openai_client() if use_ai else None
    validation_errors: List[str] = []
    llm_tokens: Optional[int] = None
    generated_payload: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None

    # NEW: Try AI mini composer if enabled
    if use_ai_mini:
        logger.info(f"[AI_MINI] Entering AI mini composer block for {date}")
        try:
            # Import here to avoid circular dependencies
            from .ai_composer import compose_daily_forecast_parallel
            
            # Build template context first as fallback data
            logger.info(f"[AI_MINI] Attempting AI mini composer for {date}")
            
            # Extract necessary variables from daily_payload (same as _build_storylet)
            daily = daily_payload
            meta = daily.get("meta", {})
            top_events = daily.get("top_events", [])
            focus_areas = daily.get("focus_areas", [])
            
            # Extract profile info
            profile = _title_case(meta.get("profile_name"))
            
            # Extract mood, theme, and other base data
            score = float(top_events[0].get("score", 0.0)) if top_events else 0.0
            mood = _coerce_string(daily.get("mood")) or ("energised" if score >= 7 else "balanced")
            
            # Extract proper theme from focus_areas (same as legacy _build_storylet)
            headline_source = next(
                (
                    _coerce_string(area.get("headline"))
                    for area in focus_areas
                    if _coerce_string(area.get("headline"))
                ),
                "Focused Momentum",
            )
            theme = _trim_for_display(
                headline_source,
                fallback="Focused Momentum",
            ) or "Focused Momentum"
            
            summary_for_opening = _coerce_string(daily.get("summary")) or "Stay present with the day."
            
            # Build simplified fallbacks for sections
            fallback_mantra = "I choose what strengthens me."
            career_paragraph_src = "Focus on your work priorities today."
            love_paragraph_src = "Notice the emotional tone in your relationships."
            health_paragraph_src = "Pay attention to your body's signals."
            finance_paragraph_src = "Review your resources mindfully."
            career_bullets = ["Track your key tasks", "Communicate clearly with colleagues"]
            finance_bullets = ["Monitor your spending", "Review upcoming expenses"]
            health_notes = ["Rest when needed", "Move your body gently"]
            do_today = ["Focus on one priority", "Speak kindly"]
            avoid_today = ["Overcommitting", "Reactive conversations"]
            fallback_lucky = {
                "color": "Soft Rose",
                "time_window": "Morning hours",
                "direction": "East",
                "affirmation": "I attract harmony and support."
            }
            
            # Build option_b_payload with pre-populated sections (same as legacy path)
            option_b_payload_for_ai: Dict[str, Any] = {
                "profile_name": profile,
                "date": date,
                "mood": mood,
                "theme": theme,
                "opening_summary": summary_for_opening,
                "morning_mindset": {
                    "paragraph": summary_for_opening,
                    "mantra": fallback_mantra,
                },
                "career": {"paragraph": career_paragraph_src, "bullets": career_bullets},
                "love": {"paragraph": love_paragraph_src, "attached": "", "single": ""},
                "health": {"paragraph": health_paragraph_src, "good_options": health_notes},
                "finance": {"paragraph": finance_paragraph_src, "bullets": finance_bullets},
                "do_today": do_today,
                "avoid_today": avoid_today,
                "lucky": fallback_lucky,
                "one_line_summary": summary_for_opening,
                "events": daily.get("events", []),
                "top_events": top_events,
                "focus_areas": focus_areas,
            }
            
            template_context = build_context(option_b_payload_for_ai)
            
            # Use asyncio to run the parallel composer
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                ai_result = loop.run_until_complete(
                    compose_daily_forecast_parallel(
                        template_context=template_context,
                        profile_name=meta.get("profile_name", "User"),
                        forecast_date=date,
                    )
                )
                if ai_result is not None:
                    generated_payload = ai_result.model_dump(mode="json")
                    logger.info(f"AI mini composer succeeded for {date}")
                else:
                    logger.warning(f"AI mini composer returned None, falling back to templates for {date}")
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"AI mini composer failed: {e}, falling back to templates")
            # Continue to template fallback below

    if llm_client is not None and use_ai and not use_ai_mini:
        parsed, raw_response, llm_tokens = _render_with_llm(llm_client, daily_payload)
        if parsed is not None:
            sanitized = _sanitize_payload(parsed)
            is_valid, validation_errors = _validate_payload(sanitized)
            if is_valid:
                try:
                    generated_payload = (
                        DailyTemplatedResponse.model_validate(sanitized).model_dump(mode="json")
                    )
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
                sanitized_retry = _sanitize_payload(parsed_retry)
                is_valid, validation_errors = _validate_payload(sanitized_retry)
                if is_valid:
                    try:
                        generated_payload = (
                            DailyTemplatedResponse.model_validate(sanitized_retry).model_dump(mode="json")
                        )
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

    if generated_payload is not None:
        try:
            enriched_payload = _apply_special_sky_events(generated_payload, daily_payload)
            generated_payload = (
                DailyTemplatedResponse.model_validate(enriched_payload).model_dump(mode="json")
            )
        except Exception:
            logger.exception(
                "daily_template_special_events_merge_failed",
                extra={"date": date},
            )

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
