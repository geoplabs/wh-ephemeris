"""Utility helpers to expose extended muhurtas for the Panchang response."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional


def _slot(kind: str, start: datetime, end: datetime, note: Optional[str] = None) -> Dict[str, str]:
    return {
        "kind": kind,
        "start_ts": start.isoformat(),
        "end_ts": end.isoformat(),
        "note": note,
    }


def brahma_muhurta(next_sunrise_local: datetime) -> Dict[str, str]:
    span = timedelta(minutes=48)
    start = next_sunrise_local - timedelta(minutes=96)
    end = start + span
    return _slot("brahma", start, end)


def pratah_sandhya(sunrise_local: datetime) -> Dict[str, str]:
    span = timedelta(minutes=24)
    start = sunrise_local - span / 2
    end = sunrise_local + span / 2
    return _slot("pratah_sandhya", start, end)


def godhuli(sunset_local: datetime) -> Dict[str, str]:
    span = timedelta(minutes=24)
    start = sunset_local - span / 2
    end = sunset_local + span / 2
    return _slot("godhuli", start, end)


def sayana(sunset_local: datetime) -> Dict[str, str]:
    span = timedelta(minutes=30)
    start = sunset_local + timedelta(minutes=12)
    end = start + span
    return _slot("sayana", start, end)


def nishita(midnight_local: datetime) -> Dict[str, str]:
    span = timedelta(minutes=48)
    start = midnight_local - span / 2
    end = midnight_local + span / 2
    return _slot("nishita", start, end)


def vijaya_muhurta(day_len: timedelta, sunrise_local: datetime) -> Dict[str, str]:
    offset = day_len * (2.0 / 15.0)
    span = timedelta(minutes=48)
    start = sunrise_local + offset
    end = start + span
    return _slot("vijaya", start, end)


def varjyam(nakshatra_periods: List[Dict[str, str]]) -> List[Dict[str, str]]:
    slots: List[Dict[str, str]] = []
    for period in nakshatra_periods[:1]:
        try:
            start = datetime.fromisoformat(period["start_ts"])
            end = datetime.fromisoformat(period["end_ts"])
        except (KeyError, ValueError):
            continue
        if end <= start:
            continue
        mid = start + (end - start) / 2
        span = timedelta(minutes=90)
        slot_start = mid - span / 2
        slot_end = mid + span / 2
        slots.append(_slot("varjyam", slot_start, slot_end))
    return slots


def baana(sun_long: float, time_local: datetime) -> Dict[str, str]:
    types = ["dhana", "mrityu", "roga", "chora"]
    idx = int((sun_long % 360.0) // 90.0)
    label = types[idx]
    end = time_local + timedelta(hours=2)
    return _slot("baana", time_local, end, note=f"{label.title()} Baana")


def durmuhurtam(
    sunrise_local: datetime,
    day_len: timedelta,
    weekday: int,
) -> List[Dict[str, str]]:
    fractions = [(4 / 15, 5 / 15), (9 / 15, 10 / 15)]
    slots: List[Dict[str, str]] = []
    for start_frac, end_frac in fractions:
        start = sunrise_local + day_len * start_frac
        end = sunrise_local + day_len * end_frac
        slots.append(_slot("durmuhurtam", start, end, note=f"Weekday {weekday}"))
    return slots


def build_muhurta_extra(
    sunrise_local: datetime,
    sunset_local: datetime,
    next_sunrise_local: datetime,
    solar_noon_local: datetime,
    weekday: int,
    day_len: timedelta,
    nak_periods: List[Dict[str, str]],
    sun_long: float,
    now_local: datetime,
) -> Dict[str, List[Dict[str, str]]]:
    auspicious = [
        brahma_muhurta(next_sunrise_local),
        pratah_sandhya(sunrise_local),
        godhuli(sunset_local),
        sayana(sunset_local),
        nishita(sunset_local + (next_sunrise_local - sunset_local) / 2),
        vijaya_muhurta(day_len, sunrise_local),
    ]

    inauspicious = []
    inauspicious.extend(varjyam(nak_periods))
    inauspicious.extend(durmuhurtam(sunrise_local, sunset_local - sunrise_local, weekday))
    inauspicious.append(baana(sun_long, now_local))

    return {
        "auspicious_extra": auspicious,
        "inauspicious_extra": inauspicious,
    }
