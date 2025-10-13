"""Swiss Ephemeris helpers used by the Panchang and chart orchestrators."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict
from zoneinfo import ZoneInfo

import swisseph as swe


# Engine version for API responses
try:
    ENGINE_VERSION = f"swisseph-{swe.version}"
except AttributeError:
    ENGINE_VERSION = "swisseph-2.10"  # Fallback if version not available

BODIES: Dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "TrueNode": swe.TRUE_NODE,
    "Chiron": swe.CHIRON,
}

AYANAMSHA_MAP = {
    "lahiri": swe.SIDM_LAHIRI,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
    "raman": swe.SIDM_RAMAN,
}


def _backend_flag() -> int:
    """Return the Swiss Ephemeris backend flag based on environment configuration."""

    raw_backend = os.getenv("EPHEMERIS_BACKEND")
    backend = raw_backend.strip().lower() if raw_backend else "swieph"
    return swe.FLG_MOSEPH if backend == "moseph" else swe.FLG_SWIEPH


def init_paths(ephe_dir: str | os.PathLike[str] | None) -> None:
    """Set the Swiss Ephemeris file search path when available."""

    if not ephe_dir:
        return

    path = os.fspath(ephe_dir)
    if os.path.isdir(path):
        swe.set_ephe_path(path)


def to_jd_utc(date_str: str, time_str: str, tz: str) -> float:
    """Convert a local date/time to a Julian day in UTC."""

    dt_local = datetime.fromisoformat(f"{date_str}T{time_str}").replace(tzinfo=ZoneInfo(tz))
    dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
    year, month, day = dt_utc.year, dt_utc.month, dt_utc.day
    hour = (
        dt_utc.hour
        + dt_utc.minute / 60
        + dt_utc.second / 3600
        + dt_utc.microsecond / 3_600_000_000
    )
    return swe.julday(year, month, day, hour, swe.GREG_CAL)


def positions_ecliptic(jd_utc: float, sidereal: bool = False, ayanamsha: str = "lahiri") -> Dict[str, Dict[str, float]]:
    """Return ecliptic longitude and speed for supported bodies."""

    flag = _backend_flag() | swe.FLG_SPEED
    if sidereal:
        mode = AYANAMSHA_MAP.get(ayanamsha.lower(), swe.SIDM_LAHIRI)
        swe.set_sid_mode(mode)
        flag |= swe.FLG_SIDEREAL

    bodies: Dict[str, Dict[str, float]] = {}
    for name, code in BODIES.items():
        try:
            values, _ = swe.calc_ut(jd_utc, code, flag)
            lon, _lat, _dist, lon_speed, _lat_speed, _dist_speed = values
            bodies[name] = {
                "lon": lon % 360.0,
                "speed_lon": lon_speed,
                "retro": lon_speed < 0,
            }
        except Exception:
            # Bodies such as Chiron require the Swiss ephemeris files; if unavailable
            # fall back to a neutral value so the caller can still render a response.
            bodies[name] = {"lon": 0.0, "speed_lon": 0.0, "retro": False}

    return bodies

