"""Simplified Panchang helper algorithms.

These utilities provide deterministic but lightweight calculations that
approximate the expected Panchang segments for development and testing
purposes. The real production implementation can replace these helpers
with precise Swiss Ephemeris driven logic without impacting the calling
code.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple

from zoneinfo import ZoneInfo

from .ephem import positions_ecliptic

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


def _to_jd(moment: datetime) -> float:
    """Convert a timezone-aware datetime into Julian Day (UT)."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment_utc = moment.astimezone(timezone.utc)
    return moment_utc.timestamp() / 86400.0 + 2440587.5


def _moon_sun_diff(moment: datetime) -> float:
    """Return the longitudinal separation between Moon and Sun in degrees."""
    jd = _to_jd(moment)
    positions = positions_ecliptic(jd, sidereal=False)
    return (positions["Moon"]["lon"] - positions["Sun"]["lon"]) % 360.0


def _tithi_state(moment: datetime) -> Tuple[int, float]:
    """Return the tithi number and raw longitude difference at a moment."""
    diff = _moon_sun_diff(moment)
    number = int(diff // 12.0) + 1
    return number, diff


def _unwrap(diff: float, reference: float, forward: bool) -> float:
    """Unwrap a longitude difference relative to a reference value."""
    if forward:
        while diff < reference:
            diff += 360.0
    else:
        while diff > reference:
            diff -= 360.0
    return diff


def _find_boundary(
    reference_time: datetime,
    reference_diff: float,
    target: float,
    forward: bool,
) -> datetime:
    """Locate the moment when the tithi boundary is crossed."""

    unwrapped_target = target
    if forward:
        while unwrapped_target < reference_diff:
            unwrapped_target += 360.0
    else:
        while unwrapped_target > reference_diff:
            unwrapped_target -= 360.0

    step_hours = 6
    max_hours = 72
    direction = 1 if forward else -1

    candidate_time = reference_time
    candidate_diff = reference_diff
    hours = step_hours
    found = False
    while hours <= max_hours:
        candidate_time = reference_time + direction * timedelta(hours=hours)
        candidate_diff = _unwrap(
            _moon_sun_diff(candidate_time), reference_diff, forward
        )
        if forward:
            if candidate_diff >= unwrapped_target:
                found = True
                break
        else:
            if candidate_diff <= unwrapped_target:
                found = True
                break
        hours += step_hours

    if not found:
        candidate_time = reference_time + direction * timedelta(hours=max_hours)
        candidate_diff = _unwrap(
            _moon_sun_diff(candidate_time), reference_diff, forward
        )

    if forward:
        low_time, low_diff = reference_time, reference_diff
        high_time, high_diff = candidate_time, candidate_diff
    else:
        low_time, low_diff = candidate_time, candidate_diff
        high_time, high_diff = reference_time, reference_diff

    for _ in range(40):
        midpoint = low_time + (high_time - low_time) / 2
        mid_diff = _unwrap(_moon_sun_diff(midpoint), reference_diff, forward)
        if forward:
            if mid_diff < unwrapped_target:
                low_time, low_diff = midpoint, mid_diff
            else:
                high_time, high_diff = midpoint, mid_diff
        else:
            if mid_diff > unwrapped_target:
                high_time, high_diff = midpoint, mid_diff
            else:
                low_time, low_diff = midpoint, mid_diff

    return high_time


def compute_tithi(date: datetime, sunrise: datetime) -> Tuple[int, str, datetime, datetime]:
    number, diff = _tithi_state(sunrise)
    name = TITHI_NAMES[number - 1]

    start_target = (number - 1) * 12.0
    end_target = number * 12.0

    start_time = _find_boundary(sunrise, diff, start_target, forward=False)
    end_time = _find_boundary(sunrise, diff, end_target, forward=True)

    return number, name, start_time, end_time


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


def compute_lunar_day(moment: datetime) -> Tuple[int, str]:
    number, _ = _tithi_state(moment)
    paksha = "shukla" if number <= 15 else "krishna"
    return number, paksha


def compute_moon_events(date: datetime, tz: ZoneInfo) -> Tuple[str | None, str | None]:
    base = datetime(date.year, date.month, date.day, tzinfo=tz)
    moonrise = base + timedelta(hours=21)
    moonset = base + timedelta(hours=9)
    return _format_iso(moonrise), _format_iso(moonset)

