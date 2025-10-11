"""Simplified Panchang helper algorithms.

These utilities provide deterministic but lightweight calculations that
approximate the expected Panchang segments for development and testing
purposes. The real production implementation can replace these helpers
with precise Swiss Ephemeris driven logic without impacting the calling
code.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Tuple, List, Dict

import math
import os

from .ephem import positions_ecliptic

try:
    import swisseph as swe
except ImportError:  # pragma: no cover - library injected during runtime
    swe = None  # type: ignore

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

MOBILE_KARANAS = [
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

KARANA_NAME_TO_INDEX = {
    name: idx for idx, name in enumerate(MOBILE_KARANAS + FIXED_KARANAS)
}

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

NAKSHATRA_SPAN = 360.0 / 27.0
PADA_SPAN = NAKSHATRA_SPAN / 4.0
YOGA_SPAN = 360.0 / 27.0
KARANA_SPAN = 6.0

RASHI_NAMES = [
    "Mesha",
    "Vrishabha",
    "Mithuna",
    "Karka",
    "Simha",
    "Kanya",
    "Tula",
    "Vrischika",
    "Dhanu",
    "Makara",
    "Kumbha",
    "Meena",
]

EPHEMERIS_FLAG = (
    swe.FLG_MOSEPH
    if os.getenv("EPHEMERIS_BACKEND", "swieph").lower() == "moseph"
    else swe.FLG_SWIEPH
) if swe else 0


# --- K A R A N A ---


def karana_at_delta_deg(delta_deg: float) -> Tuple[int, str]:
    """Resolve the karana index (1-based) and display name for a delta."""

    d = delta_deg % 360.0
    half_tithi_index = int(d // KARANA_SPAN)

    if half_tithi_index == 0:
        return 11, "Kimstughna"
    if half_tithi_index == 57:
        return 8, "Shakuni"
    if half_tithi_index == 58:
        return 9, "Chatushpada"
    if half_tithi_index == 59:
        return 10, "Naga"

    slot = (half_tithi_index - 1) % len(MOBILE_KARANAS)
    return 1 + slot, MOBILE_KARANAS[slot]


def _format_iso(dt: datetime) -> str:
    return dt.isoformat()


def _to_jd(moment: datetime) -> float:
    """Convert a timezone-aware datetime into Julian Day (UT)."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment_utc = moment.astimezone(timezone.utc)
    return moment_utc.timestamp() / 86400.0 + 2440587.5


def _tithi_state(moment: datetime, ayanamsha: str = "lahiri") -> Tuple[int, float]:
    """Return the tithi number and raw longitude difference at a moment."""
    diff = _moon_sun_diff(moment, sidereal=True, ayanamsha=ayanamsha)
    number = int(diff // 12.0) + 1
    return number, diff


def _sun_longitude(
    moment: datetime, sidereal: bool = False, ayanamsha: str = "lahiri"
) -> float:
    jd = _to_jd(moment)
    return positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayanamsha)["Sun"]["lon"]


def _moon_longitude(
    moment: datetime, sidereal: bool = False, ayanamsha: str = "lahiri"
) -> float:
    jd = _to_jd(moment)
    return positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayanamsha)["Moon"]["lon"]


def _yoga_value(moment: datetime, ayanamsha: str = "lahiri") -> float:
    return (
        _sun_longitude(moment, sidereal=True, ayanamsha=ayanamsha) + 
        _moon_longitude(moment, sidereal=True, ayanamsha=ayanamsha)
    ) % 360.0


def _moon_sun_diff(
    moment: datetime, sidereal: bool = False, ayanamsha: str = "lahiri"
) -> float:
    """Return the longitudinal separation between Moon and Sun in degrees."""

    moon_lon = _moon_longitude(moment, sidereal=sidereal, ayanamsha=ayanamsha)
    sun_lon = _sun_longitude(moment, sidereal=sidereal, ayanamsha=ayanamsha)
    return (moon_lon - sun_lon) % 360.0


def _jd_to_datetime(jd: float) -> datetime:
    seconds = (jd - 2440587.5) * 86400.0
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _rise_or_set(
    start_of_day: datetime,
    body: int,
    rsmi: int,
    lat: float,
    lon: float,
    elevation: float = 0.0,
) -> Optional[datetime]:
    if swe is None:
        return None

    jd_start = _to_jd(start_of_day)
    geopos = (lon, lat, elevation)
    try:
        result, times = swe.rise_trans(
            jd_start, body, rsmi | swe.BIT_DISC_CENTER, geopos, 0.0, 0.0, EPHEMERIS_FLAG
        )
    except swe.Error:  # type: ignore[attr-defined]
        return None
    if result < 0 or not times:
        return None
    event_utc = _jd_to_datetime(times[0])
    return event_utc.astimezone(start_of_day.tzinfo or timezone.utc)


