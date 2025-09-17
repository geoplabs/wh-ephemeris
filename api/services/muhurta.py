"""Utility helpers for Rahu Kalam and Hora calculations.

The real Panchang implementation can replace these deterministic helpers
with precise astronomical calculations. For development the routines
below derive values from the provided sunrise and sunset timestamps.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List
WEEKDAY_RULERS = {
    "Sunday": "Sun",
    "Monday": "Moon",
    "Tuesday": "Mars",
    "Wednesday": "Mercury",
    "Thursday": "Jupiter",
    "Friday": "Venus",
    "Saturday": "Saturn",
}

# Rahu, Gulika and Yamaganda segment indices (1-based) per weekday.
RAHU_INDEX = {
    "Monday": 2,
    "Tuesday": 7,
    "Wednesday": 5,
    "Thursday": 6,
    "Friday": 4,
    "Saturday": 3,
    "Sunday": 8,
}

GULIKA_INDEX = {
    "Monday": 4,
    "Tuesday": 5,
    "Wednesday": 3,
    "Thursday": 2,
    "Friday": 1,
    "Saturday": 7,
    "Sunday": 6,
}

YAMAGANDA_INDEX = {
    "Monday": 5,
    "Tuesday": 3,
    "Wednesday": 2,
    "Thursday": 1,
    "Friday": 6,
    "Saturday": 4,
    "Sunday": 7,
}

HORA_LORDS = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]


def _segment(start: datetime, duration: timedelta, index: int) -> tuple[datetime, datetime]:
    """Return the ``index`` (1-based) segment within a day divided into eight parts."""

    seg = duration / 8
    seg_start = start + (index - 1) * seg
    return seg_start, seg_start + seg


def compute_muhurta_blocks(sunrise: datetime, sunset: datetime, weekday: str) -> Dict[str, tuple[datetime, datetime]]:
    day_length = sunset - sunrise
    rahu = _segment(sunrise, day_length, RAHU_INDEX[weekday])
    gulika = _segment(sunrise, day_length, GULIKA_INDEX[weekday])
    yamaganda = _segment(sunrise, day_length, YAMAGANDA_INDEX[weekday])

    # Abhijit muhurta is centred on solar noon with width day_length/15
    solar_noon = sunrise + day_length / 2
    width = day_length / 15
    abhijit = (solar_noon - width / 2, solar_noon + width / 2)

    return {
        "rahu_kal": rahu,
        "gulika_kal": gulika,
        "yamaganda": yamaganda,
        "abhijit": abhijit,
    }


def compute_horas(sunrise: datetime, sunset: datetime, next_sunrise: datetime, weekday: str) -> List[tuple[datetime, datetime, str]]:
    """Return a list of 24 hora spans starting from sunrise."""

    day_length = sunset - sunrise
    night_length = next_sunrise - sunset
    day_seg = day_length / 12
    night_seg = night_length / 12

    ruler = WEEKDAY_RULERS[weekday]
    start_offset = HORA_LORDS.index(ruler)
    order = HORA_LORDS[start_offset:] + HORA_LORDS[:start_offset]

    horas: List[tuple[datetime, datetime, str]] = []
    current = sunrise
    idx = 0
    for _ in range(12):
        lord = order[idx % len(order)]
        span_end = current + day_seg
        horas.append((current, span_end, lord))
        current = span_end
        idx += 1

    for _ in range(12):
        lord = order[idx % len(order)]
        span_end = current + night_seg
        horas.append((current, span_end, lord))
        current = span_end
        idx += 1

    return horas

