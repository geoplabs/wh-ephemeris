"""Resolve Panchang labels for a requested locale."""

from __future__ import annotations

from typing import Dict, Tuple

from .panchang_labels import (
    VARA,
    TITHI_EN,
    TITHI_IAST,
    TITHI_DEVA,
    PAKSHA,
    NAK_EN,
    NAK_IAST,
    NAK_DEVA,
    YOGA_EN,
    YOGA_IAST,
    YOGA_DEVA,
    KAR_EN,
    KAR_IAST,
    KAR_DEVA,
    MASA_EN,
    MASA_IAST,
    MASA_DEVA,
    PLANET_EN,
    PLANET_IAST,
    PLANET_DEVA,
)

SUPPORTED_LANGS = {"en", "hi"}
SUPPORTED_SCRIPTS = {"latin", "iast", "deva"}


def _pick(lang: str, script: str, en: str, iast: str, deva: str, hi: str | None = None) -> Tuple[str, Dict[str, str]]:
    """Return the primary label and aliases for the requested locale."""

    if lang == "hi":
        if script == "deva":
            return (hi or deva), {"en": en, "iast": iast, "deva": deva, "hi": hi or deva}
        if script == "iast":
            return iast, {"en": en, "iast": iast, "deva": deva, "hi": hi or deva}
        return (hi or en), {"en": en, "iast": iast, "deva": deva, "hi": hi or deva}
    else:
        if script == "iast":
            return iast, {"en": en, "iast": iast, "deva": deva, "hi": hi or deva}
        if script == "deva":
            return deva, {"en": en, "iast": iast, "deva": deva, "hi": hi or deva}
        return en, {"en": en, "iast": iast, "deva": deva, "hi": hi or deva}


def clamp_lang(lang: str | None) -> str:
    if not lang:
        return "en"
    lang = lang.lower()
    return lang if lang in SUPPORTED_LANGS else "en"


def clamp_script(script: str | None) -> str:
    if not script:
        return "latin"
    script = script.lower()
    return script if script in SUPPORTED_SCRIPTS else "latin"


def vara_label(dow: int, lang: str, script: str) -> Dict[str, Dict[str, str] | str]:
    en = VARA["en"][dow]
    hi = VARA["hi"][dow]
    iast = VARA["iast"][dow]
    deva = VARA["deva"][dow]
    label, aliases = _pick(lang, script, en, iast, deva, hi)
    return {"display_name": label, "aliases": aliases}


def tithi_label(number: int, paksha: str, lang: str, script: str) -> Dict[str, Dict[str, str] | str]:
    idx = number - 1
    en = f"{PAKSHA['en'][paksha]} {TITHI_EN[idx]}"
    hi = f"{PAKSHA['hi'][paksha]} {TITHI_DEVA[idx]}"
    iast = f"{PAKSHA['iast'][paksha]} {TITHI_IAST[idx]}"
    deva = f"{PAKSHA['deva'][paksha]} {TITHI_DEVA[idx]}"
    label, aliases = _pick(lang, script, en, iast, deva, hi)
    return {"display_name": label, "aliases": aliases}


def nak_label(number: int, lang: str, script: str) -> Dict[str, Dict[str, str] | str]:
    i = number - 1
    en, iast, deva = NAK_EN[i], NAK_IAST[i], NAK_DEVA[i]
    label, aliases = _pick(lang, script, en, iast, deva, NAK_DEVA[i])
    return {"display_name": label, "aliases": aliases}


def yoga_label(number: int, lang: str, script: str) -> Dict[str, Dict[str, str] | str]:
    i = number - 1
    en, iast, deva = YOGA_EN[i], YOGA_IAST[i], YOGA_DEVA[i]
    label, aliases = _pick(lang, script, en, iast, deva, YOGA_DEVA[i])
    return {"display_name": label, "aliases": aliases}


def karana_label(name_index: int, lang: str, script: str) -> Dict[str, Dict[str, str] | str]:
    en, iast, deva = KAR_EN[name_index], KAR_IAST[name_index], KAR_DEVA[name_index]
    label, aliases = _pick(lang, script, en, iast, deva, KAR_DEVA[name_index])
    return {"display_name": label, "aliases": aliases}


def masa_label(idx: int, lang: str, script: str) -> Dict[str, Dict[str, str] | str]:
    en, iast, deva = MASA_EN[idx], MASA_IAST[idx], MASA_DEVA[idx]
    label, aliases = _pick(lang, script, en, iast, deva, MASA_DEVA[idx])
    return {"display_name": label, "aliases": aliases}


def planet_label(idx: int, lang: str, script: str) -> Dict[str, Dict[str, str] | str]:
    en, iast, deva = PLANET_EN[idx], PLANET_IAST[idx], PLANET_DEVA[idx]
    label, aliases = _pick(lang, script, en, iast, deva, PLANET_DEVA[idx])
    return {"display_name": label, "aliases": aliases}