def compute_solar_events(
    start_of_day: datetime, lat: float, lon: float, elevation: float = 0.0
) -> Tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
    """Return sunrise, sunset and next day's sunrise for the location."""

    sunrise = _rise_or_set(start_of_day, swe.SUN if swe else 0, swe.CALC_RISE if swe else 0, lat, lon, elevation)
    sunset = _rise_or_set(start_of_day, swe.SUN if swe else 0, swe.CALC_SET if swe else 0, lat, lon, elevation)
    next_start = start_of_day + timedelta(days=1)
    next_sunrise = _rise_or_set(next_start, swe.SUN if swe else 0, swe.CALC_RISE if swe else 0, lat, lon, elevation)
    return sunrise, sunset, next_sunrise


def _unwrap(value: float, reference: float, forward: bool) -> float:
    """Unwrap a longitude measurement relative to a reference value."""
    if forward:
        while value < reference:
            value += 360.0
    else:
        while value > reference:
            value -= 360.0
    return value


def _find_boundary(
    reference_time: datetime,
    reference_value: float,
    target: float,
    forward: bool,
    getter: Callable[[datetime], float],
) -> datetime:
    """Locate the moment when an angular boundary is crossed."""

    unwrapped_target = target
    if forward:
        while unwrapped_target < reference_value:
            unwrapped_target += 360.0
    else:
        while unwrapped_target > reference_value:
            unwrapped_target -= 360.0

    step_hours = 6
    max_hours = 96
    direction = 1 if forward else -1

    candidate_time = reference_time
    candidate_value = reference_value
    hours = step_hours
    found = False
    while hours <= max_hours:
        candidate_time = reference_time + direction * timedelta(hours=hours)
        candidate_value = _unwrap(
            getter(candidate_time), reference_value, forward
        )
        if forward:
            if candidate_value >= unwrapped_target:
                found = True
                break
        else:
            if candidate_value <= unwrapped_target:
                found = True
                break
        hours += step_hours

    if not found:
        candidate_time = reference_time + direction * timedelta(hours=max_hours)
        candidate_value = _unwrap(
            getter(candidate_time), reference_value, forward
        )

    if forward:
        low_time, low_value = reference_time, reference_value
        high_time, high_value = candidate_time, candidate_value
    else:
        low_time, low_value = candidate_time, candidate_value
        high_time, high_value = reference_time, reference_value

    for _ in range(50):
        midpoint = low_time + (high_time - low_time) / 2
        mid_value = _unwrap(getter(midpoint), reference_value, forward)
        if forward:
            if mid_value < unwrapped_target:
                low_time, low_value = midpoint, mid_value
            else:
                high_time, high_value = midpoint, mid_value
        else:
            if mid_value > unwrapped_target:
                high_time, high_value = midpoint, mid_value
            else:
                low_time, low_value = midpoint, mid_value

    return high_time


def compute_tithi(moment: datetime, ayanamsha: str = "lahiri") -> Tuple[int, str, datetime, datetime]:
    number, diff = _tithi_state(moment, ayanamsha=ayanamsha)
    name = TITHI_NAMES[number - 1]

    start_target = (number - 1) * 12.0
    end_target = number * 12.0

    start_time = _find_boundary(moment, diff, start_target, forward=False, getter=lambda dt: _moon_sun_diff(dt, sidereal=True, ayanamsha=ayanamsha))
    end_time = _find_boundary(moment, diff, end_target, forward=True, getter=lambda dt: _moon_sun_diff(dt, sidereal=True, ayanamsha=ayanamsha))

    return number, name, start_time, end_time


