"""Scoring helpers for matching transit events to forecast areas."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

DEFAULT_AREAS: tuple[str, ...] = ("career", "love", "health", "finance")

ASPECT_WEIGHTS: Mapping[str, float] = {
    "conjunction": 1.2,
    "square": 1.0,
    "opposition": 1.0,
    "trine": 0.85,
    "sextile": 0.75,
}
DEFAULT_ASPECT_WEIGHT = 0.65

HOUSE_TO_AREAS: Mapping[int, Sequence[str]] = {
    1: ("health",),
    2: ("finance",),
    5: ("love",),
    6: ("health",),
    7: ("love",),
    8: ("finance",),
    9: ("career",),
    10: ("career",),
    11: ("career",),
    12: ("health",),
}

BODY_TO_AREAS: Mapping[str, Sequence[str]] = {
    "Sun": ("career",),
    "Moon": ("love", "health"),
    "Mercury": ("career",),
    "Venus": ("love", "finance"),
    "Mars": ("career", "health"),
    "Jupiter": ("career", "finance"),
    "Saturn": ("career",),
    "Uranus": ("career",),
    "Neptune": ("love",),
    "Pluto": ("career", "finance"),
    "Chiron": ("health", "love"),
    "TrueNode": ("career",),
    "Midheaven": ("career",),
    "Ascendant": ("health",),
}

FOCUS_KEYWORDS: Mapping[str, str] = {
    "career": "career",
    "work": "career",
    "ambition": "career",
    "purpose": "career",
    "relationship": "love",
    "relationships": "love",
    "love": "love",
    "heart": "love",
    "family": "love",
    "health": "health",
    "wellness": "health",
    "body": "health",
    "vitality": "health",
    "finance": "finance",
    "finances": "finance",
    "money": "finance",
    "resources": "finance",
    "abundance": "finance",
}

TAG_TO_AREAS: Mapping[str, str] = {
    "career": "career",
    "ambition": "career",
    "work": "career",
    "discipline": "career",
    "love": "love",
    "relationships": "love",
    "family": "love",
    "connection": "love",
    "health": "health",
    "routine": "health",
    "vitality": "health",
    "healing": "health",
    "body": "health",
    "money": "finance",
    "resources": "finance",
    "stability": "finance",
}

SOURCE_WEIGHTS: Mapping[str, float] = {
    "house": 1.2,
    "focus": 1.5,
    "body": 0.7,
    "tag": 0.5,
}

_FOCUS_FIELDS = (
    "focus",
    "focus_area",
    "focus_label",
    "dominant_focus",
    "primary_focus",
)


def _aspect_weight(event: Mapping[str, Any]) -> float:
    aspect = str(event.get("aspect") or "").lower()
    return ASPECT_WEIGHTS.get(aspect, DEFAULT_ASPECT_WEIGHT)


def _event_strength(event: Mapping[str, Any]) -> float:
    try:
        raw_score = float(event.get("score") or 0.0)
    except (TypeError, ValueError):
        raw_score = 0.0
    strength = abs(raw_score) * _aspect_weight(event)
    return round(strength, 4)


def _iter_focus_labels(event: Mapping[str, Any]) -> Iterable[str]:
    for field in _FOCUS_FIELDS:
        value = event.get(field)
        if not value:
            continue
        if isinstance(value, str):
            yield value
        elif isinstance(value, Iterable):
            for item in value:
                if item:
                    yield str(item)


def _focus_area_from_label(label: str) -> str | None:
    lowered = label.strip().lower()
    for keyword, area in FOCUS_KEYWORDS.items():
        if keyword in lowered:
            return area
    return None


def _areas_from_body(body: Any) -> Sequence[str]:
    if not body:
        return ()
    return BODY_TO_AREAS.get(str(body), ())


def _areas_from_tags(tags: Iterable[Any]) -> Sequence[str]:
    results: list[str] = []
    for tag in tags or ():
        lowered = str(tag).lower()
        area = TAG_TO_AREAS.get(lowered)
        if area and area not in results:
            results.append(area)
    return tuple(results)


def annotate_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return a shallow-copied list of events annotated with area hints."""

    annotated: list[dict[str, Any]] = []
    for event in events or []:
        copied = dict(event)
        area_sources: dict[str, set[str]] = {}

        natal_house = copied.get("natal_house")
        if isinstance(natal_house, int):
            for area in HOUSE_TO_AREAS.get(natal_house, ()):  # type: ignore[arg-type]
                area_sources.setdefault(area, set()).add("house")

        for label in _iter_focus_labels(copied):
            focus_area = _focus_area_from_label(label)
            if focus_area:
                area_sources.setdefault(focus_area, set()).add("focus")
                copied.setdefault("focus_area", focus_area)

        for key in ("transit_body", "natal_body"):
            for area in _areas_from_body(copied.get(key)):
                area_sources.setdefault(area, set()).add("body")

        tags = copied.get("tags")
        if isinstance(tags, (list, tuple, set)):
            for area in _areas_from_tags(tags):
                area_sources.setdefault(area, set()).add("tag")

        copied["area_hints"] = {area: sorted(sources) for area, sources in area_sources.items()}
        annotated.append(copied)
    return annotated


