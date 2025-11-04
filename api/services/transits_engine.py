from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from . import ephem, aspects as aspects_svc, houses as houses_svc
from .transit_math import is_applying
from .constants import sign_name_from_lon

ASPECT_WEIGHTS = {
    "conjunction": 2,    # Neutral-to-supportive (depends on planet)
    "opposition": 4,     # Friction
    "square": 3,         # Friction
    "trine": -2,         # Supportive (NEGATIVE)
    "sextile": -1,       # Supportive (NEGATIVE)
    "quincunx": 1,       # Minor friction
}
PLANET_WEIGHTS = {"Saturn":3,"Jupiter":2,"Mars":2,"Sun":1,"Venus":1,"Mercury":1,"Moon":0.5,
                  "Uranus":3,"Neptune":3,"Pluto":3,"TrueNode":1,"Chiron":1}

# Fast-moving planets for exact time calculation and prioritization
FAST_MOVING_PLANETS = {"Moon", "Mercury", "Venus", "Sun", "Mars"}
SLOW_MOVING_PLANETS = {"Saturn", "Jupiter", "Uranus", "Neptune", "Pluto", "Chiron", "TrueNode"}
ANGLE_POINTS = {"Ascendant", "Midheaven", "Descendant", "IC"}

PLANET_EXPRESSIONS: Dict[str, Dict[str, str]] = {
    "Sun": {"descriptor": "Radiant", "theme": "self-expression"},
    "Moon": {"descriptor": "Sensitive", "theme": "emotional rhythms"},
    "Mercury": {"descriptor": "Curious", "theme": "communication"},
    "Venus": {"descriptor": "Harmonizing", "theme": "relationships"},
    "Mars": {"descriptor": "Passionate", "theme": "drive"},
    "Jupiter": {"descriptor": "Expansive", "theme": "growth"},
    "Saturn": {"descriptor": "Disciplined", "theme": "responsibilities"},
    "Uranus": {"descriptor": "Liberating", "theme": "innovation"},
    "Neptune": {"descriptor": "Inspired", "theme": "imagination"},
    "Pluto": {"descriptor": "Transformative", "theme": "personal power"},
    "TrueNode": {"descriptor": "Destined", "theme": "life direction"},
    "Chiron": {"descriptor": "Healing", "theme": "inner growth"},
    "Ascendant": {"descriptor": "Emergent", "theme": "outer persona"},
    "Midheaven": {"descriptor": "Aspirational", "theme": "public ambitions"},
}

ASPECT_PHRASES = {
    "conjunction": "energy in",
    "opposition": "tension to balance within",
    "square": "challenges around",
    "trine": "period for",
    "sextile": "opportunity for",
    "quincunx": "adjustments in",
}

ASPECT_GUIDANCE = {
    "conjunction": "Channel this focus with intention.",
    "opposition": "Find healthy compromise to integrate both sides.",
    "square": "Take decisive steps to work through the friction.",
    "trine": "Trust the momentum and share your gifts.",
    "sextile": "Say yes to supportive openings as they arise.",
    "quincunx": "Make thoughtful adjustments to keep the pieces aligned.",
}

def _intensity_adverb(score: float) -> str:
    if score >= 8.5:
        return "Powerfully"
    if score >= 7.0:
        return "Strongly"
    if score >= 5.5:
        return "Notably"
    if score >= 3.5:
        return "Gently"
    return "Subtly"

def _interpretive_note(transit_body: str, natal_body: str, aspect: str, score: float) -> str:
    t_expr = PLANET_EXPRESSIONS.get(transit_body, {"descriptor": "Dynamic", "theme": "momentum"})
    n_expr = PLANET_EXPRESSIONS.get(natal_body, {"descriptor": "core", "theme": "life areas"})
    tone = ASPECT_PHRASES.get(aspect, "influence on")
    guidance = ASPECT_GUIDANCE.get(aspect, "Stay mindful of the shifting tone.")
    adverb = _intensity_adverb(score)
    descriptor = t_expr["descriptor"]
    theme = n_expr["theme"]
    headline = f"{adverb} {descriptor.lower()} {tone} {theme}".strip()
    # Capitalize first letter for readability
    headline = headline[0].upper() + headline[1:]
    return f"{headline}. {guidance}"

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
    """Calculate score with proper polarity: negative=supportive, positive=friction."""
    aspect_weight = ASPECT_WEIGHTS.get(aspect, 1)
    planet_weight = PLANET_WEIGHTS.get(t_body, 1)
    closeness = max(0.0, 1.0 - (orb / max(0.001, orb_limit)))
    
    # Polarity from aspect (negative = supportive, positive = friction)
    # Magnitude from planet importance and closeness
    polarity = 1 if aspect_weight > 0 else -1 if aspect_weight < 0 else 0
    magnitude = abs(aspect_weight) * planet_weight * closeness
    
    return round(polarity * magnitude * 3.0, 2)

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

def _natal_point_type(natal_name: str) -> str:
    """Determine if natal point is planet, angle, or house cusp."""
    if natal_name in ANGLE_POINTS or natal_name in {"Ascendant", "Midheaven"}:
        return "angle"
    if natal_name.startswith("House"):
        return "house_cusp"
    return "planet"

