"""Helpers for extended Ritu and Dinmana/Ratrimana calculations."""

from __future__ import annotations

from datetime import datetime


RITU_NAMES = [
    "Vasanta",
    "Grishma",
    "Varsha",
    "Sharad",
    "Hemanta",
    "Shishira",
]


def ritu_drik(sidereal_sun_long: float) -> str:
    index = int((sidereal_sun_long % 360.0) // 60.0)
    return RITU_NAMES[index]


def ritu_vedic(sidereal_sun_long: float) -> str:
    index = int((sidereal_sun_long % 360.0) // 60.0)
    return RITU_NAMES[index]


def dinmana_ratrimana(
    sunrise_local: datetime,
    sunset_local: datetime,
    next_sunrise_local: datetime,
) -> tuple[str, str]:
    day_len = sunset_local - sunrise_local
    night_len = next_sunrise_local - sunset_local
    return (str(day_len).split(".")[0], str(night_len).split(".")[0])


def build_ritu_extended(
    convention: str,
    sidereal_sun_long: float,
    sunrise_local: datetime,
    sunset_local: datetime,
    next_sunrise_local: datetime,
) -> dict:
    drik = ritu_drik(sidereal_sun_long)
    vedic = ritu_vedic(sidereal_sun_long)
    din, rat = dinmana_ratrimana(sunrise_local, sunset_local, next_sunrise_local)
    return {
        "drik_ritu": drik,
        "vedic_ritu": vedic,
        "convention": convention,
        "dinmana": din,
        "ratrimana": rat,
    }
