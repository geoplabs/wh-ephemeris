"""Rules of residence (Nivas) and Shool helpers."""

from __future__ import annotations

from typing import Dict


PLANET_BY_WEEKDAY = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
]

DIRECTION_BY_WEEKDAY = [
    "East",
    "West",
    "North",
    "South",
    "North-East",
    "South-East",
    "South-West",
]

CHANDRA_VASA = [
    "East",
    "South",
    "West",
    "North",
    "East",
    "South",
    "West",
]

RAHU_VASA = [
    "South",
    "South-West",
    "West",
    "North-West",
    "North",
    "South",
    "West",
]

PANCHAKA_GROUPS = ["Raja", "Chora", "Roga", "Agni", "Mrityu"]


def homahuti(weekday: int) -> str:
    return PLANET_BY_WEEKDAY[weekday % 7]


def agnivasa(tithi_number: int) -> str:
    return "Prithvi" if tithi_number % 2 else "Akasha"


def shivasa(weekday: int, tithi_number: int) -> str:
    if weekday % 2 == 0:
        return "Smashana"
    return "Mandira" if tithi_number % 2 else "Grama"


def disha_shool(weekday: int) -> str:
    return DIRECTION_BY_WEEKDAY[weekday % len(DIRECTION_BY_WEEKDAY)]


def nakshatra_shool(nak_number: int) -> str:
    directions = ["East", "South", "West", "North"]
    return directions[(nak_number - 1) % 4]


def chandra_vasa(weekday: int) -> str:
    return CHANDRA_VASA[weekday % len(CHANDRA_VASA)]


def rahu_vasa(weekday: int) -> str:
    return RAHU_VASA[weekday % len(RAHU_VASA)]


def kumbha_chakra(nak_number: int) -> Dict[str, str]:
    segment = PANCHAKA_GROUPS[(nak_number - 1) % len(PANCHAKA_GROUPS)]
    return {"segment": segment, "note": "Indicative Kumbha Chakra grouping"}


def build_nivas_and_shool(weekday: int, tithi_number: int, nak_number: int) -> Dict[str, object]:
    return {
        "homahuti": homahuti(weekday),
        "agnivasa": agnivasa(tithi_number),
        "shivasa": shivasa(weekday, tithi_number),
        "disha_shool": disha_shool(weekday),
        "nakshatra_shool": nakshatra_shool(nak_number),
        "chandra_vasa": chandra_vasa(weekday),
        "rahu_vasa": rahu_vasa(weekday),
        "kumbha_chakra": kumbha_chakra(nak_number),
    }