def _candidate(
    event: Mapping[str, Any],
    area: str,
    sources: Iterable[str],
    *,
    fallback: bool = False,
) -> dict[str, Any] | None:
    normalized_sources = sorted(set(sources))
    if not fallback and not normalized_sources:
        return None
    strength = _event_strength(event)
    relevance = sum(SOURCE_WEIGHTS.get(source, 0.4) for source in normalized_sources)
    if relevance and strength < 5.0:
        strength = 5.0
    total = strength + relevance * 25.0
    candidate = {
        "area": area,
        "event": event,
        "strength": round(strength, 4),
        "relevance": round(relevance, 4),
        "score": round(total, 4),
        "sources": normalized_sources,
    }
    if fallback:
        candidate["is_fallback"] = True
    return candidate


def rank_events_by_area(
    events: Iterable[Mapping[str, Any]],
    *,
    areas: Sequence[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Annotate and score events for each forecast area.

    Returns a tuple of (annotated_events, rankings_by_area).
    """

    annotated = annotate_events(events)
    target_areas = tuple(areas) if areas else DEFAULT_AREAS
    rankings: dict[str, list[dict[str, Any]]] = {area: [] for area in target_areas}

    for event in annotated:
        hints = event.get("area_hints") or {}
        focus_area = event.get("focus_area")
        for area in target_areas:
            sources = set(hints.get(area, []))
            if focus_area == area:
                sources.add("focus")
            candidate = _candidate(event, area, sources)
            if candidate:
                rankings[area].append(candidate)

    for area, candidates in rankings.items():
        candidates.sort(key=lambda item: (item["score"], item["strength"]), reverse=True)
        if not candidates and annotated:
            fallback_event = max(annotated, key=_event_strength)
            fallback = _candidate(fallback_event, area, (), fallback=True)
            if fallback:
                rankings[area].append(fallback)

    return annotated, rankings


def summarize_rankings(rankings: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Serialize rankings so downstream callers can rely on plain dicts."""

    summary: dict[str, dict[str, Any]] = {}
    for area, candidates in rankings.items():
        serialized: list[dict[str, Any]] = []
        for candidate in candidates:
            payload = {
                "area": candidate.get("area", area),
                "event": candidate.get("event"),
                "strength": candidate.get("strength", 0.0),
                "relevance": candidate.get("relevance", 0.0),
                "score": candidate.get("score", 0.0),
                "sources": list(candidate.get("sources", [])),
            }
            if candidate.get("is_fallback"):
                payload["is_fallback"] = True
            serialized.append(payload)
        summary[area] = {
            "selected": serialized[0] if serialized else None,
            "ranking": serialized,
        }
    return summary
