from typing import Dict, Any, List
import math
from . import ephem, aspects as aspects_svc, houses as houses_svc
from .constants import sign_name_from_lon

ASPECT_AFFECTION = {
    "conjunction": 3,
    "trine": 2,
    "sextile": 1,
    "square": -2,
    "opposition": -2,
}

# FIX: Symmetric pair weights (order doesn't matter)
PAIR_WEIGHTS = {
    ("Sun", "Sun"): 2,
    ("Sun", "Moon"): 3,
    ("Moon", "Sun"): 3,  # Symmetric
    ("Moon", "Moon"): 3,
    ("Venus", "Mars"): 3,
    ("Mars", "Venus"): 3,  # Symmetric
    ("Venus", "Venus"): 2,
    ("Mars", "Mars"): 2,
}


def angle_diff(lon1: float, lon2: float) -> float:
    """
    Public helper: calculate shortest arc between two ecliptic longitudes.
    FIX: Expose as public function instead of using private aspects_svc._angle_diff
    """
    diff = abs(lon1 - lon2)
    if diff > 180:
        diff = 360 - diff
    return diff


def circular_midpoint(a: float, b: float) -> float:
    """
    FIX: Circular mean for zodiac positions (handles 0° Aries wrap correctly).
    Example: 350° and 10° should midpoint to ~0°, not 180°.
    """
    a_r = math.radians(a)
    b_r = math.radians(b)
    x = math.cos(a_r) + math.cos(b_r)
    y = math.sin(a_r) + math.sin(b_r)
    ang = math.degrees(math.atan2(y, x)) % 360.0
    return ang


def _natal_positions(chart_input: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    sidereal = chart_input["system"] == "vedic"
    ayan = (
        (chart_input.get("options") or {}).get("ayanamsha", "lahiri") if sidereal else None
    )
    jd = ephem.to_jd_utc(chart_input["date"], chart_input["time"], chart_input["place"]["tz"])
    return ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayan)


def synastry(person_a: Dict[str, Any], person_b: Dict[str, Any], aspect_types, orb_deg: float) -> List[Dict[str, Any]]:
    """
    Calculate synastry aspects between two natal charts.
    FIX: Uses public angle_diff() and symmetric PAIR_WEIGHTS.
    """
    A = _natal_positions(person_a)
    B = _natal_positions(person_b)
    res = []
    for a_name, a_pos in A.items():
        for b_name, b_pos in B.items():
            d = angle_diff(a_pos["lon"], b_pos["lon"])  # FIX: Use public function
            for t, exact in aspects_svc.MAJOR.items():
                if t not in aspect_types:
                    continue
                if abs(d - exact) <= orb_deg:
                    orb = round(abs(d - exact), 2)
                    base = ASPECT_AFFECTION.get(t, 0)
                    pair_boost = PAIR_WEIGHTS.get((a_name, b_name), 1)  # Now symmetric
                    weight = round(
                        base
                        * pair_boost
                        * (1.0 - min(orb / max(0.1, orb_deg), 1.0)),
                        2,
                    )
                    res.append(
                        {
                            "p1": a_name,
                            "p2": b_name,
                            "type": t,
                            "orb": orb,
                            "weight": weight,
                        }
                    )
    res.sort(key=lambda x: -x["weight"])
    return res


def midpoint_composite(person_a: Dict[str, Any], person_b: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calculate midpoint composite chart (Davison method).
    FIX: Uses circular mean to handle 0° Aries wrap correctly.
    
    Note: Houses are not computed (would require composite location/time).
    For full composite house calculation, use Davison or derived chart method.
    """
    A = _natal_positions(person_a)
    B = _natal_positions(person_b)
    comp = []
    for name in A.keys():
        lon = circular_midpoint(A[name]["lon"], B[name]["lon"])  # FIX: Circular mean
        comp.append(
            {
                "name": name,
                "lon": round(lon, 2),
                "sign": sign_name_from_lon(lon),
                "house": None,  # Not computed (requires composite location/time)
            }
        )
    return comp


def aggregate_score(syn: List[Dict[str, Any]]) -> float:
    s = sum(x["weight"] for x in syn)
    s = max(-30.0, min(30.0, s))
    return round((s + 30.0) / 60.0 * 100.0, 1)
