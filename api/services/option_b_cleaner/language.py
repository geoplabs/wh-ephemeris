from __future__ import annotations

import hashlib
import random
import re
from typing import Any, Iterable, Mapping, Sequence

from .clean import de_jargon, to_you_pov
from .event_tokens import MiniTemplate, event_phrase, render_mini_template
from src.content.storylets import storylet_pools


SIGN_DETAILS = {
    "Aries": ("Cardinal", "Fire"),
    "Taurus": ("Fixed", "Earth"),
    "Gemini": ("Mutable", "Air"),
    "Cancer": ("Cardinal", "Water"),
    "Leo": ("Fixed", "Fire"),
    "Virgo": ("Mutable", "Earth"),
    "Libra": ("Cardinal", "Air"),
    "Scorpio": ("Fixed", "Water"),
    "Sagittarius": ("Mutable", "Fire"),
    "Capricorn": ("Cardinal", "Earth"),
    "Aquarius": ("Fixed", "Air"),
    "Pisces": ("Mutable", "Water"),
}

MODALITY_VERB = {
    "Cardinal": "promotes",
    "Fixed": "sustains",
    "Mutable": "inspires",
}

ELEMENT_QUALITIES = {
    "Fire": "courage and visibility",
    "Earth": "stability and structure",
    "Air": "balance and motion",
    "Water": "intuition and depth",
}

STOPWORDS = {
    "a",
    "and",
    "can",
    "may",
    "energy",
    "if",
    "into",
    "lean",
    "let",
    "may",
    "set",
    "should",
    "stay",
    "turn",
    "feel",
    "channel",
    "you're",
    "attached",
    "single",
    "take",
    "tackle",
    "move",
    "notably",
    "powerfully",
    "should",
    "the",
    "this",
    "with",
    "today",
    "your",
}

POSITIVE_CUES = {
    "radiant",
    "harmonizing",
    "support",
    "ease",
    "growth",
    "opportunity",
    "vibrant",
    "flow",
    "opening",
}

CHALLENGE_CUES = {
    "challenge",
    "friction",
    "pressure",
    "tense",
    "demand",
    "intense",
    "rigid",
    "strain",
}

FOCUS_MAP = (
    ("drive", "ambitions"),
    ("career", "career path"),
    ("work", "work"),
    ("emotional", "emotional rhythms"),
    ("heart", "heart space"),
    ("relationship", "relationships"),
    ("money", "money moves"),
    ("finance", "financial choices"),
    ("health", "wellness rituals"),
    ("body", "wellness rituals"),
)

DESCRIPTOR_OVERRIDES = {
    "heart": "tender",
    "emotional": "soothing",
    "focus": "steady",
    "balance": "balanced",
    "drive": "driven",
    "momentum": "steady",
    "energy": "vibrant",
    "tone": "steady",
    "heightens": "warming",
    "breath": "calm",
}


STORYLET_POOLS: Mapping[str, Mapping[str, object]] = storylet_pools()


def _story_seed(*parts: Any) -> int:
    material = "|".join(str(part) for part in parts if part not in {None, ""})
    if not material:
        material = "story"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _storylet_pool(area: str, section: str, tone: str) -> Sequence[str]:
    tone_key = tone if tone in {"support", "challenge", "neutral"} else "neutral"
    area_pool = STORYLET_POOLS.get(area, {})
    options: Sequence[str] = ()
    target = area_pool.get(section)
    if isinstance(target, Mapping):
        options = target.get(tone_key) or target.get("neutral", ())
    elif isinstance(target, Sequence):
        options = target
    if options:
        return options
    default_pool = STORYLET_POOLS.get("default", {})
    fallback = default_pool.get(section)
    if isinstance(fallback, Mapping):
        return fallback.get(tone_key) or fallback.get("neutral", ()) or ()
    if isinstance(fallback, Sequence):
        return fallback
    return ()


def _deterministic_choice(options: Sequence[str], seed: int, default: str = "") -> str:
    if not options:
        return default
    rng = random.Random(seed)
    return rng.choice(list(options))


def _render_storylet(
    area: str,
    section: str,
    tone: str,
    seed: int,
    *,
    tokens: Mapping[str, Any],
    default: str = "",
) -> str:
    options = _storylet_pool(area, section, tone)
    template = _deterministic_choice(options, seed, default)
    if not template:
        return default
    try:
        return template.format(**tokens)
    except (KeyError, ValueError):  # pragma: no cover - defensive formatting
        return default


