"""Rule-based classifier that maps transit events to tonal archetypes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, MutableSequence, Sequence, Tuple

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


INTENSITY_ORDER: Tuple[str, ...] = ("background", "gentle", "steady", "strong", "surge")


@dataclass(frozen=True)
class Rule:
    """Declarative archetype rule."""

    archetype: str | None
    when: Mapping[str, Any]
    extra_tags: Sequence[str]
    tone_override: str | None = None
    weight: float = 1.0
    intensity_bias: int = 0

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
            elif key == "house_family":
                if metadata.get("house_family") not in expected:
                    return False
            elif key == "aspect_type":
                if metadata.get("aspect_type") not in expected:
                    return False
            elif key == "score_bucket":
                if metadata.get("score_bucket") not in expected:
                    return False
            elif key == "focus_area":
                if metadata.get("focus_area") not in expected:
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
        weight=2.4,
    ),
    Rule(
        archetype="Radiant Expansion",
        when={
            "aspect_type": {"supportive"},
            "house_family": {"angular"},
            "score_bucket": {"elevated", "peak"},
        },
        extra_tags=("leadership", "visibility"),
        tone_override="tone:support",
        weight=1.8,
        intensity_bias=1,
    ),
    Rule(
        archetype="Prosperity Build",
        when={
            "aspect_type": {"supportive", "transformational"},
            "any_tags": {"money", "career", "resources"},
            "score_sign": {"positive", "neutral"},
        },
        extra_tags=("strategy", "stability"),
        tone_override="tone:support",
        weight=2.2,
    ),
    Rule(
        archetype="Prosperity Build",
        when={"focus_area": {"finance", "career"}},
        extra_tags=("structure", "planning"),
        tone_override=None,
        weight=1.4,
    ),
    Rule(
        archetype="Heart-Centered Calibration",
        when={
            "any_tags": {"love", "relationships", "family", "emotions"},
            "score_sign": {"negative", "neutral"},
        },
        extra_tags=("connection", "boundaries"),
        tone_override="tone:neutral",
        weight=2.0,
    ),
    Rule(
        archetype="Heart-Centered Calibration",
        when={"house_in": {4, 5, 7}, "aspect_type": {"supportive", "transformational"}},
        extra_tags=("intimacy", "empathy"),
        tone_override=None,
        weight=1.6,
    ),
    Rule(
        archetype="Disciplined Crossroads",
        when={"malefic": True, "score_sign": {"negative"}},
        extra_tags=("restructure", "courage"),
        tone_override="tone:challenge",
        weight=2.5,
        intensity_bias=1,
    ),
    Rule(
        archetype="Disciplined Crossroads",
        when={"house_family": {"angular"}, "aspect_type": {"challenging"}},
        extra_tags=("commitment", "boundaries"),
        tone_override="tone:challenge",
        weight=1.7,
    ),
    Rule(
        archetype="Visionary Alignment",
        when={
            "any_tags": {"innovation", "spiritual", "education", "travel"},
            "score_sign": {"positive"},
        },
        extra_tags=("insight", "expansion"),
        tone_override="tone:support",
        weight=2.1,
    ),
    Rule(
        archetype="Visionary Alignment",
        when={"focus_area": {"education", "spiritual"}},
        extra_tags=("study", "pilgrimage"),
        tone_override=None,
        weight=1.5,
    ),
    Rule(
        archetype="Phoenix Reframe",
        when={
            "aspect_type": {"transformational", "challenging"},
            "any_tags": {"transform", "healing", "spiritual"},
            "score_sign": {"negative", "neutral"},
        },
        extra_tags=("release", "inner_work"),
        tone_override="tone:challenge",
        weight=2.3,
        intensity_bias=1,
    ),
    Rule(
        archetype="Phoenix Reframe",
        when={"natal_body_in": {"Pluto", "Chiron"}},
        extra_tags=("shadow_work", "rebirth"),
        tone_override="tone:challenge",
        weight=1.4,
    ),
    Rule(
        archetype=None,
        when={"score_bucket": {"background"}},
        extra_tags=("subtle", "integration"),
        tone_override="tone:neutral",
        weight=0.5,
        intensity_bias=-1,
    ),
)

DEFAULT_RULE = Rule(
    archetype="Steady Integration",
    when={},
    extra_tags=("integration",),
    tone_override=None,
    weight=1.0,
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


def _score_bucket(score: float) -> str:
    magnitude = abs(score)
    if magnitude >= 90:
        return "peak"
    if magnitude >= 65:
        return "elevated"
    if magnitude >= 35:
        return "moderate"
    if magnitude >= 10:
        return "gentle"
    return "background"


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
    score_bucket = _score_bucket(score)

    transit_body = str(event.get("transit_body", "")) or ""
    natal_body = str(event.get("natal_body", "")) or ""
    natal_house = event.get("natal_house") if isinstance(event.get("natal_house"), int) else None
    focus_area = event.get("focus_area") or event.get("dominant_focus") or event.get("primary_focus")
    if isinstance(focus_area, str):
        focus_area = focus_area.strip().lower() or None
    house_family = None
    if isinstance(natal_house, int):
        if natal_house in {1, 4, 7, 10}:
            house_family = "angular"
        elif natal_house in {2, 5, 8, 11}:
            house_family = "succedent"
        elif natal_house in {3, 6, 9, 12}:
            house_family = "cadent"

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
        "score_bucket": score_bucket,
        "is_benefic": is_benefic,
        "is_malefic": is_malefic,
        "transit_body": transit_body,
        "natal_body": natal_body,
        "natal_house": natal_house,
        "house_family": house_family,
        "focus_area": focus_area,
        "base_tags": base_tags,
        "tone_tag": _tone_tag(aspect_type, score_sign, is_malefic),
    }
    metadata["tag_set"] = set(base_tags)

    matched_rules: list[Rule] = [rule for rule in RULES if rule.matches(metadata)]

    base_intensity = _intensity_from_score(score)
    tone_votes: dict[str, float] = {}
    archetype_scores: dict[str, float] = {}
    intensity_bias = 0
    aggregated_tags: list[str] = []

    def _register_tone(tag: str, weight: float) -> None:
        tone_votes[tag] = tone_votes.get(tag, 0.0) + weight

    for rule in matched_rules:
        tone = rule.tone_override or metadata["tone_tag"]
        _register_tone(tone, rule.weight)
        aggregated_tags.extend(rule.extra_tags)
        intensity_bias += rule.intensity_bias
        if rule.archetype:
            archetype_scores[rule.archetype] = archetype_scores.get(rule.archetype, 0.0) + rule.weight

    selected_archetype = None
    if archetype_scores:
        selected_archetype = max(archetype_scores.items(), key=lambda item: item[1])[0]

    if not selected_archetype:
        selected_archetype = DEFAULT_RULE.archetype
        _register_tone(metadata["tone_tag"], DEFAULT_RULE.weight)
        aggregated_tags.extend(DEFAULT_RULE.extra_tags)

    tone_choice = max(tone_votes.items(), key=lambda item: item[1])[0] if tone_votes else metadata["tone_tag"]
    base_without_tone = [t for t in base_tags if not t.startswith("tone:")]
    tags = _merge_tags([tone_choice], base_without_tone, aggregated_tags)

    base_index = INTENSITY_ORDER.index(base_intensity)
    adjusted_index = min(max(base_index + intensity_bias, 0), len(INTENSITY_ORDER) - 1)
    intensity = INTENSITY_ORDER[adjusted_index]

    return {
        "archetype": selected_archetype,
        "intensity": intensity,
        "tags": tags,
    }


__all__ = ["classify_event"]
