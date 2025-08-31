import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict
from hashlib import sha256

EPHEMERIS_BACKEND = os.getenv("EPHEMERIS_BACKEND", "moseph")
BASE_JD = 2451545.0


def to_jd_utc(date: str, time: str, tz: str) -> float:
    """Convert local date/time to Julian Day (UTC)."""
    dt_local = datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=ZoneInfo(tz))
    dt_utc = dt_local.astimezone(timezone.utc)
    return dt_utc.timestamp() / 86400.0 + 2440587.5


def _seed_offset(name: str) -> float:
    h = int(sha256(name.encode()).hexdigest()[:8], 16)
    return (h % 36000) / 100.0


def positions_ecliptic(jd: float, sidereal: bool = False, ayanamsha: str = "lahiri") -> Dict[str, Dict[str, float]]:
    """Return deterministic pseudo ecliptic longitudes for bodies."""
    days = jd - BASE_JD
    speeds = {
        "Sun": 0.9856,
        "Moon": 13.1764,
        "Mercury": 1.2,
        "Venus": 1.18,
        "Mars": 0.524,
        "Jupiter": 0.083,
        "Saturn": 0.033,
        "Uranus": 0.012,
        "Neptune": 0.006,
        "Pluto": 0.004,
        "TrueNode": -0.052,
        "Chiron": 0.017,
    }
    bodies: Dict[str, Dict[str, float]] = {}
    for name, speed in speeds.items():
        lon = (_seed_offset(name) + speed * days) % 360.0
        bodies[name] = {"lon": lon, "speed_lon": speed}
    if sidereal:
        ayan_shift = {"lahiri": 24.0}.get(ayanamsha, 24.0)
        for body in bodies.values():
            body["lon"] = (body["lon"] - ayan_shift) % 360.0
    return bodies