def _clean_text(text: str, profile_name: str) -> str:
    cleaned = de_jargon(text or "")
    return to_you_pov(cleaned, profile_name)


def _keywords_from_text(texts: Iterable[str], profile_name: str = "") -> list[str]:
    tokens: list[str] = []
    blocked = {profile_name.lower()} if profile_name else set()
    for text in texts:
        cleaned = de_jargon(text or "").lower()
        tokens.extend(re.findall(r"[a-z']+", cleaned))
    if blocked:
        tokens = [t for t in tokens if t not in blocked]
    return tokens


def descriptor_from_text(*texts: str, default: str = "steady", profile_name: str = "") -> str:
    for token in _keywords_from_text(texts, profile_name=profile_name):
        clean_token = token[:-2] if token.endswith("'s") else token
        if len(clean_token) <= 2 or clean_token.endswith("ly") or clean_token in STOPWORDS:
            continue
        return DESCRIPTOR_OVERRIDES.get(clean_token, clean_token)
    return default


def focus_from_text(*texts: str, default: str = "path", profile_name: str = "") -> str:
    combined = " ".join(filter(None, texts)).lower()
    if profile_name:
        combined = combined.replace(profile_name.lower(), "")
    for key, focus in FOCUS_MAP:
        if key in combined:
            return focus
    return default


def tone_from_text(*texts: str) -> str:
    combined = " ".join(filter(None, texts)).lower()
    for cue in CHALLENGE_CUES:
        if cue in combined:
            return "challenge"
    for cue in POSITIVE_CUES:
        if cue in combined:
            return "support"
    return "neutral"


def _normalize_tone_label(value: str | None) -> str:
    if not value:
        return "neutral"
    lowered = value.strip().lower()
    if lowered.startswith("tone:"):
        lowered = lowered.split(":", 1)[1]
    if lowered not in {"support", "challenge", "neutral"}:
        return "neutral"
    return lowered


def _article(word: str) -> str:
    if not word:
        return "a"
    return "an" if word[0].lower() in "aeiou" else "a"


