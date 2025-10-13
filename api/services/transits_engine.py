from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from . import ephem, aspects as aspects_svc, houses as houses_svc
from .constants import sign_name_from_lon

ASPECT_WEIGHTS = {"conjunction":5, "opposition":4, "square":3, "trine":2, "sextile":1}
PLANET_WEIGHTS = {"Saturn":3,"Jupiter":2,"Mars":2,"Sun":1,"Venus":1,"Mercury":1,"Moon":0.5,
                  "Uranus":3,"Neptune":3,"Pluto":3,"TrueNode":1,"Chiron":1}

def _utc_date(y,m,d,h=12)->datetime:
    return datetime(y,m,d,h,0,0,tzinfo=timezone.utc)

def _daterange_utc(d0:str, d1:str, step_days:int):
    a = datetime.fromisoformat(d0+"T12:00:00+00:00")
    b = datetime.fromisoformat(d1+"T12:00:00+00:00")
    cur = a
    while cur <= b:
        yield cur
        cur = cur + timedelta(days=step_days)

def _severity_score(aspect:str, orb:float, orb_limit:float, t_body:str)->float:
    base = ASPECT_WEIGHTS.get(aspect,1) + PLANET_WEIGHTS.get(t_body,1)
    closeness = max(0.0, 1.0 - (orb / max(0.001, orb_limit)))
    return round(10.0 * (0.3*base/8.0 + 0.7*closeness), 2)

def _natal_positions(chart_input: Dict[str,Any]) -> Dict[str,Dict[str,float]]:
    # compute natal positions (tropical or sidereal based on chart_input.system)
    sidereal = (chart_input["system"] == "vedic")
    ayan = (chart_input.get("options") or {}).get("ayanamsha","lahiri") if sidereal else None
    jd = ephem.to_jd_utc(chart_input["date"], chart_input["time"], chart_input["place"]["tz"])
    pos = ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayan)
    out = {k: {"lon": v["lon"], "speed_lon": v["speed_lon"]} for k,v in pos.items()}
    # add angles if time known
    if chart_input.get("time_known", True):
        hs = houses_svc.houses(jd, chart_input["place"]["lat"], chart_input["place"]["lon"], 
                               (chart_input.get("options") or {}).get("house_system","placidus"))
        out["Ascendant"] = {"lon": hs["asc"], "speed_lon": 0.0}
        out["Midheaven"] = {"lon": hs["mc"],  "speed_lon": 0.0}
    return out

def _transit_positions(dt: datetime, system: str, ayan: str|None) -> Dict[str,Dict[str,float]]:
    # compute positions at UTC noon on that date
    jd = ephem.to_jd_utc(dt.date().isoformat(), "12:00:00", "UTC")
    sidereal = (system == "vedic")
    pos = ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=(ayan or "lahiri"))
    return {k: {"lon": v["lon"], "speed_lon": v["speed_lon"]} for k,v in pos.items()}

def compute_transits(chart_input: Dict[str,Any], opts: Dict[str,Any]) -> List[Dict[str,Any]]:
    # options
    obs_from = opts["from_date"]; obs_to = opts["to_date"]
    step = int(opts.get("step_days",1))
    transit_bodies = set(opts.get("transit_bodies") or ["Sun","Mars","Jupiter","Saturn"])
    policy = opts.get("aspects") or {}
    orb_limit = float(policy.get("orb_deg", 3.0))
    aspect_types = policy.get("types", ["conjunction","opposition","square","trine","sextile"])

    natal_map = _natal_positions(chart_input)
    natal_targets = list((opts.get("natal_targets") or list(natal_map.keys())))

    sidereal = (chart_input["system"] == "vedic")
    ayan = (chart_input.get("options") or {}).get("ayanamsha","lahiri") if sidereal else None

    events: List[Dict[str,Any]] = []
    for dt in _daterange_utc(obs_from, obs_to, step):
        tr = _transit_positions(dt, chart_input["system"], ayan)
        # restrict to transit_bodies
        T = {k:v for k,v in tr.items() if k in transit_bodies}
        for t_name, t_pos in T.items():
            for n_name in natal_targets:
                if n_name not in natal_map: 
                    continue
                n_pos = natal_map[n_name]
                d = aspects_svc._angle_diff(t_pos["lon"], n_pos["lon"])
                # find best aspect match
                for a_name, a_exact in aspects_svc.MAJOR.items():
                    if a_name not in aspect_types:
                        continue
                    if abs(d - a_exact) <= orb_limit:
                        orb = round(abs(d - a_exact), 2)
                        score = _severity_score(a_name, orb, orb_limit, t_name)
                        applying = t_pos["speed_lon"] > n_pos["speed_lon"]
                        phase = "Applying" if applying else "Separating"
                        transit_sign = sign_name_from_lon(t_pos["lon"])
                        natal_sign = sign_name_from_lon(n_pos["lon"])
                        note = (
                            f"{phase} {a_name} at {orb:.2f}° orb. "
                            f"{t_name} in {transit_sign}; {n_name} in {natal_sign}."
                        )
                        events.append({
                            "date": dt.date().isoformat(),
                            "transit_body": t_name,
                            "natal_body": n_name,
                            "aspect": a_name,
                            "orb": orb,
                            "applying": applying,
                            "score": score,
                            "note": note,
                        })
    # Sort: date then score desc
    events.sort(key=lambda e: (e["date"], -e["score"]))
    return events
