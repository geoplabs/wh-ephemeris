from __future__ import annotations

import hashlib
import random
import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence, Tuple, List, Optional

from .clean import de_jargon, to_you_pov
from .event_tokens import MiniTemplate, event_phrase, render_mini_template
from src.content.storylets import is_phase3_enabled, get_transit_opener


# ---------- Regexes & small phonetics helpers ----------

_ARTICLE_PATTERN = re.compile(r"\b([Aa]n?)\s+([A-Za-z][\w-]*)")
_REPEATED_WORD_PATTERN = re.compile(r"\b(\w+)(\s+\1\b)+", re.IGNORECASE)

_SOFT_H_PREFIXES = ("hon", "hour", "heir")
_HARD_VOWEL_PREFIXES = ("uni", "eu", "one")
# Acronyms whose initial letter is pronounced with a vowel sound ("an MBA")
_ACRONYM_AN = set("AEFHILMNORSX")

# Punctuation/whitespace normalization
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")
_PUNCT_RUN = re.compile(r"([.!?]){2,}")
_DANGLING_COMMA = re.compile(r",\s*([.!?])")

# Skywatch and aspect smoothing (plain-English evidence)
_SKYWATCH = re.compile(r"(?:Special sky watch:.*?\.|Full Moon:.*?\.)", re.I)

# First-pass lexical smoothing of aspect verbs
_ASPECT_SMOOTH: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bflows with\b", re.I), "supports"),
    (re.compile(r"\bpresses on\b", re.I), "puts pressure on"),
    (re.compile(r"\baligns with\b", re.I), "spotlights"),
    # collapse long astro phrasing to a human label
    (
        re.compile(
            r"\b(?:separating|applying)\b.*?\b(trine|sextile|square|opposition|conjunction)\b.*?(?:\d+(?:\.\d+)?°\s*orb)?",
            re.I,
        ),
        r"\1",
    ),
    (re.compile(r"\bfrom [A-Z][a-z]+ to [A-Z][a-z]+\b"), ""),  # drop sign travel
    (re.compile(r"\b(?:trine|sextile)\b", re.I), "a supportive aspect"),
    (re.compile(r"\b(?:square|opposition)\b", re.I), "a tense aspect"),
    (re.compile(r"\bconjunction\b", re.I), "an amplifying alignment"),
]


# ---------- Astrology scaffolding ----------

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


# ---------- Lexicon ----------

STOPWORDS = {
    "a", "and", "can", "may", "if", "into", "lean", "let", "set", "should", "stay", "turn", "feel",
    "channel", "you're", "you", "ride", "bring", "guide", "attached", "single", "take", "tackle",
    "move", "notably", "powerfully", "the", "this", "with", "today", "your", "energy",
}

# Expanded cues to improve tone detection, including common astro terms
POSITIVE_CUES = {
    "radiant", "harmonizing", "support", "ease", "growth", "opportunity", "vibrant",
    "flow", "opening", "trine", "sextile", "gift", "easeful", "aligned", "supportive",
}

CHALLENGE_CUES = {
    "challenge", "friction", "pressure", "tense", "demand", "intense", "rigid", "strain",
    "square", "opposition", "block", "delay", "inhibit", "conflict", "hard",
}

# Intensity cues (used to add pacing guidance when a day is “loud”)
INTENSITY_PHRASES = {
    "full moon", "new moon", "blood moon", "eclipse", "solar eclipse", "lunar eclipse",
    "retrograde", "station", "exact hit", "exact aspect", "supermoon",
}

