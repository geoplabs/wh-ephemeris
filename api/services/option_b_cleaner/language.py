from __future__ import annotations

import re
from typing import Iterable, Sequence

from .clean import de_jargon, to_you_pov


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

MICRO_PHRASES = {
    "opening": "Harness this radiant push toward progress.",
    "career": "Let this focused drive move your intentions into form.",
    "harmony": "Let emotional harmony guide practical choices.",
}

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


def build_opening_summary(theme: str, raw: str, signs: Sequence[str], profile_name: str = "") -> str:
    sign_a = signs[0] if signs else "Libra"
    sign_b = signs[1] if len(signs) > 1 else sign_a
    descriptor = descriptor_from_text(theme, raw, profile_name=profile_name)
    focus = focus_from_text(theme, raw, profile_name=profile_name)
    article = _article(descriptor)
    first_sentence = (
        f"You ride {article} {descriptor} wave through today's {focus}—"
        f"{MICRO_PHRASES['opening']}"
    )
    backdrop = element_modality_line(sign_a, sign_b)
    return f"{first_sentence} {backdrop}"


def build_morning_paragraph(raw: str, profile_name: str, theme: str) -> str:
    descriptor = descriptor_from_text(raw, theme, profile_name=profile_name)
    focus = focus_from_text(raw, theme, default="momentum", profile_name=profile_name)
    sentence = (
        f"You set the tone by taking one intentional pause before leaning into {descriptor} {focus} today."
    )
    return sentence


def build_career_paragraph(
    raw: str, profile_name: str = "", tone_hint: str | None = None
) -> str:
    descriptor = descriptor_from_text(raw, default="steady", profile_name=profile_name)
    tone = tone_hint or tone_from_text(raw)
    if tone == "challenge":
        first = f"You steady {descriptor} demands by pacing commitments at work."
    else:
        first = f"You turn {descriptor} work into deliberate progress at work."
    second = MICRO_PHRASES["career"]
    return f"{first} {second}"


def build_love_paragraph(
    raw: str, profile_name: str = "", tone_hint: str | None = None
) -> str:
    descriptor = descriptor_from_text(raw, default="tender", profile_name=profile_name)
    tone = tone_hint or tone_from_text(raw)
    if tone == "challenge":
        return f"You ease relationship friction by listening with {descriptor} patience."
    return f"You nurture heart connections by sharing {descriptor} honesty."


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
    raw: str, theme: str, profile_name: str = "", tone_hint: str | None = None
) -> str:
    descriptor = descriptor_from_text(raw, theme, default="balanced", profile_name=profile_name)
    tone = tone_hint or tone_from_text(raw)
    if tone == "challenge":
        second = "Keep movements gentle and responsive to your body's signals."
    else:
        second = "Balance movement with rest so your body stays responsive."
    first = f"You protect wellbeing by honoring {descriptor} rhythms."
    return f"{first} {second}"


def build_finance_paragraph(
    raw: str, theme: str, profile_name: str = "", tone_hint: str | None = None
) -> str:
    descriptor = descriptor_from_text(raw, theme, default="calm", profile_name=profile_name)
    tone = tone_hint or tone_from_text(raw)
    if tone == "challenge":
        first = f"You navigate financial choices with {descriptor} patience today."
        second = "Review numbers before you commit to new moves."
    else:
        first = f"You let {descriptor} awareness guide each money choice today."
        second = MICRO_PHRASES["harmony"]
    return f"{first} {second}"


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
