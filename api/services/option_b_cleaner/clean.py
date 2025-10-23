import re
from textwrap import shorten

_ORB = re.compile(r"\b\d+(\.\d+)?°\b")
_APPLYING_SEP = re.compile(r"\b(Applying|Separating)\b[^.]*\.?")
_SIGN_IN = re.compile(r";?\s*[A-Z][a-z]+ in [A-Z][a-z]+")
_ASPECT_WORDS = re.compile(r"\b(conjunction|sextile|square|trine|opposition)\b", re.I)
_ELLIPSES = re.compile(r"\s*…\s*$")


def de_jargon(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = _APPLYING_SEP.sub("", s)
    s = _ORB.sub("", s)
    s = _SIGN_IN.sub("", s)
    s = _ASPECT_WORDS.sub("", s)
    s = _ELLIPSES.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
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


def imperative_bullet(s: str) -> str:
    s = de_jargon(s)
    s = re.sub(r"^(?:Try to|You should|Consider|Aim to)\s+", "", s, flags=re.I)
    if re.match(r"^[A-Za-z]{1,12}\b", s) and not re.match(
        r"^(Take|Choose|Focus|Lead|Review|Avoid|Set|Plan|Speak|Express)\b",
        s,
    ):
        s = "Focus on " + s[0].lower() + s[1:]
    s = s.rstrip(".")
    return shorten(s, width=88, placeholder="")


def clamp_sentences(paragraph: str, max_sentences: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    return " ".join(parts[:max_sentences]).strip()