# Prioritize relationships + synonyms over work; include plurals
FOCUS_MAP = (
    # Relationships first
    ("relationships", "relationships"),
    ("relationship", "relationships"),
    ("partner", "relationships"),
    ("romance", "relationships"),
    ("love", "heart space"),

    # Heart/feelings
    ("heart", "heart space"),
    ("emotional", "emotional rhythms"),

    # Money/finance
    ("finances", "financial choices"),
    ("finance", "financial choices"),
    ("money", "money moves"),

    # Work/career
    ("career", "career path"),
    ("drive", "ambitions"),
    ("work", "work"),

    # Phase expansions
    ("health", "wellness rituals"),
    ("body", "wellness rituals"),
    ("communication", "communication style"),
    ("creative", "creative projects"),
    ("routine", "daily routines"),
    ("boundary", "personal boundaries"),
    ("collaboration", "collaborative efforts"),
    ("solo", "solo work"),
    ("long-term", "long-term plans"),
    ("immediate", "immediate actions"),
    ("learning", "learning process"),
    ("teaching", "teaching approach"),
    ("family", "family dynamics"),
    ("home", "home environment"),
    ("spiritual", "spiritual practice"),
    ("mental", "mental clarity"),
    ("physical", "physical energy"),
    ("rest", "rest and recovery"),
    ("growth", "personal growth"),
    ("stability", "stability goals"),
    ("change", "transitions"),
    ("decision", "decision-making"),
    ("travel", "travel plans"),
    ("social", "social circles"),
    ("network", "networking efforts"),
    ("visibility", "public visibility"),
    ("persona", "outer persona"),
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
    # Phase expansions (curated adjectives)
    "creative": "creative",
    "grounded": "grounded",
    "flowing": "flowing",
    "resilient": "resilient",
    "intentional": "intentional",
    "expansive": "expansive",
    "receptive": "receptive",
    "dynamic": "dynamic",
    "measured": "measured",
    "playful": "playful",
    "serious": "serious",
    "determined": "determined",
    "curious": "curious",
    "patient": "patient",
    "urgent": "urgent",
    "spacious": "spacious",
    "compressed": "compressed",
    "gentle": "gentle",
    "fierce": "fierce",
    "centered": "centered",
    "scattered": "scattered",
    "harmonious": "harmonious",
    "tense": "tense",
    "clear": "clear",
    "foggy": "foggy",
    "radiant": "radiant",
    "subdued": "subdued",
    "powerful": "powerful",
    "delicate": "delicate",
    "bold": "bold",
    "cautious": "cautious",
    "trusting": "trusting",
    "guarded": "guarded",
    "open": "open",
    "reflective": "reflective",
}

# Provide a richer alternative palette for repetition control
_ALTERNATIVES = {
    "radiant": ["vibrant", "clear", "focused", "purposeful", "energized"],
    "steady":  ["grounded", "consistent", "measured", "reliable"],
    "gentle":  ["soft", "calm", "tender", "easy"],
    "bold":    ["decisive", "confident", "assertive", "powerful"],
}


# ---------- Storylets (same keys / more variety) ----------

