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
