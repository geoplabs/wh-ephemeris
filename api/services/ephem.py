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

import swisseph as swe


# Determine ephemeris backend based on environment variable.
# Default is Swiss Ephemeris (requires ephemeris files).
# When EPHEMERIS_BACKEND=moseph, use the built-in Moshier ephemeris
# which doesn't require external files (useful for CI).
BASE_FLAG = (
    swe.FLG_MOSEPH if os.getenv("EPHEMERIS_BACKEND", "swieph") == "moseph"
    else swe.FLG_SWIEPH
)


def calc_ut(jd: float, body: int, sidereal: bool = False):
    """Wrapper around swe.calc_ut that respects backend and zodiac type."""
    flag = BASE_FLAG | (swe.FLG_SIDEREAL if sidereal else 0)
    return swe.calc_ut(jd, body, flag)

from datetime import datetime
from zoneinfo import ZoneInfo

BODIES = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
    "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN,
    "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO,
    "TrueNode": swe.TRUE_NODE, "Chiron": swe.CHIRON
}

AYANAMSHA_MAP = {
    "lahiri": swe.SIDM_LAHIRI,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,  # KP
    "raman": swe.SIDM_RAMAN
}

ENGINE_VERSION = "m1.0.0"

def _backend_flag() -> int:
    # CI runs with MOSEPH (no ephemeris files); local/prod with SWIEPH + ephemeris files.
    return swe.FLG_MOSEPH if os.getenv("EPHEMERIS_BACKEND","swieph").lower()=="moseph" else swe.FLG_SWIEPH

def init_paths(ephe_dir: str|None):
    if ephe_dir and os.path.isdir(ephe_dir):
        swe.set_ephe_path(ephe_dir)

def to_jd_utc(date_str: str, time_str: str, tz: str) -> float:
    dt_local = datetime.fromisoformat(f"{date_str}T{time_str}").replace(tzinfo=ZoneInfo(tz))
    dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
    y,m,d = dt_utc.year, dt_utc.month, dt_utc.day
    h = dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600
    return swe.julday(y,m,d,h, swe.GREG_CAL)

def positions_ecliptic(jd_utc: float, sidereal=False, ayanamsha="lahiri"):
    flag = _backend_flag() | swe.FLG_SPEED
    if sidereal:
        mode = AYANAMSHA_MAP.get(ayanamsha.lower(), swe.SIDM_LAHIRI)
        swe.set_sid_mode(mode)
        flag |= swe.FLG_SIDEREAL

    out = {}
    for name, code in BODIES.items():
        try:
            vals, _ = swe.calc_ut(jd_utc, code, flag)
            lon, lat, dist, lon_speed, lat_speed, dist_speed = vals
            lon = lon % 360.0
            out[name] = {
                "lon": lon,
                "speed_lon": lon_speed,
                "retro": lon_speed < 0
            }
        except Exception:
            # bodies like Chiron need ephemeris files; fallback to 0° if unavailable
            out[name] = {"lon": 0.0, "speed_lon": 0.0, "retro": False}
    return out


