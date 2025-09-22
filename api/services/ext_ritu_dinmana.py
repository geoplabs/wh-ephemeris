"""Helpers for extended Ritu and Dinmana/Ratrimana calculations."""

from __future__ import annotations

from datetime import datetime


# Degrees are zodiacal, 0° = Aries 0.
# Each ritu spans TWO signs (12 signs / 6 ritus).
RITU_BANDS = [
    ("Vasanta", 330, 360),  # Pisces
    ("Vasanta", 0, 30),  # Aries
    ("Grishma", 30, 60),  # Taurus
    ("Grishma", 60, 90),  # Gemini
    ("Varsha", 90, 120),  # Cancer
    ("Varsha", 120, 150),  # Leo
    ("Sharad", 150, 180),  # Virgo
    ("Sharad", 180, 210),  # Libra
    ("Hemanta", 210, 240),  # Scorpio
    ("Hemanta", 240, 270),  # Sagittarius
    ("Shishira", 270, 300),  # Capricorn
    ("Shishira", 300, 330),  # Aquarius
]


def _ritu_from_longitude(lambda_deg: float) -> str:
    L = lambda_deg % 360.0
    for name, a, b in RITU_BANDS:
        if a < b and a <= L < b:
            return name
        if a > b and (L >= a or L < b):
            return name
    return "Vasanta"


def ritu_drik(sun_long_tropical_deg: float) -> str:
    return _ritu_from_longitude(sun_long_tropical_deg)


def ritu_vedic(sun_long_sidereal_deg: float) -> str:
    return _ritu_from_longitude(sun_long_sidereal_deg)


def dinmana_ratrimana(
    sunrise_local: datetime,
    sunset_local: datetime,
    next_sunrise_local: datetime,
) -> tuple[str, str]:
    day_len = sunset_local - sunrise_local
    night_len = next_sunrise_local - sunset_local

    def _fmt(td):
        return str(td).split(".")[0]

    return _fmt(day_len), _fmt(night_len)


def build_ritu_extended(
    convention: str,
    sun_long_tropical: float,
    sun_long_sidereal: float,
    sunrise_local: datetime,
    sunset_local: datetime,
    next_sunrise_local: datetime,
) -> dict:
    drik = ritu_drik(sun_long_tropical)
    vedic = ritu_vedic(sun_long_sidereal)
    din, rat = dinmana_ratrimana(sunrise_local, sunset_local, next_sunrise_local)
    return {
        "drik_ritu": drik,
        "vedic_ritu": vedic,
        "convention": convention,
        "dinmana": din,
        "ratrimana": rat,
    }
