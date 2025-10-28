from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .clean import clean_token_phrase


_PHASE_WORD_RE = re.compile(r"\b(applying|separating)\b", re.I)
_PHASE_LABEL_SEPARATOR = r"[:=\-\u2013\u2014]"
_PHASE_LABEL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        rf"\b(?:phase|status)\b\s*(?:{_PHASE_LABEL_SEPARATOR}|is|are)?\s*(applying|separating)\b",
        re.I,
    ),
    re.compile(
        rf"\bapplying\s*/\s*separating\b\s*(?:{_PHASE_LABEL_SEPARATOR}|is|are)?\s*(applying|separating)\b",
        re.I,
    ),
)


_ASPECT_STYLES: Mapping[str, tuple[str, str]] = {
    "conjunction": ("aligns with", "conjunction"),
    "sextile": ("supports", "supportive sextile"),
    "square": ("presses on", "square alignment"),
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


def _format_orb(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{abs(number):.2f}° orb"


def _phase_from_text(note: str) -> str:
    for pattern in _PHASE_LABEL_PATTERNS:
        match = pattern.search(note)
        if match:
            return match.group(1).lower()

    matches: list[re.Match[str]] = []
    for match in _PHASE_WORD_RE.finditer(note):
        before = note[: match.start()]
        after = note[match.end() :]
        if re.match(r"\s*/", after):
            continue
        if before.rstrip().endswith("/"):
            continue
        matches.append(match)

    if not matches:
        return ""

    first = matches[0].group(1).lower()
    return first


def _aspect_phase(event: Mapping[str, Any]) -> str:
    applying = event.get("applying")
    if isinstance(applying, bool):
        return "applying" if applying else "separating"
    note = event.get("note")
    if isinstance(note, str):
        phase = _phase_from_text(note)
        if phase:
            return phase
        cleaned = clean_token_phrase(note)
        phase = _phase_from_text(cleaned)
        if phase:
            return phase
    return ""


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


_SEXTILE_VERBS = ("supports", "boosts", "opens", "facilitates")


def _aspect_verb(event: Mapping[str, Any]) -> str:
    key = str(event.get("aspect") or "").strip().lower()
    if key == "sextile":
        seed_parts = [
            "sextile",
            str(event.get("transit_body") or ""),
            str(event.get("natal_body") or ""),
            str(event.get("natal_house") or ""),
        ]
        digest = hashlib.sha256("|".join(seed_parts).encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(_SEXTILE_VERBS)
        return _SEXTILE_VERBS[index]
    return _aspect_details(key)[0]


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


def _sign_clause(event: Mapping[str, Any]) -> str:
    transit = _sanitize_name(event.get("transit_sign"))
    natal = _sanitize_name(event.get("natal_sign"))
    if transit and natal:
        if transit == natal:
            return f"in {transit}"
        return f"from {transit} to {natal}"
    if transit:
        return f"in {transit}"
    if natal:
        return f"in {natal}"
    return ""


SAFE_DESCRIPTOR_WHITELIST: Mapping[str, Callable[[Mapping[str, Any]], str]] = {
    "transit_body": lambda event: _sanitize_name(event.get("transit_body")),
    "natal_body": lambda event: _sanitize_name(event.get("natal_body")),
    "transit_sign": lambda event: _sanitize_name(event.get("transit_sign")),
    "natal_sign": lambda event: _sanitize_name(event.get("natal_sign")),
    "aspect": lambda event: _sanitize_lower(event.get("aspect")),
    "aspect_verb": _aspect_verb,
    "aspect_family": lambda event: _aspect_details(event.get("aspect"))[1],
    "aspect_phase": _aspect_phase,
    "orb_text": lambda event: _format_orb(event.get("orb")),
    "sign_clause": _sign_clause,
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
_SOFT_H_PREFIXES = {"honest", "honor", "honour", "hour", "herb"}
_HARD_VOWEL_PREFIXES = {"one", "once", "united", "unicorn", "euro", "use", "user"}
_ARTICLE_PATTERN = re.compile(r"\b([Aa]n?)\s+([A-Za-z][A-Za-z'\-]*)")


def _indefinite_article(word: str) -> str:
    if not word:
        return "a"
    lowered = word.lower()
    if any(lowered.startswith(prefix) for prefix in _SOFT_H_PREFIXES):
        return "an"
    if lowered[0] in "aeiou":
        if any(lowered.startswith(prefix) for prefix in _HARD_VOWEL_PREFIXES):
            return "a"
        return "an"
    return "a"


def _fix_indefinite_articles(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        article, word = match.group(1), match.group(2)
        desired = _indefinite_article(word)
        if desired == article.lower():
            return match.group(0)
        replacement = desired.capitalize() if article[0].isupper() else desired
        return f"{replacement} {word}"

    return _ARTICLE_PATTERN.sub(repl, text)


def _normalize_sentence(text: str) -> str:
    text = _WHITESPACE.sub(" ", text).strip()
    text = text.replace(" ,", ",").replace(" .", ".")
    text = re.sub(r"\s+—\s+", " — ", text)
    return _fix_indefinite_articles(text)


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
        "{transit_body} {aspect_verb} your {natal_body} {sign_clause}—an {aspect_phase} {aspect_family} at {orb_text}",
        (
            "transit_body",
            "aspect_verb",
            "natal_body",
            "sign_clause",
            "aspect_phase",
            "aspect_family",
            "orb_text",
        ),
    ),
    MiniTemplate(
        "{transit_body} {aspect_verb} your {natal_body}—an {aspect_phase} {aspect_family} at {orb_text}",
        (
            "transit_body",
            "aspect_verb",
            "natal_body",
            "aspect_phase",
            "aspect_family",
            "orb_text",
        ),
    ),
    MiniTemplate(
        "{transit_body} {aspect_verb} your {natal_body}—an {aspect_family} at {orb_text}",
        (
            "transit_body",
            "aspect_verb",
            "natal_body",
            "aspect_family",
            "orb_text",
        ),
    ),
    MiniTemplate(
        "{transit_body} {aspect_verb} your {natal_body}—an {aspect_phase} {aspect_family}",
        (
            "transit_body",
            "aspect_verb",
            "natal_body",
            "aspect_phase",
            "aspect_family",
        ),
    ),
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

