"""Simplified Panchang helper algorithms.

These utilities provide deterministic but lightweight calculations that
approximate the expected Panchang segments for development and testing
purposes. The real production implementation can replace these helpers
with precise Swiss Ephemeris driven logic without impacting the calling
code.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple

from zoneinfo import ZoneInfo

TITHI_NAMES = [
    "Shukla Pratipada",
    "Shukla Dwitiya",
    "Shukla Tritiya",
    "Shukla Chaturthi",
    "Shukla Panchami",
    "Shukla Shashthi",
    "Shukla Saptami",
    "Shukla Ashtami",
    "Shukla Navami",
    "Shukla Dashami",
    "Shukla Ekadashi",
    "Shukla Dwadashi",
    "Shukla Trayodashi",
    "Shukla Chaturdashi",
    "Purnima",
    "Krishna Pratipada",
    "Krishna Dwitiya",
    "Krishna Tritiya",
    "Krishna Chaturthi",
    "Krishna Panchami",
    "Krishna Shashthi",
    "Krishna Saptami",
    "Krishna Ashtami",
    "Krishna Navami",
    "Krishna Dashami",
    "Krishna Ekadashi",
    "Krishna Dwadashi",
    "Krishna Trayodashi",
    "Krishna Chaturdashi",
    "Amavasya",
]

NAKSHATRA_NAMES = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

YOGA_NAMES = [
    "Vishkambha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shoola",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyan",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
]

KARANA_SEQUENCE = [
    "Bava",
    "Balava",
    "Kaulava",
    "Taitila",
    "Garaja",
    "Vanija",
    "Vishti (Bhadra)",
]

FIXED_KARANAS = [
    "Shakuni",
    "Chatushpada",
    "Naga",
    "Kimstughna",
]

MASA_AMANTA = [
    "Chaitra",
    "Vaishakha",
    "Jyeshtha",
    "Ashadha",
    "Shravana",
    "Bhadrapada",
    "Ashwin",
    "Kartika",
    "Margashirsha",
    "Pausha",
    "Magha",
    "Phalguna",
]


def _format_iso(dt: datetime) -> str:
    return dt.isoformat()


def compute_tithi(date: datetime, sunrise: datetime) -> Tuple[int, str, datetime, datetime]:
    ordinal = date.toordinal()
    number = (ordinal % 30) + 1
    name = TITHI_NAMES[number - 1]
    # Anchor start roughly three hours before sunrise to mimic overnight spans.
    start = sunrise - timedelta(hours=3)
    end = start + timedelta(hours=24)
    return number, name, start, end


def compute_nakshatra(date: datetime, sunrise: datetime) -> Tuple[int, str, int, datetime, datetime]:
    ordinal = date.toordinal()
    number = (ordinal % 27) + 1
    name = NAKSHATRA_NAMES[number - 1]
    pada = ((ordinal // 7) % 4) + 1
    start = sunrise - timedelta(hours=6)
    end = start + timedelta(hours=24)
    return number, name, pada, start, end


def compute_yoga(date: datetime, sunrise: datetime) -> Tuple[int, str, datetime, datetime]:
    ordinal = date.toordinal()
    number = (ordinal % len(YOGA_NAMES)) + 1
    name = YOGA_NAMES[number - 1]
    start = sunrise - timedelta(hours=2)
    end = start + timedelta(hours=26)
    return number, name, start, end


def compute_karana(date: datetime, sunrise: datetime) -> Tuple[int, str, datetime, datetime]:
    ordinal = date.toordinal()
    half_index = (ordinal * 2) % 56
    if half_index >= 50:
        offset = (half_index - 50) % len(FIXED_KARANAS)
        name = FIXED_KARANAS[offset]
        index = len(KARANA_SEQUENCE) + offset
    else:
        index = half_index % len(KARANA_SEQUENCE)
        name = KARANA_SEQUENCE[index]
    start = sunrise + timedelta(hours=9)
    end = start + timedelta(hours=6)
    return index, name, start, end


def compute_masa(date: datetime) -> Tuple[int, str, int, str]:
    month_idx = date.month - 1
    amanta = MASA_AMANTA[month_idx % 12]
    purnimanta = MASA_AMANTA[(month_idx + 1) % 12]
    return month_idx % 12, amanta, (month_idx + 1) % 12, purnimanta


def compute_lunar_day(date: datetime) -> Tuple[int, str]:
    number = (date.toordinal() % 30) + 1
    paksha = "shukla" if number <= 15 else "krishna"
    return number, paksha


def compute_moon_events(date: datetime, tz: ZoneInfo) -> Tuple[str | None, str | None]:
    base = datetime(date.year, date.month, date.day, tzinfo=tz)
    moonrise = base + timedelta(hours=21)
    moonset = base + timedelta(hours=9)
    return _format_iso(moonrise), _format_iso(moonset)