def compute_nakshatra(moment: datetime, ayanamsha: str = "lahiri") -> Tuple[int, str, int, datetime, datetime]:
    moon_lon = _moon_longitude(moment, sidereal=True, ayanamsha=ayanamsha)
    number = int(moon_lon // NAKSHATRA_SPAN) + 1
    name = NAKSHATRA_NAMES[(number - 1) % len(NAKSHATRA_NAMES)]
    pada = int((moon_lon % NAKSHATRA_SPAN) // PADA_SPAN) + 1

    start_target = math.floor(moon_lon / NAKSHATRA_SPAN) * NAKSHATRA_SPAN
    end_target = start_target + NAKSHATRA_SPAN

    start_time = _find_boundary(moment, moon_lon, start_target, forward=False, getter=lambda dt: _moon_longitude(dt, sidereal=True, ayanamsha=ayanamsha))
    end_time = _find_boundary(moment, moon_lon, end_target, forward=True, getter=lambda dt: _moon_longitude(dt, sidereal=True, ayanamsha=ayanamsha))

    return number, name, pada, start_time, end_time


def compute_yoga(moment: datetime, ayanamsha: str = "lahiri") -> Tuple[int, str, datetime, datetime]:
    yoga_val = _yoga_value(moment, ayanamsha=ayanamsha)
    number = int(yoga_val // YOGA_SPAN) + 1
    name = YOGA_NAMES[(number - 1) % len(YOGA_NAMES)]

    start_target = math.floor(yoga_val / YOGA_SPAN) * YOGA_SPAN
    end_target = start_target + YOGA_SPAN

    start_time = _find_boundary(moment, yoga_val, start_target, forward=False, getter=lambda dt: _yoga_value(dt, ayanamsha=ayanamsha))
    end_time = _find_boundary(moment, yoga_val, end_target, forward=True, getter=lambda dt: _yoga_value(dt, ayanamsha=ayanamsha))

    return number, name, start_time, end_time


def compute_karana(
    moment: datetime, ayanamsha: str = "lahiri"
) -> Tuple[int, str, datetime, datetime]:
    diff = _moon_sun_diff(moment, sidereal=True, ayanamsha=ayanamsha)
    half_index = int(diff // KARANA_SPAN)
    number, name = karana_at_delta_deg(diff)

    start_target = half_index * KARANA_SPAN
    end_target = ((half_index + 1) * KARANA_SPAN) % 360.0

    getter = lambda dt: _moon_sun_diff(dt, sidereal=True, ayanamsha=ayanamsha)
    start_time = _find_boundary(moment, diff, start_target, forward=False, getter=getter)
    end_time = _find_boundary(moment, diff, end_target, forward=True, getter=getter)

    return number - 1, name, start_time, end_time


def compute_masa(moment: datetime, ayanamsha: str = "lahiri") -> Tuple[int, str, int, str]:
    sun_lon = _sun_longitude(moment, sidereal=True, ayanamsha=ayanamsha) % 360.0
    amanta_index = int(sun_lon // 30.0) % 12
    purnimanta_index = (amanta_index + 1) % 12
    return (
        amanta_index,
        MASA_AMANTA[amanta_index],
        purnimanta_index,
        MASA_AMANTA[purnimanta_index],
    )


def compute_lunar_day(moment: datetime, ayanamsha: str = "lahiri") -> Tuple[int, str]:
    number, _ = _tithi_state(moment, ayanamsha=ayanamsha)
    paksha = "shukla" if number <= 15 else "krishna"
    return number, paksha


def compute_moon_events(
    start_of_day: datetime,
    lat: float,
    lon: float,
    elevation: float = 0.0,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    if swe is None:
        fallback_rise = start_of_day + timedelta(hours=21)
        fallback_set = start_of_day + timedelta(hours=9)
        return fallback_rise, fallback_set

    rise = _rise_or_set(start_of_day, swe.MOON, swe.CALC_RISE, lat, lon, elevation)
    set_ = _rise_or_set(start_of_day, swe.MOON, swe.CALC_SET, lat, lon, elevation)
    return rise, set_


def compute_rashi(moment: datetime, ayanamsha: str = "lahiri") -> Tuple[int, str, int, str]:
    sun_lon = _sun_longitude(moment, sidereal=True, ayanamsha=ayanamsha) % 360.0
    moon_lon = _moon_longitude(moment, sidereal=True, ayanamsha=ayanamsha) % 360.0
    sun_idx = int(sun_lon // 30.0)
    moon_idx = int(moon_lon // 30.0)
    return sun_idx, RASHI_NAMES[sun_idx], moon_idx, RASHI_NAMES[moon_idx]


def _ensure_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def _enumerate_periods(
    start: datetime,
    end: datetime,
    resolver: Callable[[datetime], Dict[str, object]],
) -> List[Dict[str, object]]:
    start = _ensure_aware(start)
    end = _ensure_aware(end)
    if end <= start:
        return []

    periods: List[Dict[str, object]] = []
    epsilon = timedelta(seconds=1)
    current = start
    safety = 0
    while current < end and safety < 500:
        info = resolver(current)
        raw_start = _ensure_aware(info["start"])  # type: ignore[index]
        raw_end = _ensure_aware(info["end"])  # type: ignore[index]
        period_start = max(raw_start, start)
        period_end = min(raw_end, end)

        if period_end <= period_start:
            current = current + epsilon
            safety += 1
            continue

        normalized: Dict[str, object] = {
            key: value
            for key, value in info.items()
            if key not in {"start", "end"}
        }
        normalized["start"] = period_start
        normalized["end"] = period_end
        periods.append(normalized)

        if raw_end >= end:
            break

        current = raw_end + epsilon
        safety += 1

    return periods


def enumerate_tithi_periods(
    start_utc: datetime,
    end_utc: datetime,
    lat: float,
    lon: float,
    ayanamsha: str,
) -> List[Dict[str, object]]:
    del lat, lon  # Not used for tithi calculations

    def _resolve(moment: datetime) -> Dict[str, object]:
        number, name, period_start, period_end = compute_tithi(moment, ayanamsha=ayanamsha)
        return {
            "number": number,
            "name": name,
            "start": period_start,
            "end": period_end,
        }

    return _enumerate_periods(start_utc, end_utc, _resolve)


def enumerate_nakshatra_periods(
    start_utc: datetime,
    end_utc: datetime,
    lat: float,
    lon: float,
    ayanamsha: str,
) -> List[Dict[str, object]]:
    del lat, lon  # Not used for nakshatra calculations

    def _resolve(moment: datetime) -> Dict[str, object]:
        number, name, pada, period_start, period_end = compute_nakshatra(moment, ayanamsha=ayanamsha)
        return {
            "number": number,
            "name": name,
            "pada": pada,
            "start": period_start,
            "end": period_end,
        }

    return _enumerate_periods(start_utc, end_utc, _resolve)


def enumerate_yoga_periods(
    start_utc: datetime,
    end_utc: datetime,
    lat: float,
    lon: float,
    ayanamsha: str,
) -> List[Dict[str, object]]:
    del lat, lon  # Not used for yoga calculations

    def _resolve(moment: datetime) -> Dict[str, object]:
        number, name, period_start, period_end = compute_yoga(moment, ayanamsha=ayanamsha)
        return {
            "number": number,
            "name": name,
            "start": period_start,
            "end": period_end,
        }

    return _enumerate_periods(start_utc, end_utc, _resolve)


def enumerate_karana_periods(
    start_utc: datetime,
    end_utc: datetime,
    lat: float,
    lon: float,
    ayanamsha: str,
) -> List[Dict[str, object]]:
    del lat, lon

    if end_utc <= start_utc:
        return []

    ayan = (ayanamsha or "lahiri").lower()
    getter = lambda dt: _moon_sun_diff(dt, sidereal=True, ayanamsha=ayan)

    periods: List[Dict[str, object]] = []
    current_start = start_utc
    # probe slightly ahead to determine the active half-tithi index
    probe_delta = getter(current_start)
    half_index = int(probe_delta // KARANA_SPAN)

    for _ in range(20):
        mid_deg = ((half_index + 0.5) * KARANA_SPAN) % 360.0
        number, name = karana_at_delta_deg(mid_deg)

        target = ((half_index + 1) * KARANA_SPAN) % 360.0
        boundary = _find_boundary(
            current_start,
            probe_delta,
            target,
            forward=True,
            getter=getter,
        )

        if boundary <= current_start:
            boundary = current_start + timedelta(seconds=1)

        segment_end = min(boundary, end_utc)
        periods.append(
            {
                "number": number,
                "name": name,
                "start": current_start,
                "end": segment_end,
            }
        )

        if segment_end >= end_utc:
            break

        # advance to next span and evaluate the new elongation
        current_start = segment_end
        if current_start >= end_utc:
            break
        probe_delta = getter(current_start)
        half_index = int(probe_delta // KARANA_SPAN)

    if periods and periods[-1]["end"] < end_utc:
        # extend last segment to cover the tail using the current label
        last = periods[-1]
        periods.append(
            {
                "number": last["number"],
                "name": last["name"],
                "start": last["end"],
                "end": end_utc,
            }
        )

    return periods

