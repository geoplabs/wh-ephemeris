from typing import Dict, Any, List
from . import ephem, aspects as aspects_svc, houses as houses_svc
from .constants import sign_name_from_lon

ASPECT_AFFECTION = {
    "conjunction": 3,
    "trine": 2,
    "sextile": 1,
    "square": -2,
    "opposition": -2,
}
PAIR_WEIGHTS = {
    ("Sun", "Sun"): 2,
    ("Sun", "Moon"): 3,
    ("Moon", "Moon"): 3,
    ("Venus", "Mars"): 3,
    ("Venus", "Venus"): 2,
    ("Mars", "Mars"): 2,
}


def _natal_positions(chart_input: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    sidereal = chart_input["system"] == "vedic"
    ayan = (
        (chart_input.get("options") or {}).get("ayanamsha", "lahiri") if sidereal else None
    )
    jd = ephem.to_jd_utc(chart_input["date"], chart_input["time"], chart_input["place"]["tz"])
    return ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayan)


def synastry(person_a: Dict[str, Any], person_b: Dict[str, Any], aspect_types, orb_deg: float) -> List[Dict[str, Any]]:
    A = _natal_positions(person_a)
    B = _natal_positions(person_b)
    res = []
    for a_name, a_pos in A.items():
        for b_name, b_pos in B.items():
            d = aspects_svc._angle_diff(a_pos["lon"], b_pos["lon"])
            for t, exact in aspects_svc.MAJOR.items():
                if t not in aspect_types:
                    continue
                if abs(d - exact) <= orb_deg:
                    orb = round(abs(d - exact), 2)
                    base = ASPECT_AFFECTION.get(t, 0)
                    pair_boost = PAIR_WEIGHTS.get((a_name, b_name), 1)
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
    A = _natal_positions(person_a)
    B = _natal_positions(person_b)
    comp = []
    for name in A.keys():
        lon = ((A[name]["lon"] + B[name]["lon"]) / 2.0) % 360.0
        comp.append(
            {
                "name": name,
                "lon": round(lon, 2),
                "sign": sign_name_from_lon(lon),
                "house": None,
            }
        )
    return comp


def aggregate_score(syn: List[Dict[str, Any]]) -> float:
    s = sum(x["weight"] for x in syn)
    s = max(-30.0, min(30.0, s))
    return round((s + 30.0) / 60.0 * 100.0, 1)