STORYLETS: dict[str, dict[str, Any]] = {
    "default": {
        "openers": {
            "support": (
                "You move with {descriptor} confidence through today's {focus}.",
                "Your {descriptor} rhythm keeps today's {focus} flowing forward.",
                "You keep a {descriptor} tempo as today's {focus} opens up.",
                "With {descriptor} ease, you navigate today's {focus}.",
            ),
            "challenge": (
                "You steady {descriptor} turbulence inside today's {focus}.",
                "Your {descriptor} resolve helps you navigate today's {focus} demands.",
                "You keep a {descriptor} grip on what's shifting in today's {focus}.",
                "You pace yourself with {descriptor} patience across today's {focus}.",
            ),
            "neutral": (
                "You bring {descriptor} awareness to today's {focus}.",
                "Your {descriptor} pace sets the tone for today's {focus}.",
                "You keep a {descriptor} view on the whole of today's {focus}.",
                "A {descriptor} presence supports today's {focus}.",
            ),
        },
        "coaching": (
            "Name the step that matters most so you stay anchored.",
            "Pause for one breath to notice what still feels aligned.",
            "Document a small win so progress remains tangible.",
            "Decide one boundary you'll honor even if plans move.",
            "Share one clear ask so collaboration stays easy.",
        ),
        "closers": {
            "support": (
                "Keep trusting the rituals that already work.",
                "Let steady choices show you the path forward.",
                "Carry this momentum with quiet confidence.",
            ),
            "challenge": (
                "Protect your bandwidth so pressure can't run the day.",
                "Move gently but deliberately—you're allowed to pace yourself.",
                "Keep margins wide; let clarity arrive before action.",
            ),
            "neutral": (
                "Return to the practices that remind you why you're doing this.",
                "Stay with the process, one grounded choice at a time.",
                "Let consistency build the result you want.",
            ),
        },
    },
    "career": {
        "openers": {
            "support": (
                "You channel {descriptor} drive into today's {focus}.",
                "Your {descriptor} ambition steadies today's {focus}.",
                "With {descriptor} clarity, you guide today's {focus}.",
            ),
            "challenge": (
                "You steady {descriptor} pressure across today's {focus}.",
                "Your {descriptor} grit keeps today's {focus} in motion.",
                "You keep {descriptor} focus while priorities shift.",
            ),
            "neutral": (
                "You organize {descriptor} focus around today's {focus}.",
                "Your {descriptor} pace sets an intentional tone for today's {focus}.",
                "You frame today's {focus} with {descriptor} structure.",
            ),
        },
        "coaching": (
            "Break the workload into deliberate moves you can trust.",
            "Map the moving pieces before you commit to the next milestone.",
            "Share an update that keeps collaborators aligned.",
            "Time-box the hardest piece and start there.",
        ),
        "closers": {
            "support": (
                "Let steady wins show the momentum you're building.",
                "Lean into allies who reinforce your vision.",
                "Ship the small thing; compounding wins matter.",
            ),
            "challenge": (
                "Keep pacing yourself so the pressure doesn't run the show.",
                "Protect your bandwidth with clear boundaries.",
                "Defer non-essentials; keep the core moving.",
            ),
            "neutral": (
                "Stay with the process that makes results repeatable.",
                "Keep your workflow anchored to what truly matters.",
                "Let clarity set the sequence of next steps.",
            ),
        },
    },
    "love": {
        "openers": {
            "support": (
                "You bring {descriptor} care into today's {focus}.",
                "Your {descriptor} presence softens today's {focus}.",
                "You meet today's {focus} with {descriptor} sincerity.",
            ),
            "challenge": (
                "You ease {descriptor} tension inside today's {focus}.",
                "Your {descriptor} honesty steadies today's {focus} conversations.",
                "You keep repairs gentle and {descriptor}.",
            ),
            "neutral": (
                "You invite {descriptor} attention into today's {focus}.",
                "Your {descriptor} pace keeps today's {focus} sincere.",
                "You allow space for {descriptor} connection to unfold.",
            ),
        },
        "coaching": (
            "Ask one curious question so connection feels mutual.",
            "Share how your body feels when a moment lands right.",
            "Let listening lead before you decide the next move.",
            "Name the need; keep the tone warm.",
        ),
        "closers": {
            "support": (
                "Follow the conversations that feel nourishing.",
                "Let shared rituals remind you you're supported.",
                "Keep the softness you found today.",
            ),
            "challenge": (
                "Keep soft boundaries so tenderness can return.",
                "Name what you need while staying receptive.",
                "Slow the pace; clarity is kind.",
            ),
            "neutral": (
                "Let the pace stay human—no need to force answers.",
                "Stay tuned to the gestures that feel genuine.",
                "Let small signs guide the next step.",
            ),
        },
    },
    "health": {
        "openers": {
            "support": (
                "You honor {descriptor} rhythms through today's {focus}.",
                "Your {descriptor} awareness protects today's {focus} rituals.",
                "You give your body {descriptor} space to respond.",
            ),
            "challenge": (
                "You soften {descriptor} strain across today's {focus}.",
                "Your {descriptor} pacing defuses today's {focus} demands.",
                "You choose {descriptor} adjustments that respect limits.",
            ),
            "neutral": (
                "You bring {descriptor} care into today's {focus}.",
                "Your {descriptor} presence steadies today's {focus} routines.",
                "You tune into {descriptor} signals before you push.",
            ),
        },
        "coaching": (
            "Schedule breathers so your body feels consulted.",
            "Hydrate and stretch before momentum carries you away.",
            "Track one ritual that keeps your system grounded.",
            "Wind down early; sleep is strategy.",
        ),
        "closers": {
            "support": (
                "Let gentle structure support your wellbeing.",
                "Stay loyal to the practices that replenish you.",
                "Carry the ease forward, even in busy hours.",
            ),
            "challenge": (
                "Keep adjustments responsive so recovery stays on track.",
                "Trust the feedback your body keeps sharing.",
                "Scale effort down; reduce friction on purpose.",
            ),
            "neutral": (
                "Balance effort with rest so your energy can reset.",
                "Stay present with the signals that guide your care.",
                "Let the simple habit be enough today.",
            ),
        },
    },
    "finance": {
        "openers": {
            "support": (
                "You guide {descriptor} awareness through today's {focus}.",
                "Your {descriptor} clarity shapes today's {focus} choices.",
                "You align spending with {descriptor} intention.",
            ),
            "challenge": (
                "You bring {descriptor} patience to today's {focus} decisions.",
                "Your {descriptor} caution steadies today's {focus} review.",
                "You keep risk small and {descriptor}.",
            ),
            "neutral": (
                "You organize {descriptor} strategy around today's {focus}.",
                "Your {descriptor} pacing makes today's {focus} sustainable.",
                "You keep perspective {descriptor} as you plan.",
            ),
        },
        "coaching": (
            "Check the numbers twice before you commit.",
            "Match each expense to the feeling it delivers.",
            "Journal one win that proves your plan is working.",
            "Hold discretionary moves until clarity settles.",
        ),
        "closers": {
            "support": (
                "Let aligned choices build your long game.",
                "Trust the budget that keeps breathing room intact.",
                "Keep momentum but protect reserves.",
            ),
            "challenge": (
                "Keep big moves on hold until the math confirms it.",
                "Protect resources by filtering decisions through calm.",
                "Delay non-essentials; fund what's core.",
            ),
            "neutral": (
                "Stay curious about where your focus is funding momentum.",
                "Let steady pacing make each decision easier to trust.",
                "Refine the plan; don't rush the commit.",
            ),
        },
    },
}


