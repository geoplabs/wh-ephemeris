"""Chandrabalam and Tarabalam helpers for extended Panchang."""

from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from .panchang_algos import NAKSHATRA_NAMES


RASHI_EN = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


def chandrabalam_lists(moon_rashi: str) -> Tuple[List[str], List[str]]:
    try:
        idx = RASHI_EN.index(moon_rashi)
    except ValueError:
        return [], []

    good = [RASHI_EN[idx], RASHI_EN[(idx + 4) % 12], RASHI_EN[(idx + 8) % 12]]
    bad = [RASHI_EN[(idx + 3) % 12], RASHI_EN[(idx + 7) % 12], RASHI_EN[(idx + 11) % 12]]
    return good, bad


def tarabalam_lists(nak_number: int) -> Tuple[List[str], List[str]]:
    index = (nak_number - 1) % len(NAKSHATRA_NAMES)
    good = [
        NAKSHATRA_NAMES[index],
        NAKSHATRA_NAMES[(index + 3) % 27],
        NAKSHATRA_NAMES[(index + 6) % 27],
    ]
    bad = [
        NAKSHATRA_NAMES[(index + 1) % 27],
        NAKSHATRA_NAMES[(index + 2) % 27],
        NAKSHATRA_NAMES[(index + 7) % 27],
    ]
    return good, bad


def build_balam(moon_rashi: str, nak_number: int, until_local: datetime) -> dict:
    good_c, bad_c = chandrabalam_lists(moon_rashi)
    good_t, bad_t = tarabalam_lists(nak_number)
    return {
        "chandrabalam_good": good_c,
        "chandrabalam_bad": bad_c,
        "tarabalam_good": good_t,
        "tarabalam_bad": bad_t,
        "valid_until_ts": until_local.isoformat(),
    }
