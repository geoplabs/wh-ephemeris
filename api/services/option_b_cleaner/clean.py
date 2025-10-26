import re

from src.content.phrasebank import PhraseAsset, bullet_templates_for

_ORB = re.compile(r"\b\d+(\.\d+)?°\b")
_APPLYING_SEP = re.compile(r"\b(Applying|Separating)\b[^.]*\.?")
_SIGN_IN = re.compile(r";?\s*[A-Z][a-z]+ in [A-Z][a-z]+")
_ASPECT_WORDS = re.compile(r"\b(conjunction|sextile|square|trine|opposition)\b", re.I)
_ELLIPSES = re.compile(r"(?:\u2026|…|\.\.\.)")
_MULTISPACE = re.compile(r"\s{2,}")

_STOPWORDS = {
    "a",
    "an",
    "and",
    "around",
    "as",
    "by",
    "can",
    "channel",
    "focus",
    "for",
    "from",
    "in",
    "into",
    "may",
    "now",
    "of",
    "on",
    "should",
    "the",
    "this",
    "to",
    "today",
    "with",
    "you",
    "your",
}

_DIRECT_VERBS = {"review", "check", "plan", "stretch", "hydrate", "share", "breathe", "rest", "express", "address"}


def de_jargon(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = _APPLYING_SEP.sub("", s)
    s = _ORB.sub("", s)
    s = _SIGN_IN.sub("", s)
    s = _ASPECT_WORDS.sub("", s)
    s = _ELLIPSES.sub(" ", s)
    s = _MULTISPACE.sub(" ", s).strip()
    return s


def to_you_pov(s: str, profile_name: str) -> str:
    if not isinstance(s, str):
        return s
    s = re.sub(
        rf"^{re.escape(profile_name)}\s+(can|may|should)\b",
        lambda m: f"You {m.group(1)}",
        s,
        flags=re.I,
    )
    s = s.replace(profile_name, "You")
    s = re.sub(r"^you\b", "You", s)
    return s


def _keywords_for_bullet(text: str) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z']+", text)]
    keywords = [w for w in words if len(w) > 2 and w not in _STOPWORDS and not w.endswith("ly")]
    if not keywords:
        keywords = [w for w in words if w not in _STOPWORDS]
    if "drive" in keywords and "energy" in keywords:
        keywords = [w for w in keywords if w != "energy"]
    return keywords[:3] if keywords else ["steady"]


def _format_phrase(words: list[str], mode: str = "do") -> str:
    tokens = [w for w in words if w]
    has_harmonizing = "harmonizing" in tokens
    has_emotional = "emotional" in tokens
    has_energy = "energy" in tokens
    tokens = [w for w in tokens if w not in {"harmonizing", "emotional", "energy"}]
    combo: list[str] = []
    if has_harmonizing:
        combo.append("harmonizing")
    if has_emotional:
        combo.append("emotional")
    if has_energy:
        combo.append("energy")
    if combo:
        tokens = combo + tokens
    has_curious = "curious" in tokens
    has_inner = "inner" in tokens
    tokens = [w for w in tokens if w not in {"curious", "inner"}]
    curious_block: list[str] = []
    if has_curious:
        curious_block.append("curious")
    if has_inner:
        curious_block.append("inner")
    if curious_block:
        tokens = curious_block + tokens
    has_outer = "outer" in tokens
    has_persona = "persona" in tokens
    tokens = [w for w in tokens if w not in {"outer", "persona"}]
    if has_outer or has_persona:
        persona_block: list[str] = ["outer"] if has_outer else []
        if has_persona:
            persona_block.append("persona")
        tokens = persona_block + tokens
    if "curious" in tokens and "outer" in tokens:
        tokens = [w for w in tokens if w not in {"curious", "outer"}]
        tokens = ["curious", "outer"] + tokens
    if "disciplined" in tokens:
        replacement = "steady" if mode == "do" else "pushing"
        tokens = [replacement if w == "disciplined" else w for w in tokens]
    has_relationship = "relationships" in tokens or "relationship" in tokens
    if "challenges" in tokens and has_relationship:
        tokens = [w for w in tokens if w not in {"relationships", "relationship", "challenges"}]
        block = []
        if mode == "avoid" and "pushing" in tokens:
            tokens = [w for w in tokens if w != "pushing"]
            block.extend(["pushing", "relationship", "boundaries"])
        else:
            block.extend(["relationship", "boundaries"])
            if mode == "do" and "steady" in tokens:
                tokens = [w for w in tokens if w != "steady"]
                block.insert(0, "steady")
        tokens = block + tokens
    if "self" in tokens:
        tokens = ["self-expression" if w == "self" else w for w in tokens]
    if "self-expression" in tokens and "challenges" in tokens:
        tokens = ["focus" if w == "challenges" else w for w in tokens]
    if "period" in tokens:
        tokens = ["growth" if w == "period" else w for w in tokens]
    if "self-expression" in tokens and "priorities" in tokens:
        tokens = [w for w in tokens if w not in {"self-expression", "priorities"}]
        tokens = ["self-expression", "priorities"] + tokens
    if "self-expression" in tokens and "focus" in tokens:
        tokens = [w for w in tokens if w != "focus"]
    if "opportunity" in tokens:
        tokens = ["openings" if w == "opportunity" else w for w in tokens]
    if "intention" in tokens:
        tokens = ["intentions" if w == "intention" else w for w in tokens]
    if len(tokens) == 1 and tokens[0] == "steady":
        tokens.append("balance")
    phrase = " ".join(tokens)
    if not phrase:
        return "steady focus"
    return phrase


def _resolve_templates(area: str | None, mode: str, asset: PhraseAsset | None) -> tuple[str, ...]:
    if area:
        archetype = asset.archetype if asset else None
        intensity = asset.intensity if asset else None
        templates = bullet_templates_for(
            area,
            mode,
            archetype=archetype,
            intensity=intensity,
        )
        if templates:
            return templates
    return (
        "Focus on {phrase} today.",
        "Choose {phrase} now.",
        "Set {phrase} priorities today.",
        "Plan {phrase} today.",
    ) if mode == "do" else (
        "Avoid {phrase} today.",
        "Skip {phrase} now.",
        "Hold back from {phrase} today.",
        "Delay {phrase} moves today.",
    )


def imperative_bullet(s: str, order: int = 0, mode: str = "do", *, area: str | None = None, asset: PhraseAsset | None = None) -> str:
    s = de_jargon(s)
    s = re.sub(r"^(?:Try to|You should|Consider|Aim to)\s+", "", s, flags=re.I)
    words = _keywords_for_bullet(s)
    if mode == "avoid":
        words = [w for w in words if w != "avoid"]
    phrase_words = words
    if mode == "avoid":
        if not phrase_words:
            return "Avoid reactive conflicts today."
        if "relationship" in phrase_words and "boundaries" in phrase_words:
            phrase_words = ["pushing", "relationship", "boundaries"]
        elif phrase_words == ["steady"]:
            phrase_words = ["overloading", "commitments"]
    if mode == "do" and phrase_words and phrase_words[0] in _DIRECT_VERBS:
        verb = phrase_words[0].capitalize()
        phrase = _format_phrase(phrase_words[1:], mode)
        candidate = f"{verb} {phrase} today." if phrase else f"{verb} today."
        word_count = len(candidate.rstrip(".").split())
        if word_count < 3:
            candidate = f"{verb} with care today."
        return candidate
    templates = _resolve_templates(area, mode, asset)
    template = templates[order % len(templates)]
    # Trim phrase to keep word count between 3 and 10 once formatted
    for cut in range(len(phrase_words), 0, -1):
        phrase = _format_phrase(phrase_words[:cut], mode)
        candidate = template.format(phrase=phrase)
        word_count = len(candidate.rstrip(".").split())
        if 3 <= word_count <= 10:
            return candidate
    phrase = _format_phrase([words[0]], mode)
    candidate = template.format(phrase=phrase)
    return candidate


def clamp_sentences(paragraph: str, max_sentences: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    return " ".join(parts[:max_sentences]).strip()
