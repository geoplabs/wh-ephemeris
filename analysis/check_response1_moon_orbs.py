"""Validate lunar aspect orbs reported in Response 1/3 for John (profile user_12345).

This script recomputes the true orbital separation for a subset of the
Moon-to-angle events that were included in the vendor response. The goal is to
double-check whether the quoted orb values (especially for the Moon) are
trustworthy.  Only a few of the most obvious entries are verified here because
several already show meaningful discrepancies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

import swisseph as swe


@dataclass(frozen=True)
class OrbCheck:
    label: str
    timestamp: datetime
    aspect: str
    reported_orb_deg: float


def julday(dt: datetime) -> float:
    """Return a UT Julian day for the supplied aware datetime."""

    if dt.tzinfo is None:
        raise ValueError("Datetimes must be timezone-aware (UTC)")
    dt_utc = dt.astimezone(UTC)
    hour_decimal = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600 + dt_utc.microsecond / 3.6e9
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal)


def ecliptic_longitude(body: int, jd_ut: float) -> float:
    """Return absolute ecliptic longitude in degrees for a Swiss Ephemeris body."""

    return swe.calc_ut(jd_ut, body)[0][0] % 360


ASPECT_ANGLES: Final[dict[str, float]] = {
    "conjunction": 0.0,
    "opposition": 180.0,
    "square": 90.0,
}


def orb_difference(transit_lon: float, natal_lon: float, aspect: str) -> float:
    """Compute the absolute difference between actual and theoretical aspect."""

    desired = ASPECT_ANGLES[aspect]
    diff = (transit_lon - natal_lon) % 360
    if diff > 180:
        diff = 360 - diff
    return abs(diff - desired)


BIRTH_JD_UT = julday(datetime(1990, 5, 15, 9, 0, tzinfo=UTC))
NATAL_ASC = swe.houses(BIRTH_JD_UT, 28.6139, 77.2090)[1][0]
NATAL_MC = swe.houses(BIRTH_JD_UT, 28.6139, 77.2090)[1][1]


EVENTS: Final[list[OrbCheck]] = [
    OrbCheck(
        label="2025-01-05 Moon opposition Ascendant",
        timestamp=datetime(2025, 1, 5, 11, 31, 32, tzinfo=UTC),
        aspect="opposition",
        reported_orb_deg=0.28,
    ),
    OrbCheck(
        label="2025-01-18 Moon square Midheaven",
        timestamp=datetime(2025, 1, 18, 17, 32, 54, tzinfo=UTC),
        aspect="square",
        reported_orb_deg=0.23,
    ),
    OrbCheck(
        label="2025-01-26 Moon square Ascendant",
        timestamp=datetime(2025, 1, 26, 6, 24, 15, tzinfo=UTC),
        aspect="square",
        reported_orb_deg=0.22,
    ),
    OrbCheck(
        label="2025-02-08 Moon conjunction Midheaven",
        timestamp=datetime(2025, 2, 8, 8, 57, 41, tzinfo=UTC),
        aspect="conjunction",
        reported_orb_deg=1.68,
    ),
    OrbCheck(
        label="2025-02-08 Moon square Ascendant",
        timestamp=datetime(2025, 2, 8, 3, 21, 27, tzinfo=UTC),
        aspect="square",
        reported_orb_deg=1.5,
    ),
]


def main() -> None:
    for entry in EVENTS:
        jd_ut = julday(entry.timestamp)
        moon_lon = ecliptic_longitude(swe.MOON, jd_ut)
        if "Asc" in entry.label:
            natal_lon = NATAL_ASC
        else:
            natal_lon = NATAL_MC
        actual_orb = orb_difference(moon_lon, natal_lon, entry.aspect)
        delta = actual_orb - entry.reported_orb_deg
        print(
            f"{entry.label}: reported orb={entry.reported_orb_deg:.2f}°, "
            f"actual={actual_orb:.3f}°, delta={delta:+.3f}°"
        )


if __name__ == "__main__":
    main()
