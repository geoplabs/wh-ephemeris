"""Helpers for normalising Panchang place inputs."""

import os
from typing import Any, Dict, Optional, Tuple

try:  # pragma: no cover - optional dependency
    from timezonefinder import TimezoneFinder

    _TF = TimezoneFinder()
except Exception:  # pragma: no cover - defensive
    _TF = None


DEF_LAT = float(os.getenv("DEFAULT_PLACE_LAT", "28.6139"))
DEF_LON = float(os.getenv("DEFAULT_PLACE_LON", "77.2090"))
DEF_TZ = os.getenv("DEFAULT_PLACE_TZ", "Asia/Kolkata")
DEF_LBL = os.getenv("DEFAULT_PLACE_LABEL", "New Delhi, India")


def clamp_lat_lon(lat: float, lon: float) -> Tuple[float, float]:
    """Clamp latitude/longitude to safe ranges."""

    lat = max(min(lat, 89.9), -89.9)
    lon = ((lon + 180.0) % 360.0) - 180.0  # wrap to [-180, 180)
    return lat, lon


def infer_tz(lat: float, lon: float) -> Optional[str]:
    """Infer timezone name for a coordinate pair."""

    if _TF is None:
        return None
    try:
        return _TF.timezone_at(lng=lon, lat=lat)
    except Exception:  # pragma: no cover - defensive
        return None


def normalize_place(place: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Normalise place payload and capture metadata flags."""

    flags: Dict[str, Any] = {
        "place_defaults_used": False,
        "tz_inferred": False,
        "default_reason": None,
    }

    if not place:
        flags.update({"place_defaults_used": True, "default_reason": "missing_place"})
        return {"lat": DEF_LAT, "lon": DEF_LON, "tz": DEF_TZ, "query": DEF_LBL}, flags

    lat = place.get("lat")
    lon = place.get("lon")
    tz = place.get("tz")
    lbl = place.get("query") or place.get("label") or None
    elevation = place.get("elevation")

    if lat is None or lon is None:
        flags.update({"place_defaults_used": True, "default_reason": "missing_latlon"})
        eff_lat, eff_lon = DEF_LAT, DEF_LON
        eff_tz = tz or DEF_TZ
        eff_lbl = lbl or DEF_LBL
        eff_place = {
            "lat": eff_lat,
            "lon": eff_lon,
            "tz": eff_tz,
            "query": eff_lbl,
        }
        if elevation is not None:
            eff_place["elevation"] = elevation
        return eff_place, flags

    lat, lon = clamp_lat_lon(float(lat), float(lon))

    if not tz:
        tz_guess = infer_tz(lat, lon)
        if tz_guess:
            tz = tz_guess
            flags["tz_inferred"] = True
            flags["default_reason"] = "missing_tz"
        else:
            tz = DEF_TZ
            flags.update({"tz_inferred": False, "default_reason": "missing_tz"})

    eff_lbl = lbl or f"{lat:.4f}, {lon:.4f}"
    eff_place = {"lat": lat, "lon": lon, "tz": tz, "query": eff_lbl}
    if elevation is not None:
        eff_place["elevation"] = elevation
    return eff_place, flags
