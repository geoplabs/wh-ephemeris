"""Helpers for Panchaka Rahita and Udaya Lagna spans."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List


PANCHAKA_NAMES = ["Raja", "Chora", "Roga", "Agni", "Mrityu"]
ZODIAC_EN = [
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


def panchaka_slots(
    sunrise_local: datetime,
    sunset_local: datetime,
    nak_number: int,
    weekday: int,
) -> List[Dict[str, str]]:
    total = sunset_local - sunrise_local
    segment = total / len(PANCHAKA_NAMES)
    slots: List[Dict[str, str]] = []
    current = sunrise_local
    for name in PANCHAKA_NAMES:
        end = current + segment
        slots.append({"name": name, "start_ts": current.isoformat(), "end_ts": end.isoformat()})
        current = end
    return slots


def udaya_lagna_slots(
    lat: float,
    lon: float,
    tzinfo,
    sunrise_local: datetime,
) -> List[Dict[str, str]]:
    span = timedelta(hours=12)
    segment = span / len(ZODIAC_EN)
    slots: List[Dict[str, str]] = []
    for idx in range(len(ZODIAC_EN)):
        start = sunrise_local + segment * idx
        end = start + segment
        if start >= sunrise_local + span:
            break
        slots.append(
            {
                "lagna": ZODIAC_EN[idx % len(ZODIAC_EN)],
                "start_ts": start.isoformat(),
                "end_ts": end.isoformat(),
            }
        )
    return slots


def build_panchaka_and_lagna(
    sunrise_local: datetime,
    sunset_local: datetime,
    nak_number: int,
    weekday: int,
    lat: float,
    lon: float,
    tzinfo,
) -> Dict[str, List[Dict[str, str]]]:
    return {
        "panchaka_rahita": panchaka_slots(sunrise_local, sunset_local, nak_number, weekday),
        "udaya_lagna": udaya_lagna_slots(lat, lon, tzinfo, sunrise_local),
    }