def _ensure_sentence(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


def _compose_paragraph(
    lead: str,
    evidence: Sequence[str] | None,
    closing: str | None,
) -> str:
    parts: list[str] = []
    if lead:
        normalized = _ensure_sentence(lead)
        if normalized:
            parts.append(normalized)
    for sentence in evidence or ():
        normalized = _ensure_sentence(sentence)
        if normalized and normalized not in parts:
            parts.append(normalized)
    if closing:
        normalized = _ensure_sentence(closing)
        if normalized:
            parts.append(normalized)
    return " ".join(parts).strip()


def _event_evidence_sentences(
    event: Mapping[str, Any] | None,
    supporting_event: Mapping[str, Any] | None = None,
    *,
    area: str | None = None,
    seed: int | None = None,
) -> tuple[str, ...]:
    sentences: list[str] = []
    primary = event_phrase(event)
    supporting = event_phrase(supporting_event)
    if primary and supporting and supporting != primary:
        templates_by_area = {
            "career": (
                "{primary} while {supporting}",
                "{primary}; meanwhile, {supporting}",
                "{primary}. In your workflow, {supporting}",
            ),
            "love": (
                "{primary} while {supporting}",
                "{primary}. Heart-wise, {supporting}",
                "{primary}; intimacy-wise, {supporting}",
            ),
            "health": (
                "{primary} while {supporting}",
                "{primary}. For your body, {supporting}",
                "{primary}; meanwhile your routines, {supporting}",
            ),
            "finance": (
                "{primary} while {supporting}",
                "{primary}. Money-wise, {supporting}",
                "{primary}; budget-wise, {supporting}",
            ),
        }
        templates = templates_by_area.get(area or "", templates_by_area["career"])
        base_seed = seed or 0
        template = templates[base_seed % len(templates)]
        sentences.append(template.format(primary=primary, supporting=supporting))
    elif primary:
        sentences.append(primary)
    elif supporting:
        sentences.append(supporting)
    return tuple(sentences)


def _build_story_paragraph(
    area: str,
    *,
    raw: str,
    descriptor: str,
    focus: str,
    tone: str,
    clause: str | None,
    event: Mapping[str, Any] | None,
    supporting_event: Mapping[str, Any] | None,
    opener_default: str,
    closing_default: str,
    force_default_opener: bool = False,
) -> str:
    tokens = {"descriptor": descriptor, "focus": focus}
    primary_phrase = event_phrase(event)
    supporting_phrase = event_phrase(supporting_event)
    base_seed = _story_seed(area, raw, descriptor, focus, tone, primary_phrase, supporting_phrase)
    opener_default_text = opener_default.format(**tokens)
    if force_default_opener:
        opener = opener_default_text
    else:
        opener = _render_storylet(
            area,
            "openers",
            tone,
            base_seed,
            tokens=tokens,
            default=opener_default_text,
        )
    evidence = list(
        _event_evidence_sentences(
            event,
            supporting_event,
            area=area,
            seed=base_seed + 1,
        )
    )
    coaching = _render_storylet(
        area,
        "coaching",
        tone,
        base_seed + 2,
        tokens=tokens,
        default="",
    )
    if coaching:
        evidence.append(coaching)
    default_closing = closing_default.format(**tokens)
    closing = clause.strip() if clause else _render_storylet(
        area,
        "closers",
        tone,
        base_seed + 3,
        tokens=tokens,
        default=default_closing,
    )
    return _compose_paragraph(opener, evidence, closing)


def element_modality_line(sign_a: str, sign_b: str) -> str:
    info_a = SIGN_DETAILS.get(sign_a, ("Cardinal", "Air"))
    info_b = SIGN_DETAILS.get(sign_b or sign_a, info_a)
    verb_a = MODALITY_VERB.get(info_a[0], "promotes")
    verb_b = MODALITY_VERB.get(info_b[0], "sustains")
    qual_a = ELEMENT_QUALITIES.get(info_a[1], "balance and motion")
    qual_b = ELEMENT_QUALITIES.get(info_b[1], "intuition and depth")
    return (
        f"{info_a[0]} {info_a[1]} ({sign_a}) {verb_a} {qual_a}, "
        f"while {info_b[0]} {info_b[1]} ({sign_b}) {verb_b} {qual_b}."
    )


def build_opening_summary(
    theme: str,
    raw: str,
    signs: Sequence[str],
    profile_name: str = "",
    clause: str | None = None,
) -> str:
    sign_a = signs[0] if signs else "Libra"
    sign_b = signs[1] if len(signs) > 1 else sign_a
    descriptor = descriptor_from_text(theme, raw, profile_name=profile_name)
    focus = focus_from_text(theme, raw, profile_name=profile_name)
    article = _article(descriptor)
    closing = clause.strip() if clause else "Harness this radiant push toward progress."
    if closing and not closing.endswith("."):
        closing = f"{closing}."
    first_sentence = (
        f"You ride {article} {descriptor} wave through today's {focus}—"
        f"{closing}"
    )
    backdrop = element_modality_line(sign_a, sign_b)
    return f"{first_sentence} {backdrop}"


def build_morning_paragraph(
    raw: str,
    profile_name: str,
    theme: str,
    event: Mapping[str, Any] | None = None,
) -> str:
    descriptor = descriptor_from_text(raw, theme, profile_name=profile_name)
    focus = focus_from_text(raw, theme, default="momentum", profile_name=profile_name)
    event_clause = event_phrase(event)
    tokens = {"descriptor": descriptor, "focus": focus, "event_clause": event_clause}
    sentence = render_mini_template(
        (
            MiniTemplate(
                "You set the tone with one intentional pause before leaning into {descriptor} {focus} today while {event_clause}.",
                ("descriptor", "focus", "event_clause"),
            ),
            MiniTemplate(
                "You set the tone by taking one intentional pause before leaning into {descriptor} {focus} today.",
                ("descriptor", "focus"),
            ),
        ),
        tokens,
    )
    return sentence or "You set the tone by taking one intentional pause before leaning into steady momentum today."


def build_career_paragraph(
    raw: str,
    profile_name: str = "",
    tone_hint: str | None = None,
    clause: str | None = None,
    event: Mapping[str, Any] | None = None,
    supporting_event: Mapping[str, Any] | None = None,
) -> str:
    descriptor = descriptor_from_text(raw, default="steady", profile_name=profile_name)
    focus = focus_from_text(raw, default="work", profile_name=profile_name)
    tone_value = tone_hint if tone_hint else tone_from_text(raw, clause or "")
    tone = _normalize_tone_label(tone_value)
    return _build_story_paragraph(
        "career",
        raw=raw,
        descriptor=descriptor,
        focus=focus,
        tone=tone,
        clause=clause,
        event=event,
        supporting_event=supporting_event,
        opener_default="You turn {descriptor} work into deliberate progress at work.",
        closing_default="Let this focused drive move your intentions into form.",
    )


def build_love_paragraph(
    raw: str,
    profile_name: str = "",
    tone_hint: str | None = None,
    clause: str | None = None,
    event: Mapping[str, Any] | None = None,
    supporting_event: Mapping[str, Any] | None = None,
) -> str:
    descriptor = descriptor_from_text(raw, default="tender", profile_name=profile_name)
    focus = focus_from_text(raw, default="heart space", profile_name=profile_name)
    tone_value = tone_hint if tone_hint else tone_from_text(raw, clause or "")
    tone = _normalize_tone_label(tone_value)
    return _build_story_paragraph(
        "love",
        raw=raw,
        descriptor=descriptor,
        focus=focus,
        tone=tone,
        clause=clause,
        event=event,
        supporting_event=supporting_event,
        opener_default="You nurture heart connections by sharing {descriptor} honesty.",
        closing_default="Let shared space stay honest and kind.",
    )


def build_love_status(
    raw: str, status: str, profile_name: str = "", tone_hint: str | None = None
) -> str:
    tone = tone_hint or tone_from_text(raw)
    if status == "attached":
        if tone == "challenge":
            return "If you're attached, you steady shared plans with calm check-ins today."
        return "If you're attached, you lean into rituals that feel supportive and sincere."
    if tone == "challenge":
        return "If you're single, you approach new sparks with grounded curiosity."
    return "If you're single, you follow conversations that feel naturally aligned."


def build_health_paragraph(
    raw: str,
    theme: str,
    profile_name: str = "",
    tone_hint: str | None = None,
    clause: str | None = None,
    event: Mapping[str, Any] | None = None,
    supporting_event: Mapping[str, Any] | None = None,
) -> str:
    descriptor = descriptor_from_text(raw, theme, default="balanced", profile_name=profile_name)
    focus = focus_from_text(raw, theme, default="wellness rituals", profile_name=profile_name)
    tone_value = tone_hint if tone_hint else tone_from_text(raw, theme, clause or "")
    tone = _normalize_tone_label(tone_value)
    closing_default = (
        "Keep movements gentle and responsive to your body's signals."
        if tone == "challenge"
        else "Balance movement with rest so your body stays responsive."
    )
    force_default_opener = event is None and supporting_event is None
    return _build_story_paragraph(
        "health",
        raw=raw or theme,
        descriptor=descriptor,
        focus=focus,
        tone=tone,
        clause=clause,
        event=event,
        supporting_event=supporting_event,
        opener_default="You protect wellbeing by honoring {descriptor} rhythms.",
        closing_default=closing_default,
        force_default_opener=force_default_opener,
    )


def build_finance_paragraph(
    raw: str,
    theme: str,
    profile_name: str = "",
    tone_hint: str | None = None,
    clause: str | None = None,
    event: Mapping[str, Any] | None = None,
    supporting_event: Mapping[str, Any] | None = None,
) -> str:
    descriptor = descriptor_from_text(raw, theme, default="calm", profile_name=profile_name)
    focus = focus_from_text(raw, theme, default="money choices", profile_name=profile_name)
    tone_value = tone_hint if tone_hint else tone_from_text(raw, theme, clause or "")
    tone = _normalize_tone_label(tone_value)
    closing_default = (
        "Review numbers before you commit to new moves."
        if tone == "challenge"
        else "Let emotional harmony guide practical choices."
    )
    return _build_story_paragraph(
        "finance",
        raw=raw or theme,
        descriptor=descriptor,
        focus=focus,
        tone=tone,
        clause=clause,
        event=event,
        supporting_event=supporting_event,
        opener_default="You let {descriptor} awareness guide each money choice today.",
        closing_default=closing_default,
    )


def build_one_line_summary(raw: str, theme: str, profile_name: str = "") -> str:
    descriptor = descriptor_from_text(raw, theme, default="steady", profile_name=profile_name)
    focus = focus_from_text(raw, theme, default="momentum", profile_name=profile_name)
    return f"You close the day by keeping {descriptor} {focus} in view."


def polished_text(raw: str, profile_name: str) -> str:
    cleaned = _clean_text(raw, profile_name)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if not sentences:
        return ""
    first = sentences[0]
    if not first.endswith("."):
        first += "."
    return first
