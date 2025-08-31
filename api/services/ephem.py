import os
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

