"""Scoring helpers for matching transit events to forecast areas."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from src.content.archetype_router import classify_event

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
    1: ("health", "career"),
    2: ("finance", "career"),
    3: ("career", "health"),
    4: ("love", "health"),
    5: ("love", "career"),
    6: ("health", "career"),
    7: ("love", "finance"),
    8: ("finance", "love"),
    9: ("career", "love"),
    10: ("career", "finance"),
    11: ("career", "finance"),
    12: ("health", "spiritual"),
}

AREA_FALLBACK_HOUSES: Mapping[str, Sequence[int]] = {
    "career": (10, 6, 11, 2, 9, 1),
    "love": (7, 5, 11, 4, 8),
    "health": (6, 1, 12, 3, 2),
    "finance": (2, 8, 10, 11, 5),
}

BODY_TO_AREAS: Mapping[str, Sequence[str]] = {
    "Sun": ("career",),
    "Moon": ("love", "health"),
    "Mercury": ("career", "finance"),
    "Venus": ("love", "finance"),
    "Mars": ("career", "health"),
    "Jupiter": ("career", "finance"),
    "Saturn": ("career", "finance"),
    "Uranus": ("career", "love"),
    "Neptune": ("love", "spiritual"),
    "Pluto": ("career", "finance", "love"),
    "Chiron": ("health", "love"),
    "TrueNode": ("career", "spiritual"),
    "Midheaven": ("career",),
    "Ascendant": ("health", "career"),
}

FOCUS_KEYWORDS: Mapping[str, str] = {
    "career": "career",
    "work": "career",
    "ambition": "career",
    "purpose": "career",
    "calling": "career",
    "mission": "career",
    "relationship": "love",
    "relationships": "love",
    "partner": "love",
    "partners": "love",
    "love": "love",
    "heart": "love",
    "family": "love",
    "romance": "love",
    "health": "health",
    "wellness": "health",
    "body": "health",
    "vitality": "health",
    "routine": "health",
    "ritual": "health",
    "finance": "finance",
    "finances": "finance",
    "money": "finance",
    "resources": "finance",
    "abundance": "finance",
    "wealth": "finance",
    "budget": "finance",
}

TAG_TO_AREAS: Mapping[str, str] = {
    "career": "career",
    "ambition": "career",
    "work": "career",
    "discipline": "career",
    "strategy": "career",
    "planning": "career",
    "leadership": "career",
    "visibility": "career",
    "love": "love",
    "relationships": "love",
    "family": "love",
    "connection": "love",
    "intimacy": "love",
    "empathy": "love",
    "healing": "health",
    "health": "health",
    "routine": "health",
    "vitality": "health",
    "body": "health",
    "momentum": "health",
    "money": "finance",
    "resources": "finance",
    "stability": "finance",
    "structure": "finance",
    "strategy_finance": "finance",
}

SOURCE_WEIGHTS: Mapping[str, float] = {
    "house": 1.2,
    "focus": 1.6,
    "body": 0.7,
    "tag": 0.6,
    "classification": 0.9,
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


def _intensity_multiplier(intensity: str | None) -> float:
    lookup = {
        "surge": 1.5,
        "strong": 1.25,
        "steady": 1.0,
        "gentle": 0.85,
        "background": 0.6,
    }
    return lookup.get(intensity or "steady", 1.0)


def _event_strength(event: Mapping[str, Any]) -> float:
    try:
        raw_score = float(event.get("score") or 0.0)
    except (TypeError, ValueError):
        raw_score = 0.0
    classification = event.get("classification") or {}
    multiplier = _intensity_multiplier(classification.get("intensity"))
    strength = abs(raw_score) * _aspect_weight(event) * multiplier
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
        if lowered.startswith("tone:"):
            continue
        area = TAG_TO_AREAS.get(lowered)
        if area and area not in results:
            results.append(area)
    return tuple(results)


def annotate_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return a shallow-copied list of events annotated with area hints."""

    annotated: list[dict[str, Any]] = []
    for event in events or []:
        copied = dict(event)
        classification = classify_event(copied)
        copied["classification"] = classification
        area_sources: dict[str, set[str]] = {}

        natal_house = copied.get("natal_house")
        if isinstance(natal_house, int):
            for area in HOUSE_TO_AREAS.get(natal_house, ()):  # type: ignore[arg-type]
                area_sources.setdefault(area, set()).add("house")
            for area, houses in AREA_FALLBACK_HOUSES.items():
                if natal_house in houses:
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

        class_tags = classification.get("tags") if isinstance(classification, Mapping) else ()
        for area in _areas_from_tags(class_tags):
            area_sources.setdefault(area, set()).add("classification")

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
        strength *= 1.2
    classification = event.get("classification") or {}
    class_tags = classification.get("tags", []) if isinstance(classification, Mapping) else []
    coherence = 0.0
    for tag in class_tags:
        if tag.startswith("tone:"):
            continue
        if TAG_TO_AREAS.get(tag.lower()) == area:
            coherence += 0.35
    if classification.get("archetype") == "Steady Integration" and area == "health":
        coherence += 0.2
    total = strength + relevance * 25.0 + coherence * 18.0
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


def _fallback_candidate(area: str, events: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    houses = AREA_FALLBACK_HOUSES.get(area, ())
    best: dict[str, Any] | None = None
    best_score = float("-inf")
    for event in events:
        house = event.get("natal_house")
        if houses and house not in houses:
            continue
        candidate = _candidate(event, area, (), fallback=True)
        if candidate and candidate["score"] > best_score:
            best = candidate
            best_score = candidate["score"]
    if best:
        return best
    if events:
        return _candidate(events[0], area, (), fallback=True)
    return None


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
            fallback = _fallback_candidate(area, annotated)
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
            "supporting": serialized[1] if len(serialized) > 1 else None,
            "ranking": serialized,
        }
    return summary


__all__ = [
    "annotate_events",
    "rank_events_by_area",
    "summarize_rankings",
]
