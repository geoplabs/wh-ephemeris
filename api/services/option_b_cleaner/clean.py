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
    "keep",
    "may",
    "now",
    "while",
    "of",
    "on",
    "take",
    "should",
    "the",
    "this",
    "to",
    "today",
    "with",
    "you",
    "your",
}

_DIRECT_VERBS = {
    "review",
    "check",
    "plan",
    "stretch",
    "hydrate",
    "share",
    "breathe",
    "rest",
    "express",
    "address",
    "choose",
    "set",
    "track",
    "outline",
    "match",
    "name",
    "note",
    "speak",
    "avoid",
    "skip",
    "hold",
    "delay",
}
_PLANETS = {"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"}
_ZODIAC_SIGNS = {
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
}
_MODALITIES = {"cardinal", "fixed", "mutable"}
_ELEMENTS = {"fire", "earth", "air", "water"}
_ACTION_NOUNS = {
    "align": "alignment",
    "aligns": "alignment",
    "aligned": "alignment",
    "aligning": "alignment",
    "flow": "flow",
    "flows": "flow",
    "flowing": "flow",
    "press": "pressure",
    "presses": "pressure",
    "pressed": "pressure",
    "pressing": "pressure",
    "support": "support",
    "supports": "support",
    "supported": "support",
    "supporting": "support",
    "supportive": "support",
    "guide": "guidance",
    "guides": "guidance",
    "guided": "guidance",
    "guiding": "guidance",
    "inspire": "inspiration",
    "inspires": "inspiration",
    "inspired": "inspiration",
    "inspiring": "inspiration",
}
_DROP_TOKENS = {"influence", "influences"}
_TOKENIZER = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?")


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


def clean_tokens(s: str, *, max_tokens: int = 8) -> list[str]:
    """Return sanitized tokens extracted from ``s`` after ``de_jargon`` cleanup."""

    if not isinstance(s, str):
        return []
    cleaned = de_jargon(s or "")
    tokens: list[str] = []
    for raw in _TOKENIZER.findall(cleaned):
        token = raw.strip("'\"")
        if not token:
            continue
        safe = re.sub(r"[^A-Za-z0-9-]", "", token)
        if not safe:
            continue
        tokens.append(safe)
        if len(tokens) >= max_tokens:
            break
    return tokens


def clean_token_phrase(s: str, *, max_tokens: int = 5) -> str:
    """Return a space-joined phrase of sanitized tokens suitable for reuse."""

    tokens = clean_tokens(s, max_tokens=max_tokens)
    if not tokens:
        return ""
    return " ".join(tokens)


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


