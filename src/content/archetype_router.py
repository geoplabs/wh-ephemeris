"""Rule-based classifier that maps transit events to tonal archetypes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, MutableSequence, Sequence

SUPPORTIVE_ASPECTS = {"trine", "sextile"}
CHALLENGING_ASPECTS = {"square", "opposition"}
TRANSFORMATIONAL_ASPECTS = {"conjunction"}

BENEFIC_PLANETS = {"Jupiter", "Venus", "Sun", "Moon"}
MALEFIC_PLANETS = {"Mars", "Saturn", "Pluto"}

BODY_TAGS = {
    "Sun": ("career", "vitality"),
    "Moon": ("emotions", "family"),
    "Mercury": ("education", "career"),
    "Venus": ("love", "money"),
    "Mars": ("career", "health"),
    "Jupiter": ("education", "spiritual", "growth"),
    "Saturn": ("discipline", "career"),
    "Uranus": ("innovation", "travel"),
    "Neptune": ("spiritual",),
    "Pluto": ("transform",),
    "Chiron": ("healing", "growth"),
    "TrueNode": ("spiritual", "destiny"),
    "Midheaven": ("career",),
    "Ascendant": ("identity", "health"),
}

HOUSE_TAGS = {
    1: ("identity", "health"),
    2: ("money", "resources"),
    3: ("education", "communication"),
    4: ("family", "home"),
    5: ("joy", "creativity"),
    6: ("health", "routine"),
    7: ("love", "relationships"),
    8: ("intimacy", "money"),
    9: ("travel", "education", "spiritual"),
    10: ("career", "public"),
    11: ("community", "ambition"),
    12: ("spiritual", "healing"),
}


@dataclass(frozen=True)
class Rule:
    """Declarative archetype rule."""

    archetype: str
    when: Mapping[str, Any]
    extra_tags: Sequence[str]
    tone_override: str | None = None

    def matches(self, metadata: Mapping[str, Any]) -> bool:
        tag_set = metadata["tag_set"]
        for key, expected in self.when.items():
            if key == "any_tags":
                if not tag_set.intersection(expected):
                    return False
            elif key == "all_tags":
                if not set(expected).issubset(tag_set):
                    return False
            elif key == "house_in":
                house = metadata.get("natal_house")
                if house is None or house not in expected:
                    return False
            elif key == "transit_body_in":
                if metadata.get("transit_body") not in expected:
                    return False
            elif key == "natal_body_in":
                if metadata.get("natal_body") not in expected:
                    return False
            elif key == "benefic":
                if bool(metadata.get("is_benefic")) is not expected:
                    return False
            elif key == "malefic":
                if bool(metadata.get("is_malefic")) is not expected:
                    return False
            else:
                value = metadata.get(key)
                if value not in expected:
                    return False
        return True


RULES: Sequence[Rule] = (
    Rule(
        archetype="Radiant Expansion",
        when={"benefic": True, "score_sign": {"positive"}},
        extra_tags=("growth", "momentum"),
        tone_override="tone:support",
    ),
    Rule(
        archetype="Prosperity Build",
        when={
            "aspect_type": {"supportive"},
            "any_tags": {"money", "career", "resources"},
            "score_sign": {"positive"},
        },
        extra_tags=("strategy", "stability"),
        tone_override="tone:support",
    ),
    Rule(
        archetype="Heart-Centered Calibration",
        when={
            "any_tags": {"love", "relationships", "family", "emotions"},
            "score_sign": {"negative", "neutral"},
        },
        extra_tags=("connection", "boundaries"),
        tone_override="tone:neutral",
    ),
    Rule(
        archetype="Disciplined Crossroads",
        when={"malefic": True, "score_sign": {"negative"}},
        extra_tags=("restructure", "courage"),
        tone_override="tone:challenge",
    ),
    Rule(
        archetype="Visionary Alignment",
        when={
            "any_tags": {"innovation", "spiritual", "education", "travel"},
            "score_sign": {"positive"},
        },
        extra_tags=("insight", "expansion"),
        tone_override="tone:support",
    ),
    Rule(
        archetype="Phoenix Reframe",
        when={
            "aspect_type": {"transformational", "challenging"},
            "any_tags": {"transform", "healing", "spiritual"},
            "score_sign": {"negative"},
        },
        extra_tags=("release", "inner_work"),
        tone_override="tone:challenge",
    ),
)

DEFAULT_RULE = Rule(
    archetype="Steady Integration",
    when={},
    extra_tags=("integration",),
    tone_override=None,
)


def _aspect_type(aspect: str) -> str:
    lowered = (aspect or "").lower()
    if lowered in SUPPORTIVE_ASPECTS:
        return "supportive"
    if lowered in CHALLENGING_ASPECTS:
        return "challenging"
    if lowered in TRANSFORMATIONAL_ASPECTS:
        return "transformational"
    return "neutral"


def _score_sign(score: float) -> str:
    if score > 0.5:
        return "positive"
    if score < -0.5:
        return "negative"
    return "neutral"


def _intensity_from_score(score: float) -> str:
    magnitude = abs(score)
    if magnitude >= 80:
        return "surge"
    if magnitude >= 60:
        return "strong"
    if magnitude >= 40:
        return "steady"
    if magnitude >= 15:
        return "gentle"
    return "background"


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _tone_tag(aspect_type: str, score_sign: str, is_malefic: bool) -> str:
    if score_sign == "positive" and aspect_type in {"supportive", "transformational"}:
        return "tone:support"
    if score_sign == "negative" or aspect_type == "challenging" or is_malefic:
        return "tone:challenge"
    return "tone:neutral"


def _base_tags(event: Mapping[str, Any]) -> MutableSequence[str]:
    tags: list[str] = []
    natal_body = event.get("natal_body")
    natal_house = event.get("natal_house")
    if natal_body and natal_body in BODY_TAGS:
        tags.extend(BODY_TAGS[natal_body])
    if isinstance(natal_house, int) and natal_house in HOUSE_TAGS:
        tags.extend(HOUSE_TAGS[natal_house])
    return tags


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _merge_tags(*groups: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for tag in group:
            if not tag:
                continue
            if tag not in seen:
                seen.add(tag)
                merged.append(tag)
    return merged


def classify_event(event: Mapping[str, Any]) -> Dict[str, Any]:
    """Return archetype metadata for a single event."""

    score = _coerce_float(event.get("score"))
    aspect_type = _aspect_type(str(event.get("aspect", "")))
    score_sign = _score_sign(score)

    transit_body = str(event.get("transit_body", "")) or ""
    natal_body = str(event.get("natal_body", "")) or ""
    natal_house = event.get("natal_house") if isinstance(event.get("natal_house"), int) else None

    is_benefic = _normalize_bool(
        event.get("is_benefic")
        or event.get("benefic")
        or event.get("transit_benefic")
        or (transit_body in BENEFIC_PLANETS)
    )
    is_malefic = _normalize_bool(
        event.get("is_malefic")
        or event.get("malefic")
        or event.get("transit_malefic")
        or (transit_body in MALEFIC_PLANETS)
    )

    base_tags = _base_tags(event)
    if is_benefic:
        base_tags.append("support")
    if is_malefic:
        base_tags.append("discipline")
    if score_sign == "positive":
        base_tags.append("opening")
    if score_sign == "negative":
        base_tags.append("pressure")

    metadata = {
        "score": score,
        "aspect_type": aspect_type,
        "score_sign": score_sign,
        "is_benefic": is_benefic,
        "is_malefic": is_malefic,
        "transit_body": transit_body,
        "natal_body": natal_body,
        "natal_house": natal_house,
        "base_tags": base_tags,
        "tone_tag": _tone_tag(aspect_type, score_sign, is_malefic),
    }
    metadata["tag_set"] = set(base_tags)

    for rule in RULES:
        if rule.matches(metadata):
            tone = rule.tone_override or metadata["tone_tag"]
            base_without_tone = [t for t in base_tags if not t.startswith("tone:")]
            tags = _merge_tags([tone], base_without_tone, rule.extra_tags)
            return {
                "archetype": rule.archetype,
                "intensity": _intensity_from_score(score),
                "tags": tags,
            }

    tone = metadata["tone_tag"]
    base_without_tone = [t for t in base_tags if not t.startswith("tone:")]
    tags = _merge_tags([tone], base_without_tone, DEFAULT_RULE.extra_tags)
    return {
        "archetype": DEFAULT_RULE.archetype,
        "intensity": _intensity_from_score(score),
        "tags": tags,
    }


__all__ = ["classify_event"]
