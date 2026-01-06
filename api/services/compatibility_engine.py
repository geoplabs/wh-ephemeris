from typing import Dict, Any, List, Set
import math
from . import ephem, aspects as aspects_svc
from .constants import sign_name_from_lon

ASPECT_AFFECTION = {
    "conjunction": 3,
    "trine": 2,
    "sextile": 1,
    "square": -2,
    "opposition": -2,
}

# FIX 1: Order-invariant pair weights (store only one direction)
# Lookup will check both (a,b) and (b,a) automatically
PAIR_WEIGHTS = {
    ("Sun", "Sun"): 2,
    ("Sun", "Moon"): 3,  # Moon-Sun also gets 3
    ("Moon", "Moon"): 3,
    ("Venus", "Mars"): 3,  # Mars-Venus also gets 3
    ("Venus", "Venus"): 2,
    ("Mars", "Mars"): 2,
}


def get_pair_weight(planet1: str, planet2: str) -> float:
    """
    Get pair weight with automatic bidirectional lookup.
    FIX 1: Future-proof - no need to manually add symmetric entries.
    """
    return PAIR_WEIGHTS.get((planet1, planet2)) or PAIR_WEIGHTS.get((planet2, planet1), 1.0)


def angle_diff(lon1: float, lon2: float) -> float:
    """
    Public helper: calculate shortest arc between two ecliptic longitudes.
    
    Returns: Unsigned angular distance [0..180] degrees.
    
    FIX 3: This is correct for aspect matching (0/60/90/120/180).
    If you need signed difference (applying/separating logic), use a different function.
    
    Example:
        angle_diff(10, 350) = 20  (not -20 or +340)
        angle_diff(0, 180) = 180
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
    
    FIX 1: Uses order-invariant get_pair_weight()
    FIX 5: Converts aspect_types to set for O(1) membership checks
    """
    A = _natal_positions(person_a)
    B = _natal_positions(person_b)
    
    # FIX 5: Convert to set for faster membership checking
    aspect_types_set = set(aspect_types) if not isinstance(aspect_types, set) else aspect_types
    
    res = []
    for a_name, a_pos in A.items():
        # FIX 2: Skip if planet not in B (robustness for optional planets)
        for b_name, b_pos in B.items():
            d = angle_diff(a_pos["lon"], b_pos["lon"])
            for t, exact in aspects_svc.MAJOR.items():
                if t not in aspect_types_set:
                    continue
                if abs(d - exact) <= orb_deg:
                    orb = round(abs(d - exact), 2)
                    base = ASPECT_AFFECTION.get(t, 0)
                    pair_boost = get_pair_weight(a_name, b_name)  # FIX 1: Order-invariant
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
    
    FIX 2: Only includes planets present in BOTH charts (intersection).
    Uses circular mean to handle 0° Aries wrap correctly.
    
    Note: Houses are not computed (would require composite location/time).
    For full composite house calculation, use Davison or derived chart method.
    """
    A = _natal_positions(person_a)
    B = _natal_positions(person_b)
    comp = []
    
    # FIX 2: Only process planets present in both charts (safe intersection)
    common_planets = A.keys() & B.keys()
    
    for name in common_planets:
        lon = circular_midpoint(A[name]["lon"], B[name]["lon"])
        comp.append(
            {
                "name": name,
                "lon": round(lon, 2),
                "sign": sign_name_from_lon(lon),
                "house": None,  # Not computed (requires composite location/time)
            }
        )
    return comp


def aggregate_score(syn: List[Dict[str, Any]], method: str = "sigmoid") -> float:
    """
    Aggregate synastry aspect weights into a 0-100 compatibility score.
    
    FIX 4: Improved normalization to prevent ceiling collapse.
    
    Args:
        syn: List of synastry aspects with 'weight' field
        method: "sigmoid" (default, better distribution) or "clamp" (legacy)
    
    Returns:
        Score from 0 (worst) to 100 (best)
    
    Examples:
        - No aspects: ~50
        - Strong positive aspects: 70-90
        - Many strong aspects: 90-98 (not all 100)
        - Challenging aspects: 20-40
    """
    if not syn:
        return 50.0  # Neutral if no aspects
    
    total_weight = sum(x["weight"] for x in syn)
    
    if method == "sigmoid":
        # FIX 4: Sigmoid mapping - prevents ceiling collapse, better discrimination
        # Maps [-infinity, +infinity] -> [0, 100] with smooth curve
        # Center at 0, scale factor of 15 gives good spread
        score = 100.0 / (1.0 + math.exp(-total_weight / 15.0))
        return round(score, 1)
    else:
        # Legacy: hard clamp (aggressive saturation)
        s = max(-30.0, min(30.0, total_weight))
        return round((s + 30.0) / 60.0 * 100.0, 1)
