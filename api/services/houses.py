import swisseph as swe
from .constants import sign_index_from_lon

HOUSE_CODE_MAP = {
    "placidus": "P",
    "koch": "K",
    "whole_sign": "W",
    "regiomontanus": "R",
    "campanus": "C",
}

def houses(jd_utc: float, lat: float, lon: float, system: str = "placidus"):
    hs = HOUSE_CODE_MAP.get(system.lower(), "P")
    cusps, ascmc = swe.houses(jd_utc, lat, lon, hs.encode())
    # cusps: list of 12 values
    return {
        "asc": ascmc[0] % 360.0,
        "mc": ascmc[1] % 360.0,
        "cusps": [cusps[i] % 360.0 for i in range(12)]
    }

def house_of(lon: float, cusps: list[float]) -> int:
    # For quadrant systems: walk cusps; assume cusps sorted by sign order starting at 1
    # Convert longitudes to 0..360, find sector (cusp[i]..cusp[i+1])
    # A simple approach: shift all longitudes so cusp1 becomes 0°
    shift = cusps[0]
    def norm(x): 
        y = (x - shift) % 360.0
        return y
    nlon = norm(lon)
    ncusps = [norm(c) for c in cusps] + [360.0]
    for i in range(12):
        if ncusps[i] <= nlon < ncusps[i+1]:
            return i+1
    return 12

def solar_whole_sign_houses(sun_lon: float) -> list[int]:
    # Return the sign index for houses 1..12 when time unknown:
    # House 1 = Sun's sign; next signs in order
    start = sign_index_from_lon(sun_lon)
    return [(start + i) % 12 for i in range(12)]
