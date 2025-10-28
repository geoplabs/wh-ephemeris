"""Scoring helpers for matching transit events to forecast areas."""

from __future__ import annotations

from collections import Counter
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

AREA_SOURCE_WEIGHTS: Mapping[str, Mapping[str, float]] = {
    "career": {
        "house": 1.35,
        "house:fallback": 1.05,
        "house:borrowed": 0.95,
        "focus": 1.9,
        "body": 0.95,
        "tag": 0.75,
        "classification": 1.05,
    },
    "love": {
        "house": 1.25,
        "house:fallback": 1.0,
        "house:borrowed": 0.95,
        "focus": 1.75,
        "body": 0.9,
        "tag": 0.85,
        "classification": 1.1,
    },
    "health": {
        "house": 1.4,
        "house:fallback": 1.1,
        "house:borrowed": 1.0,
        "focus": 1.6,
        "body": 1.0,
        "tag": 0.7,
        "classification": 0.95,
    },
    "finance": {
        "house": 1.3,
        "house:fallback": 1.05,
        "house:borrowed": 1.0,
        "focus": 1.7,
        "body": 0.95,
        "tag": 0.9,
        "classification": 1.05,
    },
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


def _house_distance(a: Any, b: Any) -> int | None:
    if not isinstance(a, int) or not isinstance(b, int):
        return None
    diff = abs(a - b)
    return min(diff, 12 - diff)


def _source_weight(area: str, source: str) -> float:
    weights = AREA_SOURCE_WEIGHTS.get(area, {})
    if source in weights:
        return weights[source]
    base = source.split(":", 1)[0]
    if base in weights:
        return weights[base]
    if source in SOURCE_WEIGHTS:
        return SOURCE_WEIGHTS[source]
    if base in SOURCE_WEIGHTS:
        return SOURCE_WEIGHTS[base]
    return 0.4


def annotate_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return a shallow-copied list of events annotated with area hints."""

    annotated: list[dict[str, Any]] = []
    for event in events or []:
        copied = dict(event)
        classification = classify_event(copied)
        copied["classification"] = classification
        area_sources: dict[str, list[str]] = {}

        natal_house = copied.get("natal_house")
        if isinstance(natal_house, int):
            primary_house_areas = set(HOUSE_TO_AREAS.get(natal_house, ()))  # type: ignore[arg-type]
            for area in primary_house_areas:
                area_sources.setdefault(area, []).append("house")
            for area, houses in AREA_FALLBACK_HOUSES.items():
                if area in primary_house_areas:
                    continue
                if natal_house in houses:
                    area_sources.setdefault(area, []).append("house:fallback")

        for label in _iter_focus_labels(copied):
            focus_area = _focus_area_from_label(label)
            if focus_area:
                area_sources.setdefault(focus_area, []).append("focus")
                copied.setdefault("focus_area", focus_area)

        for key in ("transit_body", "natal_body"):
            for area in _areas_from_body(copied.get(key)):
                area_sources.setdefault(area, []).append("body")

        tags = copied.get("tags")
        if isinstance(tags, (list, tuple, set)):
            for area in _areas_from_tags(tags):
                area_sources.setdefault(area, []).append("tag")

        class_tags = classification.get("tags") if isinstance(classification, Mapping) else ()
        for area in _areas_from_tags(class_tags):
            area_sources.setdefault(area, []).append("classification")

        copied["area_hints"] = {area: tuple(sources) for area, sources in area_sources.items()}
        annotated.append(copied)
    return annotated


def _candidate(
    event: Mapping[str, Any],
    area: str,
    sources: Iterable[str],
    *,
    fallback: bool = False,
) -> dict[str, Any] | None:
    contributions = [source for source in sources if source]
    counts = Counter(contributions)
    if not fallback and not counts:
        return None
    strength = _event_strength(event)
    relevance = 0.0
    source_breakdown: dict[str, float] = {}
    for source, count in counts.items():
        weight = _source_weight(area, source)
        contribution = weight * count
        source_breakdown[source] = round(contribution, 4)
        relevance += contribution
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
    display_sources: list[str] = []
    for source, count in sorted(counts.items()):
        label = source.replace(":", " → ")
        if count > 1:
            label = f"{label}×{count}"
        display_sources.append(label)
    candidate = {
        "area": area,
        "event": event,
        "strength": round(strength, 4),
        "relevance": round(relevance, 4),
        "score": round(total, 4),
        "sources": display_sources,
        "source_breakdown": source_breakdown,
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
        contributions: list[str] = []
        closest_distance: int | None = None
        if isinstance(house, int) and houses:
            if house in houses:
                rank = houses.index(house)
                repeats = max(1, len(houses) - rank)
                contributions.extend(["house:fallback"] * repeats)
                closest_distance = 0
            else:
                distances = [d for target in houses if (d := _house_distance(house, target)) is not None]
                if distances:
                    closest_distance = min(distances)
                    if closest_distance <= 2:
                        repeats = 2 - closest_distance + 1
                        contributions.extend(["house:borrowed"] * repeats)
        focus_area = event.get("focus_area")
        if isinstance(focus_area, str) and focus_area.strip().lower() == area:
            contributions.append("focus")
        candidate = _candidate(event, area, contributions, fallback=True)
        if not candidate:
            continue
        closeness_bonus = 0.0
        if closest_distance is not None:
            closeness_bonus = max(0, 3 - closest_distance)
        candidate_score = candidate["score"] + closeness_bonus
        if candidate_score > best_score:
            best = candidate
            best_score = candidate_score
    if best:
        return best
    if events:
        extra_sources: list[str] = []
        house = events[0].get("natal_house")
        if isinstance(house, int):
            extra_sources.append("house:borrowed")
        return _candidate(events[0], area, extra_sources, fallback=True)
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
            raw_sources = list(hints.get(area, ()))
            sources: list[str] = list(raw_sources)
            if isinstance(focus_area, str) and focus_area == area:
                sources.append("focus")
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
            if candidate.get("source_breakdown"):
                payload["source_breakdown"] = dict(candidate["source_breakdown"])
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
