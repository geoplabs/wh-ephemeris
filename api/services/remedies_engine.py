from typing import Dict, Any, List
from . import ephem
from .constants import sign_name_from_lon
from .dignities import dignity_for

GEMSTONES = {
    "Sun": "Ruby",
    "Moon": "Pearl",
    "Mars": "Red Coral",
    "Mercury": "Emerald",
    "Jupiter": "Yellow Sapphire",
    "Venus": "Diamond",
    "Saturn": "Blue Sapphire",
    "Rahu": "Hessonite",
    "Ketu": "Cat's Eye",
}


def compute_remedies(chart_input: Dict[str, Any], allow_gemstones: bool = True) -> List[Dict[str, Any]]:
    jd = ephem.to_jd_utc(chart_input["date"], chart_input["time"], chart_input["place"]["tz"])
    sidereal = chart_input["system"] == "vedic"
    ayan = (
        (chart_input.get("options") or {}).get("ayanamsha", "lahiri") if sidereal else None
    )
    pos = ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayan)

    out = []
    for planet in [
        "Sun",
        "Moon",
        "Mars",
        "Mercury",
        "Jupiter",
        "Venus",
        "Saturn",
        "TrueNode",
        "Chiron",
    ]:
        if planet not in pos:
            continue
        lon = pos[planet]["lon"]
        sign = sign_name_from_lon(lon)
        dig = dignity_for(planet, sign)
        if dig in ("fall", "detriment"):
            item = {
                "planet": planet,
                "issue": f"{planet} in {dig}",
                "recommendation": "Strengthen {}-related qualities through disciplined practice, donations, and mantra.".format(
                    planet
                ),
                "gemstone": GEMSTONES.get(planet) if allow_gemstones else None,
                "cautions": [
                    "Consult a qualified practitioner.",
                    "Use certified gemstones only.",
                    "Budget responsibly.",
                ],
            }
            out.append(item)
    if not out:
        out.append(
            {
                "planet": "Overall",
                "issue": "No critical weaknesses detected",
                "recommendation": "Focus on balanced routines (sleep, diet, meditation) and service.",
                "gemstone": None,
                "cautions": [],
            }
        )
    return out
