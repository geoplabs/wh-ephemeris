from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .clean import clean_token_phrase


_ASPECT_STYLES: Mapping[str, tuple[str, str]] = {
    "conjunction": ("aligns with", "harmonizing conjunction"),
    "sextile": ("supports", "supportive sextile"),
    "square": ("presses on", "pressing square"),
    "trine": ("flows with", "flowing trine"),
    "opposition": ("balances", "balancing opposition"),
}
_ASPECT_FALLBACK = ("activates", "dynamic aspect")

_ORDINAL_CACHE: dict[int, str] = {}


def _ordinal(n: int) -> str:
    if n in _ORDINAL_CACHE:
        return _ORDINAL_CACHE[n]
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    value = f"{n}{suffix}"
    _ORDINAL_CACHE[n] = value
    return value


def _sanitize_name(value: Any) -> str:
    phrase = clean_token_phrase(value)
    return phrase


def _sanitize_lower(value: Any) -> str:
    phrase = clean_token_phrase(value)
    return phrase.lower() if phrase else ""


def _house_label(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return ""
    if number < 1 or number > 12:
        return ""
    return f"{_ordinal(number)} house"


def _aspect_details(value: Any) -> tuple[str, str]:
    key = str(value or "").strip().lower()
    return _ASPECT_STYLES.get(key, _ASPECT_FALLBACK)


def _event_focus(value: Any) -> str:
    if isinstance(value, str):
        return clean_token_phrase(value)
    if isinstance(value, (list, tuple)):
        for item in value:
            focus = clean_token_phrase(item)
            if focus:
                return focus
    return ""


def _transit_influence(event: Mapping[str, Any]) -> str:
    body = _sanitize_name(event.get("transit_body"))
    if not body:
        return ""
    return f"{body} influence"


SAFE_DESCRIPTOR_WHITELIST: Mapping[str, Callable[[Mapping[str, Any]], str]] = {
    "transit_body": lambda event: _sanitize_name(event.get("transit_body")),
    "natal_body": lambda event: _sanitize_name(event.get("natal_body")),
    "transit_sign": lambda event: _sanitize_name(event.get("transit_sign")),
    "natal_sign": lambda event: _sanitize_name(event.get("natal_sign")),
    "aspect": lambda event: _sanitize_lower(event.get("aspect")),
    "aspect_verb": lambda event: _aspect_details(event.get("aspect"))[0],
    "aspect_family": lambda event: _aspect_details(event.get("aspect"))[1],
    "natal_house_label": lambda event: _house_label(event.get("natal_house")),
    "event_focus": lambda event: _event_focus(
        event.get("focus_label")
        or event.get("focus")
        or event.get("focus_area")
        or event.get("dominant_focus")
        or event.get("primary_focus")
    ),
    "transit_influence": _transit_influence,
}


def safe_event_tokens(event: Mapping[str, Any] | None) -> dict[str, str]:
    """Return sanitized tokens from ``event`` based on the descriptor whitelist."""

    if not isinstance(event, Mapping):
        return {}
    tokens: dict[str, str] = {}
    for key, resolver in SAFE_DESCRIPTOR_WHITELIST.items():
        value = resolver(event)
        if not value:
            continue
        text = str(value).strip()
        if text:
            tokens[key] = text
    return tokens


@dataclass(frozen=True)
class MiniTemplate:
    template: str
    required: tuple[str, ...] = ()


class _SafeTokens(dict[str, str]):
    def __missing__(self, key: str) -> str:  # pragma: no cover - handled via defaults
        return ""


_WHITESPACE = re.compile(r"\s+")


def _normalize_sentence(text: str) -> str:
    text = _WHITESPACE.sub(" ", text).strip()
    text = text.replace(" ,", ",").replace(" .", ".")
    text = re.sub(r"\s+—\s+", " — ", text)
    return text


def render_mini_template(templates: Sequence[MiniTemplate], tokens: Mapping[str, Any]) -> str:
    """Render the first matching template using ``tokens``.

    Any template whose required keys are missing or blank is skipped.
    """

    prepared: dict[str, str] = {}
    for key, value in tokens.items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            prepared[key] = text
    safe = _SafeTokens(prepared)
    for tmpl in templates:
        if all(safe[key] for key in tmpl.required):
            rendered = tmpl.template.format_map(safe)
            return _normalize_sentence(rendered)
    return ""


DEFAULT_EVENT_TEMPLATES: tuple[MiniTemplate, ...] = (
    MiniTemplate(
        "{transit_body} {aspect_verb} your {natal_body} in the {natal_house_label}—a {aspect_family} influence",
        ("transit_body", "aspect_verb", "natal_body", "natal_house_label", "aspect_family"),
    ),
    MiniTemplate(
        "{transit_body} {aspect_verb} your {natal_body}—a {aspect_family} influence",
        ("transit_body", "aspect_verb", "natal_body", "aspect_family"),
    ),
    MiniTemplate(
        "{transit_body} activates your {natal_house_label}",
        ("transit_body", "natal_house_label"),
    ),
    MiniTemplate("{transit_influence}", ("transit_influence",)),
)


def event_phrase(
    event: Mapping[str, Any] | None,
    extra_templates: Sequence[MiniTemplate] | None = None,
) -> str:
    """Return a sanitized phrase summarizing ``event``."""

    tokens = safe_event_tokens(event)
    if not tokens:
        return ""
    templates: list[MiniTemplate] = []
    if extra_templates:
        templates.extend(extra_templates)
    templates.extend(DEFAULT_EVENT_TEMPLATES)
    phrase = render_mini_template(templates, tokens)
    return phrase