# ---------- Utilities ----------

def _story_seed(*parts: Any) -> int:
    """Stable-ish seed from content for deterministic variety."""
    material = "|".join(str(part) for part in parts if part not in {None, ""}) or "story"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _sanitize_spaces(text: str) -> str:
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _DANGLING_COMMA.sub(r"\1", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _PUNCT_RUN.sub(lambda m: m.group(1), text)
    return text.strip()


def _collapse_repeated_words(text: str) -> str:
    return _REPEATED_WORD_PATTERN.sub(lambda m: m.group(1), text)


def _ensure_sentence(text: str) -> str:
    cleaned = _sanitize_spaces(_collapse_repeated_words((text or "").strip()))
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


def fix_indefinite_articles(text: str) -> str:
    """Switch 'a/an' based on pronunciation heuristics (incl. acronyms)."""
    def _article(word: str) -> str:
        if not word:
            return "a"
        if word.isupper() and word[0] in _ACRONYM_AN:
            return "an"
        lowered = word.lower()
        if any(lowered.startswith(prefix) for prefix in _SOFT_H_PREFIXES):
            return "an"
        if lowered[0] in "aeiou":
            if any(lowered.startswith(prefix) for prefix in _HARD_VOWEL_PREFIXES):
                return "a"
            return "an"
        return "a"

    def repl(match: re.Match[str]) -> str:
        article, word = match.group(1), match.group(2)
        desired = _article(word)
        if desired == article.lower():
            return match.group(0)
        replacement = desired.capitalize() if article[0].isupper() else desired
        return f"{replacement} {word}"

    return _ARTICLE_PATTERN.sub(repl, text)


def _clean_text(text: str, profile_name: str) -> str:
    cleaned = de_jargon(text or "")
    return to_you_pov(cleaned, profile_name)


def _polish_sentence(s: str) -> str:
    return fix_indefinite_articles(_ensure_sentence(_sanitize_spaces(s or "")))


def _keywords_from_text(texts: Iterable[str], profile_name: str = "") -> List[str]:
    tokens: List[str] = []
    blocked: set[str] = set()
    if profile_name:
        blocked.update(re.findall(r"[a-z']+", profile_name.lower()))
    for text in texts:
        cleaned = de_jargon(text or "").lower()
        tokens.extend(re.findall(r"[a-z']+", cleaned))
    if blocked:
        tokens = [t for t in tokens if t not in blocked]
    return tokens


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("–", "-").replace("—", "-")
    return s.casefold().strip()


def _stable_index(key: str, n: int) -> int:
    h = hashlib.blake2b(key.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(h, "big") % max(1, n)


def _combined_text(*texts: str) -> str:
    return _norm(" ".join(filter(None, texts)))


def _contains_any_phrase(haystack: str, phrases: Iterable[str]) -> bool:
    h = " " + haystack.lower() + " "
    for p in phrases:
        p_clean = " " + p.lower().strip() + " "
        if p_clean in h:
            return True
    return False


# ---------- Scoring: descriptor, focus, tone, intensity ----------

def descriptor_from_text(
    *texts: str,
    default: str = "steady",
    profile_name: str = "",
    recent: Iterable[str] = (),
) -> str:
    """
    Pick a descriptor with anti-repetition and stable variability.
    - Stable hashing for option selection.
    - Cleans case/unicode/apostrophes/hyphens.
    - Curated alternatives for overused descriptors.
    - Falls back to varied default if nothing found.
    """
    recent_set = {_norm(x) for x in recent}
    key_base = _norm(" ".join(texts)) + "|" + _norm(profile_name or "")

    for token in _keywords_from_text(texts, profile_name=profile_name):
        tok = _norm(token)
        if tok.endswith("'s"):
            tok = tok[:-2]
        if len(tok) <= 2 or tok.endswith("ly") or tok in STOPWORDS:
            continue
        descriptor = _norm(DESCRIPTOR_OVERRIDES.get(tok, tok))
        if descriptor in _ALTERNATIVES:
            choices = [c for c in _ALTERNATIVES[descriptor] if _norm(c) not in recent_set] or _ALTERNATIVES[descriptor]
            idx = _stable_index(key_base + "|" + descriptor, len(choices))
            return choices[idx]
        return descriptor

    d = _norm(default)
    if d in _ALTERNATIVES:
        choices = [c for c in _ALTERNATIVES[d] if _norm(c) not in recent_set] or _ALTERNATIVES[d]
        idx = _stable_index(key_base + "|_default", len(choices))
        return choices[idx]
    return default


def focus_from_text(*texts: str, default: str = "path", profile_name: str = "") -> str:
    combined = " ".join(filter(None, texts)).lower()
    # Remove name parts as whole words
    if profile_name:
        for part in re.findall(r"[a-z]+", profile_name.lower()):
            combined = re.sub(rf"\b{re.escape(part)}\b", "", combined)
    for key, focus in FOCUS_MAP:
        if re.search(rf"\b{re.escape(key)}\b", combined):
            return focus
    return default


def tone_from_text(*texts: str) -> str:
    combined = " ".join(filter(None, texts)).lower()
    def _count_cues(cues: set[str]) -> int:
        return sum(len(re.findall(rf"\b{re.escape(cue)}\b", combined)) for cue in cues)
    pos = _count_cues(POSITIVE_CUES)
    neg = _count_cues(CHALLENGE_CUES)
    if neg > pos:
        return "challenge"
    if pos > neg:
        return "support"
    return "neutral"


def intensity_from_text(*texts: str) -> str:
    """
    Returns 'high' if eclipse/full-moon/retrograde/etc. cues are present,
    otherwise 'normal'. Use to add pacing guidance on louder days.
    """
    combined = " ".join(filter(None, texts)).lower()
    return "high" if _contains_any_phrase(combined, INTENSITY_PHRASES) else "normal"


def _normalize_tone_label(value: Optional[str]) -> str:
    if not value:
        return "neutral"
    lowered = value.strip().lower()
    if lowered.startswith("tone:"):
        lowered = lowered.split(":", 1)[1]
    if lowered not in {"support", "challenge", "neutral"}:
        return "neutral"
    return lowered


# ---------- Storylet rendering ----------

def _storylet_pool(area: str, section: str, tone: str, event: Mapping[str, Any] | None = None) -> Sequence[str]:
    # Phase 3: Use transit-specific templates for openers if enabled
    if section == "openers" and event and is_phase3_enabled():
        transit_body = (event.get("transit_body") or "").lower()
        if transit_body:
            tone_key = tone if tone in {"support", "challenge", "neutral"} else "neutral"
            area_pool = STORYLETS.get(area, {})
            fallback_options: Sequence[str] = ()
            target = area_pool.get(section)
            if isinstance(target, Mapping):
                fallback_options = target.get(tone_key) or target.get("neutral", ())
            elif isinstance(target, Sequence):
                fallback_options = target
            if not fallback_options:
                default_pool = STORYLETS.get("default", {})
                fallback = default_pool.get(section)
                if isinstance(fallback, Mapping):
                    fallback_options = fallback.get(tone_key) or fallback.get("neutral", ()) or ()
                elif isinstance(fallback, Sequence):
                    fallback_options = fallback
            transit_templates = get_transit_opener(transit_body, fallback_options)
            if transit_templates and transit_templates != tuple(fallback_options):
                return transit_templates

    tone_key = tone if tone in {"support", "challenge", "neutral"} else "neutral"
    area_pool = STORYLETS.get(area, {})
    options: Sequence[str] = ()
    target = area_pool.get(section)
    if isinstance(target, Mapping):
        options = target.get(tone_key) or target.get("neutral", ())
    elif isinstance(target, Sequence):
        options = target
    if options:
        return options
    default_pool = STORYLETS.get("default", {})
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
    event: Mapping[str, Any] | None = None,
) -> str:
    options = _storylet_pool(area, section, tone, event)
    template = _deterministic_choice(options, seed, default)
    if not template:
        return default
    try:
        return template.format(**tokens)
    except (KeyError, ValueError):
        return default


# ---------- Aspect smoothing ----------

def _post_aspect_cleanups(s: str) -> str:
    # Normalize dashes (en, em, non-breaking) to ASCII hyphen
    s = s.replace("–", "-").replace("—", "-").replace("-", "-")

    # Convert "- a separating/applying ... at 1.23° orb" -> " (separating, 1.23° orb)"
    s = re.sub(
        r"\s*[-]\s*a\s*(separating|applying)\s*(?:\w+)?\s*(?:at\s*)?(\d+(?:\.\d+)?°\s*orb)\b",
        r" (\1, \2)",
        s,
        flags=re.I,
    )
    # Fallback: "- a separating/applying" (no orb) -> " (separating)"
    s = re.sub(
        r"\s*[-]\s*a\s*(separating|applying)\b(?:\s+\w+)?",
        r" (\1)",
        s,
        flags=re.I,
    )

    # " - supportive/flowing/alignment" -> " supportive/flowing/alignment"
    s = re.sub(r"\s*-\s*(?:a\s*)?(supportive|flowing|alignment)\b", r" \1", s, flags=re.I)

    # Possessive + article glitches: "your-an", "your - a" -> "your"
    s = re.sub(r"\byour\s*-\s*(?:an|a)\b", "your", s, flags=re.I)
    s = re.sub(r"\byour\s+(?:an|a)\b", "your", s, flags=re.I)

    # If we still have e.g. "spotlights your (applying, ...)" with no noun, prefer "you"
    s = re.sub(
        r"\b(supports|spotlights|puts pressure on)\s+your\b(?=\s*(?:\(|[.,]|$))",
        r"\1 you",
        s,
        flags=re.I,
    )

    # Spacing for True Node
    s = re.sub(r"\bTrueNode\b", "True Node", s)

    return re.sub(r"\s{2,}", " ", s).strip()


def _apply_aspect_smooth(text: str) -> str:
    s = text
    for rx, repl in _ASPECT_SMOOTH:
        s = rx.sub(repl, s)
    s = _post_aspect_cleanups(s)
    return s


# ---------- Evidence helpers ----------

def _strip_skywatch(text: str) -> tuple[str, str]:
    """Return (stripped_text, skywatch_note_once)."""
    if not text:
        return "", ""
    notes = _SKYWATCH.findall(text)
    cleaned = _SKYWATCH.sub("", text).strip()
    return cleaned, " ".join(dict.fromkeys(n.strip() for n in notes))


def _plain_event_sentence(s: str) -> str:
    # remove any embedded skywatch before cleaning
    s, _ = _strip_skywatch(s or "")
    s = de_jargon(s)
    s = _apply_aspect_smooth(s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s[0].upper() + s[1:] if s else s


def _clamp(text: str, n: int = 3) -> str:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    return " ".join(parts[:n])


# ---------- Paragraph assembly ----------

def _compose_paragraph(
    lead: str,
    evidence: Sequence[str] | None,
    closing: str | None,
    *,
    area: str = "general",
    events: List[Mapping[str, Any]] | None = None,
    apply_qa: bool = True,
    clamp_to: int = 3,
) -> str:
    parts: List[str] = []
    if lead:
        normalized = fix_indefinite_articles(_ensure_sentence(lead))
        if normalized:
            parts.append(normalized)
    for sentence in evidence or ():
        normalized = fix_indefinite_articles(_ensure_sentence(sentence))
        if normalized and normalized not in parts:
            parts.append(normalized)
    if closing:
        normalized = fix_indefinite_articles(_ensure_sentence(closing))
        if normalized:
            parts.append(normalized)

    result = _sanitize_spaces(" ".join(parts).strip())

    # Apply phrasebank QA polish and driver microcopy integration (best-effort)
    if apply_qa and result:
        try:
            from api.services.option_b_cleaner.phrasebank_integration import (
                apply_qa_polish,
                inject_driver_microcopy,
            )
            result = apply_qa_polish(result, area=area)
            if events:
                result = inject_driver_microcopy(result, events, max_injections=1)
        except Exception:
            pass

    if clamp_to and clamp_to > 0:
        result = _clamp(result, clamp_to)

    # NEVER let sky-watch leak into sections
    result, _ = _strip_skywatch(result)
    return result


def _event_evidence_sentences(
    event: Mapping[str, Any] | None,
    supporting_event: Mapping[str, Any] | None = None,
    *,
    area: str | None = None,
    seed: int | None = None,
) -> tuple[str, ...]:
    sentences: List[str] = []
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
        base_seed = (seed or 0)
        template = templates[base_seed % len(templates)]
        sentences.append(template.format(primary=_plain_event_sentence(primary), supporting=_plain_event_sentence(supporting)))
    elif primary:
        sentences.append(_plain_event_sentence(primary))
    elif supporting:
        sentences.append(_plain_event_sentence(supporting))

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

    # opener
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
            event=event,
        )

    # evidence
    evidence = list(
        _event_evidence_sentences(
            event,
            supporting_event,
            area=area,
            seed=base_seed + 1,
        )
    )

    # coaching (tone-aware)
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

    # If intensity is high, append a pacing hint (once, tone-aware)
    loud = intensity_from_text(raw, primary_phrase or "", supporting_phrase or "")
    if loud == "high":
        if tone == "challenge":
            evidence.append("Keep margins wide and skip optional commitments.")
        elif tone == "support":
            evidence.append("Let the tailwind help—but keep your pacing humane.")
        else:
            evidence.append("Stay responsive; re-sequence plans if signals shift.")

    # closing
    default_closing = closing_default.format(**tokens)
    closing = clause.strip() if clause else _render_storylet(
        area,
        "closers",
        tone,
        base_seed + 3,
        tokens=tokens,
        default=default_closing,
    )

    # Compose with QA and driver microcopy
    events_list = [event, supporting_event] if event and supporting_event else \
                  [event] if event else \
                  [supporting_event] if supporting_event else None

    return _compose_paragraph(
        opener,
        evidence,
        closing,
        area=area,
        events=events_list,
        apply_qa=True,
        clamp_to=3,
    )


# ---------- Lines & sections ----------

def element_modality_line(sign_a: str, sign_b: str) -> str:
    info_a = SIGN_DETAILS.get(sign_a, ("Cardinal", "Air"))
    info_b = SIGN_DETAILS.get(sign_b or sign_a, info_a)
    qa = ELEMENT_QUALITIES.get(info_a[1], "balance and clarity").lower()
    qb = ELEMENT_QUALITIES.get(info_b[1], "focus and steadiness").lower()
    if sign_a == sign_b:
        return f"{sign_a} keeps things {qa}"
    return f"{sign_a} keeps things {qa}, while {sign_b} adds {qb}"


def build_opening_summary(
    theme: str,
    raw: str,
    signs: Sequence[str],
    profile_name: str = "",
    clause: str | None = None,
) -> str:
    sign_a = signs[0] if signs else "Libra"
    sign_b = signs[1] if len(signs) > 1 else sign_a

    # Strip sky-watch once (append at end)
    theme_clean, skywatch = _strip_skywatch((theme or "") + " " + (raw or ""))
    descriptor = descriptor_from_text(theme_clean, raw, profile_name=profile_name)
    focus = focus_from_text(theme_clean, raw, profile_name=profile_name)
    article = "an" if descriptor and descriptor[0].lower() in "aeiou" else "a"

    backdrop = element_modality_line(sign_a, sign_b)
    closing = (clause.strip() if clause else "Keep momentum pointed toward meaningful moves.") or ""
    closing = closing.replace("quiet clarity", "calm focus").rstrip(".")
    closing_frag = (closing[0].lower() + closing[1:]) if closing else ""

    summary = f"You ride {article} {descriptor} wave toward today's {focus} as {backdrop}"
    if closing_frag:
        summary += f", and {closing_frag}"
    summary = summary.rstrip(", ") + "."

    out = fix_indefinite_articles(_sanitize_spaces(summary))
    if skywatch:
        out += f" ({skywatch})"
    return out


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
    final = _polish_sentence(
        sentence or "You set the tone by taking one intentional pause before leaning into steady momentum today."
    )
    final, _ = _strip_skywatch(final)  # keep sky-watch out of sections
    return final


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
        opener_default="You turn {descriptor} focus into deliberate progress at work.",
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
    # keep sky-watch only in one-liner + summary
    combined, sky = _strip_skywatch((raw or "") + " " + (theme or ""))
    descriptor = descriptor_from_text(combined, theme, default="steady", profile_name=profile_name)
    focus = focus_from_text(combined, theme, default="momentum", profile_name=profile_name)
    line = fix_indefinite_articles(_sanitize_spaces(f"Make {descriptor} moves and keep your {focus} in view."))
    if sky:
        line += f" ({sky})"
    return line


# ---------- Surface polishers ----------

def polished_text(raw: str, profile_name: str) -> str:
    """
    Return the first polished sentence from an LLM/raw string:
    - de-jargon + second-person POV
    - normalize spacing/punctuation
    - ensure terminal punctuation
    """
    cleaned = _clean_text(raw, profile_name)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if not sentences:
        return ""
    first = sentences[0]
    return _ensure_sentence(first)


# ---------- Optional high-level aggregator (non-breaking addition) ----------

def build_daily_narrative(
    *,
    theme: str,
    raw: str,
    signs: Sequence[str],
    profile_name: str = "",
    tone_hints: Mapping[str, str] | None = None,
    events: Mapping[str, Mapping[str, Any] | None] | None = None,
) -> Mapping[str, str]:
    """
    Convenience aggregator that returns a dict with all major sections rendered.
    keys: summary, morning, career, love, health, finance, one_liner
    """
    tone_hints = tone_hints or {}
    events = events or {}
    return {
        "summary": build_opening_summary(theme, raw, signs, profile_name),
        "morning": build_morning_paragraph(raw, profile_name, theme, events.get("morning")),
        "career": build_career_paragraph(
            raw,
            profile_name=profile_name,
            tone_hint=tone_hints.get("career"),
            clause=None,
            event=events.get("career"),
            supporting_event=events.get("career_support"),
        ),
        "love": build_love_paragraph(
            raw,
            profile_name=profile_name,
            tone_hint=tone_hints.get("love"),
            clause=None,
            event=events.get("love"),
            supporting_event=events.get("love_support"),
        ),
        "health": build_health_paragraph(
            raw,
            theme,
            profile_name=profile_name,
            tone_hint=tone_hints.get("health"),
            clause=None,
            event=events.get("health"),
            supporting_event=events.get("health_support"),
        ),
        "finance": build_finance_paragraph(
            raw,
            theme,
            profile_name=profile_name,
            tone_hint=tone_hints.get("finance"),
            clause=None,
            event=events.get("finance"),
            supporting_event=events.get("finance_support"),
        ),
        "one_liner": build_one_line_summary(raw, theme, profile_name),
    }
