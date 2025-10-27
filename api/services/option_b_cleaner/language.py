from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence

from .clean import de_jargon, to_you_pov
from .event_tokens import MiniTemplate, event_phrase, render_mini_template


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
) -> tuple[str, ...]:
    sentences: list[str] = []
    primary = event_phrase(event)
    supporting = event_phrase(supporting_event)
    if primary:
        sentences.append(primary)
    if supporting and supporting != primary:
        connector = f"Meanwhile, {supporting}"
        sentences.append(connector)
    return tuple(sentences)


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
    tone = tone_hint or tone_from_text(raw)
    event_clause = event_phrase(event)
    tokens = {"descriptor": descriptor, "event_clause": event_clause}
    if tone == "challenge":
        first = render_mini_template(
            (
                MiniTemplate(
                    "You steady {descriptor} demands by pacing commitments at work while {event_clause}.",
                    ("descriptor", "event_clause"),
                ),
                MiniTemplate(
                    "You steady {descriptor} demands by pacing commitments at work.",
                    ("descriptor",),
                ),
            ),
            tokens,
        )
    else:
        first = render_mini_template(
            (
                MiniTemplate(
                    "You turn {descriptor} work into deliberate progress at work while {event_clause}.",
                    ("descriptor", "event_clause"),
                ),
                MiniTemplate(
                    "You turn {descriptor} work into deliberate progress at work.",
                    ("descriptor",),
                ),
            ),
            tokens,
        )
    if not first:
        first = "You turn steady work into deliberate progress at work."
    closing = clause.strip() if clause else "Let this focused drive move your intentions into form."
    evidence = _event_evidence_sentences(event, supporting_event)
    return _compose_paragraph(first, evidence, closing)


def build_love_paragraph(
    raw: str,
    profile_name: str = "",
    tone_hint: str | None = None,
    clause: str | None = None,
    event: Mapping[str, Any] | None = None,
    supporting_event: Mapping[str, Any] | None = None,
) -> str:
    descriptor = descriptor_from_text(raw, default="tender", profile_name=profile_name)
    tone = tone_hint or tone_from_text(raw)
    event_clause = event_phrase(event)
    tokens = {"descriptor": descriptor, "event_clause": event_clause}
    if tone == "challenge":
        base = render_mini_template(
            (
                MiniTemplate(
                    "You ease relationship friction by listening with {descriptor} patience while {event_clause}.",
                    ("descriptor", "event_clause"),
                ),
                MiniTemplate(
                    "You ease relationship friction by listening with {descriptor} patience.",
                    ("descriptor",),
                ),
            ),
            tokens,
        )
    else:
        base = render_mini_template(
            (
                MiniTemplate(
                    "You nurture heart connections by sharing {descriptor} honesty as {event_clause}.",
                    ("descriptor", "event_clause"),
                ),
                MiniTemplate(
                    "You nurture heart connections by sharing {descriptor} honesty.",
                    ("descriptor",),
                ),
            ),
            tokens,
        )
    if not base:
        base = "You nurture heart connections by sharing tender honesty."
    closing = clause.strip() if clause else ""
    evidence = _event_evidence_sentences(event, supporting_event)
    return _compose_paragraph(base, evidence, closing)


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
    tone = tone_hint or tone_from_text(raw)
    if tone == "challenge":
        default_second = "Keep movements gentle and responsive to your body's signals."
    else:
        default_second = "Balance movement with rest so your body stays responsive."
    closing = clause.strip() if clause else default_second
    event_clause = event_phrase(event)
    first = render_mini_template(
        (
            MiniTemplate(
                "You protect wellbeing by honoring {descriptor} rhythms while {event_clause}.",
                ("descriptor", "event_clause"),
            ),
            MiniTemplate(
                "You protect wellbeing by honoring {descriptor} rhythms.",
                ("descriptor",),
            ),
        ),
        {"descriptor": descriptor, "event_clause": event_clause},
    )
    if not first:
        first = "You protect wellbeing by honoring balanced rhythms."
    evidence = _event_evidence_sentences(event, supporting_event)
    return _compose_paragraph(first, evidence, closing)


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
    tone = tone_hint or tone_from_text(raw)
    event_clause = event_phrase(event)
    tokens = {"descriptor": descriptor, "event_clause": event_clause}
    if tone == "challenge":
        first = render_mini_template(
            (
                MiniTemplate(
                    "You navigate financial choices with {descriptor} patience today while {event_clause}.",
                    ("descriptor", "event_clause"),
                ),
                MiniTemplate(
                    "You navigate financial choices with {descriptor} patience today.",
                    ("descriptor",),
                ),
            ),
            tokens,
        )
        default_second = "Review numbers before you commit to new moves."
    else:
        first = render_mini_template(
            (
                MiniTemplate(
                    "You let {descriptor} awareness guide each money choice today while {event_clause}.",
                    ("descriptor", "event_clause"),
                ),
                MiniTemplate(
                    "You let {descriptor} awareness guide each money choice today.",
                    ("descriptor",),
                ),
            ),
            tokens,
        )
        default_second = "Let emotional harmony guide practical choices."
    if not first:
        first = "You let calm awareness guide each money choice today."
    closing = clause.strip() if clause else default_second
    evidence = _event_evidence_sentences(event, supporting_event)
    return _compose_paragraph(first, evidence, closing)


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