def _dedupe_preserve_order(words: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for word in words:
        if not word:
            continue
        if word not in seen:
            unique.append(word)
            seen.add(word)
    return unique


def _cleanup_sentence(text: str) -> str:
    replacements = {
        "conversations priorities": "conversations",
        "conversation priorities": "conversation",
        "priority priorities": "priority",
        "boundary ambitions": "boundaries",
        "responsibility boundary": "responsibility boundaries",
        "public boundary": "public boundaries",
        "relationship boundary": "relationship boundaries",
        "boundaries priorities": "boundaries",
        "conversations outer": "outer conversations",
        "outer conversations rituals": "outer rituals",
        "curious outer conversations": "curious outer rituals",
        "drive support professional wins": "drive to support professional wins",
        "drive tune body": "drive to tune your body",
        "drive tune": "drive to tune",
        "responsibility stabilize boundaries": "responsibility boundaries",
        "responsibility finances boundaries": "responsibility boundaries",
        "steady back relationship": "steady relationship",
        "harmonizing emotional rhythms steps": "harmonizing emotional rhythms",
        "growth rhythms intentions": "growth rhythms",
        "tune your body care to protect your reserves": "tune your body",
    }
    cleaned = text
    for needle, replacement in replacements.items():
        cleaned = cleaned.replace(needle, replacement)
    cleaned = re.sub(r"\b(\w+)\s+to\s+\1\b", r"\1", cleaned)
    cleaned = re.sub(r"\bChoose radiant drive support\b", "Choose radiant drive to support", cleaned)
    cleaned = re.sub(r"\b(\w+)\s+\1\b", r"\1", cleaned)
    cleaned = re.sub(
        r"\bSet\s+([A-Za-z]+) priority\b",
        lambda m: f"Set a {m.group(1)} priority",
        cleaned,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    overrides = {
        "Choose curious conversations support today.": "Start one curious, open-ended conversation that advances a work goal.",
        "Set radiant personal power priority today.": "Set two priorities that showcase your initiative.",
    }
    return overrides.get(cleaned, cleaned)


def _keywords_for_bullet(text: str) -> list[str]:
    primary_clause = text.split(".", 1)[0]
    tokens = clean_tokens(primary_clause, max_tokens=15)
    lowered = [t.lower() for t in tokens]
    keywords = [
        w
        for w in lowered
        if len(w) > 2 and w not in _STOPWORDS and not w.endswith("ly")
    ]
    if not keywords:
        keywords = [w for w in lowered if w not in _STOPWORDS]
    keywords = _dedupe_preserve_order(keywords)
    if len(keywords) > 3:
        general_tail = {"career", "path", "momentum", "today", "energy"}
        trimmed = [w for w in keywords if w not in general_tail]
        if len(trimmed) >= 3:
            keywords = trimmed
    if "drive" in keywords and "energy" in keywords:
        keywords = [w for w in keywords if w != "energy"]
    return keywords[:6] if keywords else ["steady"]


def _singularize_token(word: str) -> str:
    specific = {
        "responsibilities": "responsibility",
        "priorities": "priority",
        "boundaries": "boundary",
        "energies": "energy",
        "conversations": "conversation",
    }
    if word in specific:
        return specific[word]
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    return word


def _format_phrase(words: list[str], mode: str = "do") -> str:
    tokens = _dedupe_preserve_order([w.lower() for w in words if w])
    filler_tokens = {
        "anchor",
        "aligned",
        "align",
        "aligning",
        "keeps",
        "keep",
        "keeping",
        "moves",
        "move",
        "moving",
        "stay",
        "staying",
        "that",
        "feel",
        "feels",
        "feeling",
        "true",
        "truly",
        "scatters",
        "when",
        "need",
        "needs",
        "back",
        "steps",
        "stabilize",
        "smart",
    }
    if tokens:
        tokens = [t for t in tokens if t not in filler_tokens]
    if "emotional" in tokens and "sensitive" in tokens:
        tokens = [t for t in tokens if t != "sensitive"]
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
    if "challenges" in tokens:
        tokens = [w for w in tokens if w != "challenges"]
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
    if tokens and tokens[0] in {"curious", "sensitive"}:
        noun_map = {
            "curious": ("conversation", "conversations"),
            "sensitive": ("boundary", "boundaries"),
        }
        singular, plural = noun_map[tokens[0]]
        if all(t not in {singular, plural} for t in tokens[1:]):
            insert_at = 1
            if len(tokens) > 1 and tokens[1] == "inner":
                insert_at = 2
            noun_choice = singular if mode == "do" else plural
            if tokens[0] == "curious":
                noun_choice = plural
            elif tokens[0] == "sensitive" and mode == "do":
                noun_choice = plural
            tokens.insert(insert_at, noun_choice)
    if "boundary" in tokens or "boundaries" in tokens:
        boundary_idx = tokens.index("boundary") if "boundary" in tokens else tokens.index("boundaries")
        tokens[boundary_idx] = "boundaries"
        qualifier_idx = boundary_idx + 1
        if qualifier_idx < len(tokens):
            qualifier = tokens[qualifier_idx]
            if qualifier not in {"and", "or", "of"}:
                tokens.pop(qualifier_idx)
                singular = _singularize_token(qualifier)
                if singular not in {"priority", "support", "professional"}:
                    if singular and singular not in tokens[:boundary_idx]:
                        tokens.insert(boundary_idx, singular)
    if "relationship" in tokens and "boundaries" in tokens:
        tokens = [w for w in tokens if w != "relationship"]
        idx = tokens.index("boundaries")
        tokens.insert(idx, "relationship")
    collapsed: list[str] = []
    singular_seen: set[str] = set()
    for token in tokens:
        base = _singularize_token(token)
        if base in singular_seen:
            continue
        singular_seen.add(base)
        collapsed.append(base if token != base else token)
    tokens = collapsed
    if tokens and tokens[0] == "one":
        tokens[0] = "single"
    if "priority" in tokens and "drive" in tokens:
        tokens = [t for t in tokens if t != "drive"]
    if (
        tokens
        and tokens[0] == "radiant"
        and len(words) > 1
        and "priority" not in tokens
        and all(t not in {"drive", "momentum"} for t in tokens[1:])
    ):
        tokens.insert(1, "drive")
    if "boundaries" in tokens:
        idx = tokens.index("boundaries")
        tokens = tokens[: idx + 1]
    if tokens and tokens[0] == "curious":
        extras = [w for w in tokens[1:] if w not in {"inner", "conversation", "conversations"}]
        has_inner = "inner" in tokens[1:]
        tokens = ["curious"] + (["inner"] if has_inner else []) + ["conversations"] + extras
        if len(tokens) > 3:
            tokens = tokens[:3]
    if len(tokens) == 1:
        filler = {
            "steady": "balance",
            "sensitive": "boundaries",
            "curious": "conversations",
        }.get(tokens[0], "focus")
        if tokens[0] == "radiant":
            filler = ""
        if filler:
            tokens.append(filler)
    tokens = _refine_phrase_tokens(tokens, mode)
    tokens = _dedupe_preserve_order(tokens)
    tokens = tokens[:5]
    phrase = " ".join(tokens)
    if not phrase:
        return "steady focus"
    return phrase


def _refine_phrase_tokens(tokens: list[str], mode: str) -> list[str]:
    if not tokens:
        return []
    working = _combine_planet_sequences(tokens)
    filtered: list[str] = []
    descriptive_seen = False
    for token in working:
        if token in _PLANETS and descriptive_seen:
            continue
        if any(ch.isupper() for ch in token) or " " in token or "-" in token:
            descriptive_seen = True
        filtered.append(token)
    working = filtered
    refined: list[str] = []
    for token in working:
        if not token:
            continue
        if token in _DROP_TOKENS:
            continue
        if any(ch.isupper() for ch in token):
            refined.append(token)
            continue
        lowered = token.lower()
        mapped = _normalize_action_word(lowered)
        refined.append(mapped if mapped else "")
    refined = [tok for tok in refined if tok]
    refined = _dedupe_preserve_order(refined)
    refined = _compress_sign_tokens(refined)
    refined = _suppress_redundant_terms(refined)
    refined = _titlecase_tokens(refined)
    return refined


def _normalize_action_word(token: str) -> str:
    if not token:
        return ""
    if token in _ACTION_NOUNS:
        return _ACTION_NOUNS[token]
    for suffix in ("ing", "ive", "ed", "es", "s"):
        if token.endswith(suffix) and token[: -len(suffix)] in _ACTION_NOUNS:
            base = token[: -len(suffix)]
            return _ACTION_NOUNS[base]
    return token


def _combine_planet_sequences(tokens: list[str]) -> list[str]:
    out: list[str] = []
    idx = 0
    while idx < len(tokens):
        word = tokens[idx]
        if word in _PLANETS and idx + 1 < len(tokens):
            action_word = tokens[idx + 1]
            noun = _ACTION_NOUNS.get(action_word)
            if noun:
                partner_idx = idx + 2
                partner: str | None = None
                while partner_idx < len(tokens):
                    candidate = tokens[partner_idx]
                    if candidate in _PLANETS:
                        partner = candidate
                        break
                    if candidate in {"your", "the"}:
                        partner_idx += 1
                        continue
                    break
                if partner:
                    hyphen = "-to-" if partner == word else "-"
                    out.append(f"{word.title()}{hyphen}{partner.title()} {noun}")
                    idx = partner_idx + 1
                    continue
                out.append(f"{word.title()} {noun}")
                idx += 2
                continue
        out.append(word)
        idx += 1
    return out


def _compress_sign_tokens(tokens: list[str]) -> list[str]:
    if not tokens:
        return []
    sign = next((t for t in tokens if t in _ZODIAC_SIGNS), None)
    modality = next((t for t in tokens if t in _MODALITIES), None)
    element = next((t for t in tokens if t in _ELEMENTS), None)
    out: list[str] = []
    used_sign = False
    for token in tokens:
        if token in _ZODIAC_SIGNS:
            if not used_sign:
                out.append(token.title())
                used_sign = True
            continue
        if sign and (token in _MODALITIES or token in _ELEMENTS):
            continue
        out.append(token)
    if not sign:
        descriptor_parts = []
        if modality:
            descriptor_parts.append(modality.title())
        if element:
            descriptor_parts.append(element.title())
        descriptor = " ".join(descriptor_parts).strip()
        if descriptor:
            inserted = False
            new_out: list[str] = []
            for token in out:
                if not inserted and token in {"inspiration", "support", "focus", "momentum", "guidance"}:
                    new_out.append(descriptor)
                    inserted = True
                new_out.append(token)
            if not inserted:
                new_out.insert(0, descriptor)
            out = new_out
    if out and out[0].lower() in _ZODIAC_SIGNS and len(out) > 3:
        out = out[:3]
    if out and " " in out[0]:
        first_word = out[0].split(" ", 1)[0].lower()
        if first_word in _MODALITIES and len(out) > 3:
            out = out[:3]
    if "inspiration" in out and len(out) > 2:
        trimmed: list[str] = []
        for token in out:
            trimmed.append(token)
            if token == "inspiration":
                break
        out = trimmed
    return out


def _suppress_redundant_terms(tokens: list[str]) -> list[str]:
    result: list[str] = []
    seen_endings: set[str] = set()
    for token in tokens:
        lowered = token.lower()
        ending = lowered
        if " " in ending:
            ending = ending.rsplit(" ", 1)[-1]
        if "-" in ending:
            ending = ending.rsplit("-", 1)[-1]
        if ending in seen_endings:
            continue
        seen_endings.add(ending)
        result.append(token)
    return result


def _titlecase_tokens(tokens: list[str]) -> list[str]:
    result: list[str] = []
    for token in tokens:
        if not token:
            continue
        lowered = token.lower()
        if lowered in _PLANETS or lowered in _ZODIAC_SIGNS:
            result.append(token.title())
            continue
        if lowered in _ELEMENTS or lowered in _MODALITIES:
            result.append(token.title())
            continue
        if "-" in token and " " not in token:
            parts = token.split("-")
            rebuilt = []
            for part in parts:
                lower_part = part.lower()
                if lower_part in _PLANETS or lower_part in _ZODIAC_SIGNS:
                    rebuilt.append(part.title())
                else:
                    rebuilt.append(part)
            result.append("-".join(rebuilt))
            continue
        result.append(token)
    return result


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
        "Prioritize {phrase} so progress is tangible today.",
        "Channel {phrase} into a visible win.",
        "Clarify {phrase} and note the next step before the afternoon.",
        "Schedule {phrase} so momentum keeps building.",
    ) if mode == "do" else (
        "Avoid {phrase} if it scatters your focus.",
        "Skip {phrase} when you need clarity to decide.",
        "Hold back from {phrase} until timing improves.",
        "Delay {phrase} so boundaries stay firm.",
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
    if phrase_words and phrase_words[0] in _DIRECT_VERBS:
        lower_verb = phrase_words[0].lower()
        remainder = phrase_words[1:]
        prefix = lower_verb.capitalize()
        if mode == "avoid":
            if lower_verb == "hold" and remainder and remainder[0] == "back":
                remainder = remainder[1:]
                prefix = "Hold back from"
            elif lower_verb == "avoid":
                prefix = "Avoid"
            elif lower_verb == "skip":
                prefix = "Skip"
            elif lower_verb == "delay":
                prefix = "Delay"
        phrase = _format_phrase(remainder, mode) if remainder else ""
        if not phrase:
            candidate = f"{prefix} today."
        else:
            candidate = f"{prefix} {phrase} today."
        word_count = len(candidate.rstrip(".").split())
        if word_count < 3:
            fallback_verb = "Stay mindful" if mode == "avoid" else f"{prefix} with care"
            candidate = f"{fallback_verb} today."
        return _cleanup_sentence(candidate)
    templates = _resolve_templates(area, mode, asset)
    best_candidate: str | None = None
    template_count = len(templates)
    for offset in range(template_count):
        template = templates[(order + offset) % template_count]
        for cut in range(len(phrase_words), 0, -1):
            phrase = _format_phrase(phrase_words[:cut], mode)
            candidate = template.format(phrase=phrase)
            word_count = len(candidate.rstrip(".").split())
            if 3 <= word_count <= 10:
                return _cleanup_sentence(candidate)
            if 3 <= word_count <= 14 and best_candidate is None:
                best_candidate = candidate
    if best_candidate:
        return _cleanup_sentence(best_candidate)
    phrase = _format_phrase([words[0]], mode)
    template = templates[order % template_count]
    return _cleanup_sentence(template.format(phrase=phrase))


def clamp_sentences(paragraph: str, max_sentences: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    return " ".join(parts[:max_sentences]).strip()