def _calculate_exact_hit_time(
    transit_lon: float,
    transit_speed: float,
    natal_lon: float,
    aspect_angle: float,
    base_date: datetime,
) -> Optional[str]:
    """Calculate exact UTC time when aspect becomes perfect.
    
    Only calculates for fast-moving planets with reasonable daily motion.
    Returns ISO format string with UTC timezone.
    """
    if abs(transit_speed) < 0.01:  # Too slow to calculate precise time
        return None
    
    # Calculate angular separation using shortest arc
    # This gives us the "aspect-like" separation (0-180°)
    diff = (transit_lon - natal_lon) % 360
    if diff > 180:
        diff = 360 - diff
    
    # How far are we from the exact aspect angle?
    orb = diff - aspect_angle
    
    # To determine direction (applying vs separating), simulate planet position in 1 hour
    future_lon = transit_lon + (transit_speed / 24.0)
    future_diff = (future_lon - natal_lon) % 360
    if future_diff > 180:
        future_diff = 360 - future_diff
    
    # If future separation is smaller, we're applying (negative delta)
    # If future separation is larger, we're separating (positive delta)
    if abs(future_diff - aspect_angle) < abs(orb):
        # Applying - we haven't hit exact yet
        delta = -orb
    else:
        # Separating - we've passed exact
        delta = orb
    
    # Calculate hours to exact aspect
    hours_to_exact = delta / (transit_speed / 24.0) if transit_speed != 0 else None
    
    # Allow ±72 hours to capture aspects that are active today even if exact hit was recent or upcoming
    if hours_to_exact is None or abs(hours_to_exact) > 72:  # More than 3 days away
        return None
    
    exact_time = base_date + timedelta(hours=hours_to_exact)
    return exact_time.isoformat().replace("+00:00", "Z")

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
    # Default: prioritize fast-moving planets for better caution window calculation
    default_bodies = ["Moon", "Mercury", "Venus", "Sun", "Mars", "Jupiter", "Saturn"]
    transit_bodies = set(opts.get("transit_bodies") or default_bodies)
    policy = opts.get("aspects") or {}
    orb_limit = float(policy.get("orb_deg", 3.0))
    aspect_types = policy.get(
        "types",
        ["conjunction", "opposition", "square", "trine", "sextile", "quincunx"],
    )
    requested_aspects = {
        aspects_svc.canonical_aspect(name)
        for name in aspect_types
        if aspects_svc.canonical_aspect(name) in aspects_svc.MAJOR
    }

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
                    if a_name not in requested_aspects:
                        continue
                    if abs(d - a_exact) <= orb_limit:
                        orb = round(abs(d - a_exact), 2)
                        score = _severity_score(a_name, orb, orb_limit, t_name)
                        applying = is_applying(
                            t_pos["lon"],
                            t_pos["speed_lon"],
                            n_pos["lon"],
                            n_pos["speed_lon"],
                            a_exact,
                        )
                        phase = "applying" if applying else "separating"
                        phase_cap = "Applying" if applying else "Separating"
                        transit_sign = sign_name_from_lon(t_pos["lon"])
                        natal_sign = sign_name_from_lon(n_pos["lon"])
                        zodiac_mode = "sidereal" if sidereal else "tropical"
                        note = (
                            f"{_interpretive_note(t_name, n_name, a_name, score)} "
                            f"{phase_cap} {a_name} at {orb:.2f}° orb. "
                            f"{t_name} (transit, {zodiac_mode}) in {transit_sign}; "
                            f"{n_name} (natal, {zodiac_mode}) in {natal_sign}."
                        )
                        
                        # Calculate exact hit time for fast-moving planets
                        exact_hit_time_utc = None
                        if t_name in FAST_MOVING_PLANETS and abs(t_pos["speed_lon"]) > 0.01:
                            exact_hit_time_utc = _calculate_exact_hit_time(
                                t_pos["lon"],
                                t_pos["speed_lon"],
                                n_pos["lon"],
                                a_exact,
                                dt,
                            )
                        
                        # Determine transit motion (retrograde/direct)
                        transit_motion = "retrograde" if t_pos["speed_lon"] < 0 else "direct"
                        
                        # Determine natal point type
                        natal_point_type = _natal_point_type(n_name)
                        
                        # Build event dict
                        event = {
                            "date": dt.date().isoformat(),
                            "transit_body": t_name,
                            "natal_body": n_name,
                            "aspect": a_name,
                            "orb": orb,
                            "applying": applying,
                            "phase": phase,  # lowercase for caution window compatibility
                            "score": score,
                            "note": note,
                            "transit_sign": transit_sign,
                            "natal_sign": natal_sign,
                            "zodiac": zodiac_mode,
                            "transit_motion": transit_motion,
                            "natal_point_type": natal_point_type,
                        }
                        
                        # Add exact_hit_time_utc if calculated
                        if exact_hit_time_utc:
                            event["exact_hit_time_utc"] = exact_hit_time_utc
                        
                        events.append(event)
    
    # Sort: Prioritize fast-moving planets, then by date, then by score
    # Priority order: fast planets with exact_hit_time > fast planets without > slow planets
    def _sort_key(e: Dict[str, Any]) -> tuple:
        is_fast = e["transit_body"] in FAST_MOVING_PLANETS
        has_exact_time = "exact_hit_time_utc" in e
        # Priority: fast with time (0), fast without time (1), slow (2)
        priority = 0 if (is_fast and has_exact_time) else (1 if is_fast else 2)
        return (e["date"], priority, -e["score"])
    
    events.sort(key=_sort_key)
    return events
