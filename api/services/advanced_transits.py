"""
Advanced Transit Features for Personalized Daily Horoscopes

This module implements:
1. Station detection (Retrograde/Direct changes)
2. Retrograde category bias
3. Sign changes (Ingresses)
4. Solar relationships (Cazimi, Combust, Under Beams)
5. Enhanced outer-planet windows

Author: WH Ephemeris Team
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from . import ephem
from .constants import sign_name_from_lon


# ============================================================================
# CONSTANTS
# ============================================================================

# Station windows (hours before/after exact station)
STATION_WINDOWS = {
    "Moon": 12,      # ±12 hours
    "Mercury": 24,   # ±24 hours
    "Venus": 24,     # ±24 hours
    "Sun": 0,        # Sun doesn't go retrograde
    "Mars": 48,      # ±48 hours
    "Jupiter": 72,   # ±72 hours
    "Saturn": 72,    # ±72 hours
    "Uranus": 72,    # ±72 hours
    "Neptune": 72,   # ±72 hours
    "Pluto": 72,     # ±72 hours
    "Chiron": 48,    # ±48 hours
}

# Retrograde category biases
RETROGRADE_CATEGORIES = {
    "Mercury": {
        "areas": ["career", "communication", "logistics", "technology"],
        "ongoing_modifier": 0.2,
        "station_boost": 0.8,
        "description": "Communication, logistics, and technology review period"
    },
    "Venus": {
        "areas": ["love", "finance", "relationships", "aesthetics"],
        "ongoing_modifier": 0.2,
        "station_boost": 0.8,
        "description": "Relationship and financial review period"
    },
    "Mars": {
        "areas": ["career", "health", "assertiveness", "action"],
        "ongoing_modifier": 0.2,
        "station_boost": 0.8,
        "description": "Action and assertiveness recalibration period"
    },
    "Jupiter": {
        "areas": ["career", "growth", "expansion", "opportunities"],
        "ongoing_modifier": 0.15,
        "station_boost": 0.6,
        "description": "Growth and expansion review period"
    },
    "Saturn": {
        "areas": ["career", "structure", "responsibility", "discipline"],
        "ongoing_modifier": 0.15,
        "station_boost": 0.6,
        "description": "Structure and responsibility review period"
    },
}

# Solar proximity thresholds (degrees)
CAZIMI_THRESHOLD = 17 / 60  # ~0.28° (17 arcminutes)
COMBUST_THRESHOLD = 8.0     # 8°
UNDER_BEAMS_THRESHOLD = 17.0  # 17°

# Ingress window (hours around sign change)
INGRESS_WINDOW_HOURS = {
    "Moon": 3,
    "Mercury": 4,
    "Venus": 4,
    "Sun": 6,
    "Mars": 5,
    "Jupiter": 6,
    "Saturn": 6,
    "Uranus": 6,
    "Neptune": 6,
    "Pluto": 6,
}


# ============================================================================
# STATION DETECTION
# ============================================================================

def detect_station(
    planet: str,
    current_speed: float,
    forecast_date: datetime,
    chart_date: datetime,
) -> Optional[Dict[str, Any]]:
    """
    Detect if a planet is stationary (near direction change).
    
    Args:
        planet: Planet name
        current_speed: Current longitudinal speed (degrees/day)
        forecast_date: Date for the forecast
        chart_date: Birth date
        
    Returns:
        Station info dict or None
    """
    # Check if planet can go retrograde
    if planet not in STATION_WINDOWS or STATION_WINDOWS[planet] == 0:
        return None
    
    # Define stationary threshold based on planet
    stationary_thresholds = {
        "Mercury": 0.15,
        "Venus": 0.10,
        "Mars": 0.08,
        "Jupiter": 0.05,
        "Saturn": 0.03,
        "Uranus": 0.02,
        "Neptune": 0.01,
        "Pluto": 0.01,
        "Chiron": 0.03,
    }
    
    threshold = stationary_thresholds.get(planet, 0.05)
    
    # Check if speed is near zero (stationary)
    if abs(current_speed) <= threshold:
        station_type = "stationary_direct" if current_speed >= 0 else "stationary_retrograde"
        
        return {
            "planet": planet,
            "station_type": station_type,
            "speed": current_speed,
            "window_hours": STATION_WINDOWS[planet],
            "is_station": True,
        }
    
    return None


def calculate_station_score(
    station_info: Dict[str, Any],
    aspect: str,
    natal_point: str,
    planet: str,
) -> float:
    """
    Calculate score modifier for station events.
    
    Station affecting angles or luminaries:
    - Mars/Saturn/Outer planets + hard aspects to angles: +1.0 (caution)
    - Venus/Jupiter + soft aspects to luminaries: -0.8 (support)
    
    Args:
        station_info: Station detection result
        aspect: Aspect type (conjunction, square, etc.)
        natal_point: Natal point being aspected
        planet: Transit planet
        
    Returns:
        Score modifier
    """
    if not station_info or not station_info.get("is_station"):
        return 0.0
    
    # Define heavy planets
    heavy_planets = {"Mars", "Saturn", "Uranus", "Neptune", "Pluto"}
    benefics = {"Venus", "Jupiter"}
    hard_aspects = {"conjunction", "square", "opposition"}
    soft_aspects = {"trine", "sextile"}
    angles = {"Ascendant", "Midheaven", "Descendant", "IC"}
    luminaries = {"Sun", "Moon"}
    
    # Mars/Saturn/Outer planets + hard aspects to angles -> Caution
    if planet in heavy_planets and aspect in hard_aspects and natal_point in angles:
        return 1.0
    
    # Venus/Jupiter + soft aspects to luminaries -> Support
    if planet in benefics and aspect in soft_aspects and natal_point in luminaries:
        return -0.8
    
    return 0.0


# ============================================================================
# RETROGRADE CATEGORY BIAS
# ============================================================================

def get_retrograde_bias(planet: str, is_retrograde: bool, is_near_station: bool = False) -> Dict[str, Any]:
    """
    Get retrograde category bias for a planet.
    
    Args:
        planet: Planet name
        is_retrograde: Is planet currently retrograde
        is_near_station: Is planet near a station
        
    Returns:
        Bias info including affected areas and modifiers
    """
    if not is_retrograde or planet not in RETROGRADE_CATEGORIES:
        return {
            "has_bias": False,
            "areas": [],
            "modifier": 0.0,
            "description": ""
        }
    
    category = RETROGRADE_CATEGORIES[planet]
    modifier = category["station_boost"] if is_near_station else category["ongoing_modifier"]
    
    return {
        "has_bias": True,
        "planet": planet,
        "areas": category["areas"],
        "modifier": modifier,
        "description": category["description"],
        "is_near_station": is_near_station,
    }


# ============================================================================
# SIGN CHANGES (INGRESSES)
# ============================================================================

def detect_ingress(
    planet: str,
    current_lon: float,
    forecast_date: datetime,
    natal_positions: Dict[str, float],
) -> Optional[Dict[str, Any]]:
    """
    Detect if a planet is near a sign change (ingress).
    
    Args:
        planet: Planet name
        current_lon: Current longitude
        forecast_date: Forecast date
        natal_positions: Dict of natal planet/angle positions
        
    Returns:
        Ingress info dict or None
    """
    # Calculate degrees to next sign boundary
    current_sign_start = (int(current_lon / 30)) * 30
    next_sign_boundary = current_sign_start + 30
    
    # Distance to next boundary
    degrees_to_boundary = next_sign_boundary - current_lon
    if degrees_to_boundary > 30:
        degrees_to_boundary -= 360
    
    # Also check distance from previous boundary
    degrees_from_boundary = current_lon - current_sign_start
    
    # Ingress window: 3-6 hours, which translates to degrees based on planet speed
    # Approximate: Moon ~0.5°/hour, Mercury ~1.5°/day, etc.
    ingress_thresholds = {
        "Moon": 1.5,      # ~3 hours (Moon moves ~13°/day)
        "Mercury": 0.5,   # ~4 hours
        "Venus": 0.4,     # ~4 hours
        "Sun": 0.25,      # ~6 hours
        "Mars": 0.3,      # ~5 hours
        "Jupiter": 0.02,  # ~6 hours (slow)
        "Saturn": 0.01,   # ~6 hours (slow)
        "Uranus": 0.005,  # ~6 hours (very slow)
        "Neptune": 0.003, # ~6 hours (very slow)
        "Pluto": 0.002,   # ~6 hours (very slow)
    }
    
    threshold = ingress_thresholds.get(planet, 0.5)
    
    # Check if near ingress (either approaching or just passed)
    is_near_ingress = degrees_to_boundary <= threshold or degrees_from_boundary <= threshold
    
    if not is_near_ingress:
        return None
    
    # Determine which sign we're entering/leaving
    current_sign_num = int(current_lon / 30) % 12
    entering_sign = sign_name_from_lon((current_sign_num + 1) * 30 % 360)
    leaving_sign = sign_name_from_lon(current_sign_num * 30)
    
    # Check if ingress hits natal angle/planet (boost if within 1.5°)
    boost = 0.0
    hit_points = []
    for natal_name, natal_lon in natal_positions.items():
        # Check if natal point is near either boundary
        for boundary in [current_sign_start, next_sign_boundary % 360]:
            angular_distance = abs((natal_lon - boundary + 180) % 360 - 180)
            if angular_distance <= 1.5:
                boost = 0.6
                hit_points.append(natal_name)
    
    return {
        "planet": planet,
        "is_ingress": True,
        "leaving_sign": leaving_sign,
        "entering_sign": entering_sign,
        "degrees_to_boundary": min(degrees_to_boundary, degrees_from_boundary),
        "window_hours": INGRESS_WINDOW_HOURS.get(planet, 4),
        "boost": boost,
        "hit_natal_points": hit_points,
    }


# ============================================================================
# SOLAR RELATIONSHIPS
# ============================================================================

def calculate_solar_relationship(planet_lon: float, sun_lon: float) -> Dict[str, Any]:
    """
    Calculate solar relationship (Cazimi, Combust, Under Beams).
    
    Args:
        planet_lon: Planet's ecliptic longitude
        sun_lon: Sun's ecliptic longitude
        
    Returns:
        Solar relationship info
    """
    # Calculate angular distance to Sun
    distance = abs((planet_lon - sun_lon + 180) % 360 - 180)
    
    relationship_type = None
    score_modifier = 0.0
    description = ""
    
    if distance <= CAZIMI_THRESHOLD:
        relationship_type = "cazimi"
        score_modifier = -1.0  # Strong support for planet's topics
        description = "Heart of the Sun - clarity and power"
    elif distance <= COMBUST_THRESHOLD:
        relationship_type = "combust"
        score_modifier = -0.5  # Weakens planet's support
        description = "Combust - planet weakened by Sun"
    elif distance <= UNDER_BEAMS_THRESHOLD:
        relationship_type = "under_beams"
        score_modifier = -0.2  # Minor weakening
        description = "Under the Beams - planet slightly weakened"
    
    return {
        "has_solar_relationship": relationship_type is not None,
        "type": relationship_type,
        "distance_to_sun": round(distance, 4),
        "score_modifier": score_modifier,
        "description": description,
    }


# ============================================================================
# ENHANCED OUTER-PLANET WINDOWS
# ============================================================================

def calculate_enhanced_window(
    planet: str,
    aspect: str,
    natal_point: str,
    standard_window_hours: int,
) -> int:
    """
    Calculate enhanced window duration for outer planets.
    
    Outer planets with hard aspects to Sun/Moon/ASC/MC get longer windows (±24-48h).
    
    Args:
        planet: Transit planet
        aspect: Aspect type
        natal_point: Natal point
        standard_window_hours: Standard window duration
        
    Returns:
        Enhanced window duration in hours
    """
    outer_planets = {"Saturn", "Uranus", "Neptune", "Pluto"}
    hard_aspects = {"square", "opposition"}
    key_points = {"Sun", "Moon", "Ascendant", "Midheaven"}
    
    # Outer planet + hard aspect + key point = extended window
    if planet in outer_planets and aspect in hard_aspects and natal_point in key_points:
        # Saturn: ±24h, Uranus/Neptune/Pluto: ±48h
        if planet == "Saturn":
            return 24
        else:
            return 48
    
    return standard_window_hours


def calculate_outer_planet_score_boost(
    planet: str,
    aspect: str,
    natal_point: str,
    base_score: float,
) -> float:
    """
    Calculate score boost for outer planet hard aspects to key points.
    
    Args:
        planet: Transit planet
        aspect: Aspect type
        natal_point: Natal point
        base_score: Base score from standard calculation
        
    Returns:
        Boosted score
    """
    outer_planets = {"Saturn", "Uranus", "Neptune", "Pluto"}
    hard_aspects = {"square", "opposition"}
    key_points = {"Sun", "Moon", "Ascendant", "Midheaven"}
    
    if planet in outer_planets and aspect in hard_aspects and natal_point in key_points:
        # Boost range: +1.2 to +2.0 depending on planet
        boost_factors = {
            "Saturn": 1.2,
            "Uranus": 1.5,
            "Neptune": 1.5,
            "Pluto": 2.0,
        }
        boost = boost_factors.get(planet, 1.2)
        return base_score + boost
    
    # Soft aspects from Jupiter/Venus get support boost
    benefics = {"Jupiter", "Venus"}
    soft_aspects = {"trine", "sextile"}
    
    if planet in benefics and aspect in soft_aspects:
        return base_score - 1.0
    
    return base_score


# ============================================================================
# VEDIC-SPECIFIC FEATURES
# ============================================================================

def detect_nodal_contact(
    transit_body: str,
    natal_body: str,
    orb: float,
    aspect: str,
) -> Optional[Dict[str, Any]]:
    """
    Detect Rahu/Ketu contacts to luminaries/angles for Vedic charts.
    
    Rahu/Ketu within ≤2° of Sun/Moon/ASC/MC get "fated shift" flavor
    with enhanced significance.
    
    Args:
        transit_body: Transit planet (Rahu or Ketu)
        natal_body: Natal point
        orb: Aspect orb in degrees
        aspect: Aspect type
        
    Returns:
        Nodal contact info dict or None
    """
    nodes = {"Rahu", "Ketu", "TrueNode", "MeanNode"}
    luminaries_angles = {"Sun", "Moon", "Ascendant", "Midheaven", "MC", "ASC"}
    
    # Normalize names
    transit_normalized = transit_body.strip().title()
    natal_normalized = natal_body.strip().title()
    
    # Check if this is a nodal contact to luminary/angle
    is_nodal_contact = (
        transit_normalized in nodes and
        natal_normalized in luminaries_angles and
        orb <= 2.0  # Tight orb for fated significance
    )
    
    if not is_nodal_contact:
        return None
    
    # Calculate bias based on orb tightness
    # Tighter orb = stronger fated influence
    if orb <= 0.5:
        # Very tight (±12h window)
        bias = 0.8
        window_hours = 12
        intensity = "strong"
    elif orb <= 1.0:
        # Tight
        bias = 0.5
        window_hours = 12
        intensity = "moderate"
    else:
        # Within threshold
        bias = 0.3
        window_hours = 12
        intensity = "subtle"
    
    # Determine node type effect
    # Note: TrueNode and MeanNode are the North Node (Rahu in Vedic)
    if transit_normalized in {"Rahu", "Truenode", "Meannode"}:
        node_type = "Rahu"
        description = "Fated amplification - karmic intensification"
        # Rahu amplifies and magnifies
        score_modifier = bias
    else:  # Ketu
        node_type = "Ketu"
        description = "Fated release - karmic culmination"
        # Ketu releases and dissolves
        score_modifier = -bias * 0.7  # Slightly less intense than Rahu
    
    return {
        "has_nodal_contact": True,
        "node_type": node_type,
        "natal_point": natal_normalized,
        "orb": orb,
        "intensity": intensity,
        "bias": bias,
        "score_modifier": score_modifier,
        "window_hours": window_hours,
        "description": description,
    }


def calculate_panchang_influence(
    tithi: Optional[str] = None,
    nakshatra: Optional[str] = None,
    yoga: Optional[str] = None,
    karana: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate influence from Panchang elements for daily microcopy and remedies.
    
    Args:
        tithi: Lunar day (1-30)
        nakshatra: Lunar mansion (1-27)
        yoga: Nitya Yoga (1-27)
        karana: Half-tithi (1-11)
        
    Returns:
        Panchang influence data for microcopy
    """
    # Auspicious Tithis
    auspicious_tithis = {
        "2", "3", "5", "7", "10", "11", "13",  # Generally favorable
    }
    
    # Challenging Tithis
    challenging_tithis = {
        "4", "6", "8", "9", "14",  # Require extra care
    }
    
    # Auspicious Nakshatras (for specific activities)
    auspicious_nakshatras = {
        "1": "Ashwini - swift beginnings",
        "5": "Mrigashira - seeking and exploration",
        "8": "Pushya - nourishment and growth",
        "10": "Magha - ancestral blessings",
        "11": "Purva Phalguni - creative expression",
        "17": "Anuradha - devotion and discipline",
        "22": "Shravana - learning and listening",
        "27": "Revati - completion and transcendence",
    }
    
    panchang_data = {
        "has_panchang": False,
        "tithi_influence": None,
        "nakshatra_cue": None,
        "remedy_timing": None,
        "microcopy": [],
    }
    
    if tithi:
        panchang_data["has_panchang"] = True
        if tithi in auspicious_tithis:
            panchang_data["tithi_influence"] = "favorable"
            panchang_data["microcopy"].append(f"Tithi {tithi} supports clear intentions")
        elif tithi in challenging_tithis:
            panchang_data["tithi_influence"] = "caution"
            panchang_data["microcopy"].append(f"Tithi {tithi} calls for patience")
    
    if nakshatra and nakshatra in auspicious_nakshatras:
        panchang_data["has_panchang"] = True
        panchang_data["nakshatra_cue"] = auspicious_nakshatras[nakshatra]
        panchang_data["microcopy"].append(f"Today's Nakshatra: {auspicious_nakshatras[nakshatra]}")
    
    # Yoga-based timing (some yogas are better for spiritual/material activities)
    auspicious_yogas = {"2", "3", "7", "10", "11", "13", "16", "17", "19", "26"}
    if yoga and yoga in auspicious_yogas:
        panchang_data["has_panchang"] = True
        panchang_data["remedy_timing"] = "favorable"
        panchang_data["microcopy"].append("Today's Yoga supports spiritual practices")
    
    return panchang_data


# ============================================================================
# DECLINATION & PARALLELS (ADVANCED)
# ============================================================================

def calculate_declination_parallel(
    planet_declination: float,
    natal_sun_dec: Optional[float] = None,
    natal_moon_dec: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate parallels and contra-parallels to natal Sun/Moon.
    
    Parallel: Both bodies at same declination (±1°)
    Contra-parallel: Bodies at opposite declinations (±1°)
    
    These create subtle influences on mood and clarity windows.
    
    Args:
        planet_declination: Transit planet's declination
        natal_sun_dec: Natal Sun declination
        natal_moon_dec: Natal Moon declination
        
    Returns:
        Declination aspect info
    """
    PARALLEL_ORB = 1.0  # ±1° for parallel/contra-parallel
    
    declination_aspects = {
        "has_declination_aspect": False,
        "aspects": [],
        "total_bias": 0.0,
    }
    
    # Check parallel to natal Sun
    if natal_sun_dec is not None:
        diff = abs(planet_declination - natal_sun_dec)
        # Contra-parallel: bodies at opposite declinations (e.g., +18° and -18°)
        # Check if planet and natal have opposite signs and similar magnitudes
        contra_diff = abs(abs(planet_declination) - abs(natal_sun_dec))
        is_opposite_sides = (planet_declination * natal_sun_dec) < 0  # Different signs
        
        if diff <= PARALLEL_ORB:
            # Parallel - harmonious, supportive
            declination_aspects["has_declination_aspect"] = True
            declination_aspects["aspects"].append({
                "type": "parallel",
                "to": "Sun",
                "orb": diff,
                "effect": "clarity_support",
                "bias": -0.3,  # Supportive
            })
            declination_aspects["total_bias"] -= 0.3
        
        elif is_opposite_sides and contra_diff <= PARALLEL_ORB:
            # Contra-parallel - tension, awareness
            declination_aspects["has_declination_aspect"] = True
            declination_aspects["aspects"].append({
                "type": "contra_parallel",
                "to": "Sun",
                "orb": contra_diff,
                "effect": "clarity_tension",
                "bias": 0.3,  # Minor friction
            })
            declination_aspects["total_bias"] += 0.3
    
    # Check parallel to natal Moon
    if natal_moon_dec is not None:
        diff = abs(planet_declination - natal_moon_dec)
        # Contra-parallel: bodies at opposite declinations
        contra_diff = abs(abs(planet_declination) - abs(natal_moon_dec))
        is_opposite_sides = (planet_declination * natal_moon_dec) < 0  # Different signs
        
        if diff <= PARALLEL_ORB:
            # Parallel - emotional attunement
            declination_aspects["has_declination_aspect"] = True
            declination_aspects["aspects"].append({
                "type": "parallel",
                "to": "Moon",
                "orb": diff,
                "effect": "mood_support",
                "bias": -0.3,  # Supportive
            })
            declination_aspects["total_bias"] -= 0.3
        
        elif is_opposite_sides and contra_diff <= PARALLEL_ORB:
            # Contra-parallel - emotional challenge
            declination_aspects["has_declination_aspect"] = True
            declination_aspects["aspects"].append({
                "type": "contra_parallel",
                "to": "Moon",
                "orb": contra_diff,
                "effect": "mood_tension",
                "bias": 0.3,  # Minor friction
            })
            declination_aspects["total_bias"] += 0.3
    
    return declination_aspects


# ============================================================================
# LUNAR CYCLE EVENTS (HIGH IMPACT, FREQUENT)
# ============================================================================

def detect_lunar_phase(
    moon_lon: float,
    sun_lon: float,
    forecast_datetime: datetime,
) -> Optional[Dict[str, Any]]:
    """
    Detect lunar phase and calculate its influence.
    
    Phases:
    - New Moon (0°): Fresh starts, new beginnings
    - First Quarter (90°): Action, decisions
    - Full Moon (180°): Culmination, tension/release
    - Last Quarter (270°): Review, adjustment
    
    Args:
        moon_lon: Moon longitude in degrees
        sun_lon: Sun longitude in degrees
        forecast_datetime: Current forecast date/time
        
    Returns:
        Lunar phase info dict or None
    """
    # Calculate Sun-Moon angle (Moon ahead of Sun, counterclockwise)
    # Don't use _angle_diff as it returns shortest distance
    angle = (moon_lon - sun_lon) % 360
    
    # Define phase thresholds and windows
    phases = {
        "new_moon": {
            "exact_angle": 0,
            "orb": 8,  # ±8° for detection
            "weight": 0.8,  # Can be positive or negative based on aspects
            "window_hours": 12,
            "description": "Fresh starts and new intentions",
            "keywords": ["beginning", "seed", "intention", "initiate"],
        },
        "first_quarter": {
            "exact_angle": 90,
            "orb": 6,
            "weight": 0.5,
            "window_hours": 6,
            "description": "Action moment - decisions and momentum",
            "keywords": ["action", "decision", "push", "momentum"],
        },
        "full_moon": {
            "exact_angle": 180,
            "orb": 8,
            "weight": 1.0,  # Will be adjusted based on natal aspects
            "window_hours": 12,
            "description": "Culmination and release",
            "keywords": ["culmination", "release", "harvest", "revelation"],
        },
        "last_quarter": {
            "exact_angle": 270,
            "orb": 6,
            "weight": 0.5,
            "window_hours": 6,
            "description": "Review and adjustment moment",
            "keywords": ["review", "adjust", "refine", "release"],
        },
    }
    
    # Find matching phase
    for phase_name, phase_data in phases.items():
        diff = abs(angle - phase_data["exact_angle"])
        if diff <= phase_data["orb"]:
            return {
                "has_lunar_phase": True,
                "phase_name": phase_name,
                "angle": angle,
                "orb_from_exact": diff,
                "base_weight": phase_data["weight"],
                "window_hours": phase_data["window_hours"],
                "description": phase_data["description"],
                "keywords": phase_data["keywords"],
            }
    
    return None


def calculate_lunar_phase_score(
    phase_info: Dict[str, Any],
    natal_aspects: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Calculate score modifier for lunar phase based on natal aspects.
    
    Full Moon gets +1.0 if squaring/opposing natal luminaries/angles,
    -0.6 if trine/sextile.
    
    Args:
        phase_info: Lunar phase info from detect_lunar_phase
        natal_aspects: Optional natal aspect information
        
    Returns:
        Score modifier
    """
    if not phase_info or not phase_info.get("has_lunar_phase"):
        return 0.0
    
    base_weight = phase_info["base_weight"]
    phase_name = phase_info["phase_name"]
    
    # If we have natal aspect information, adjust Full/New Moon weights
    if natal_aspects and phase_name in {"new_moon", "full_moon"}:
        aspect_type = natal_aspects.get("aspect_type")
        
        if aspect_type in {"square", "opposition"}:
            # Challenging aspects to luminaries/angles
            return base_weight * 1.25 if phase_name == "full_moon" else base_weight
        elif aspect_type in {"trine", "sextile"}:
            # Supportive aspects
            return -0.6  # Supportive influence
    
    # Default weights for First/Last Quarter
    return base_weight


def detect_void_of_course_moon(
    moon_lon: float,
    moon_speed: float,
    forecast_datetime: datetime,
    next_sign_ingress_time: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Detect Void-of-Course Moon periods.
    
    VoC Moon = Moon has made its last major aspect in current sign
    before changing signs. This is a "low-signal period" for execution.
    
    Effect: -0.3 to all "go/decide" suggestions; prefer "prep/review".
    
    Args:
        moon_lon: Moon longitude
        moon_speed: Moon speed (deg/day)
        forecast_datetime: Current time
        next_sign_ingress_time: When Moon enters next sign
        
    Returns:
        VoC Moon info or None
    """
    # Calculate Moon's current sign
    current_sign = int(moon_lon / 30)
    next_sign_boundary = (current_sign + 1) * 30
    
    # Calculate hours until sign change
    degrees_to_boundary = next_sign_boundary - moon_lon
    if degrees_to_boundary < 0:
        degrees_to_boundary += 360
    
    # Moon moves ~13°/day = ~0.54°/hour
    hours_to_boundary = (degrees_to_boundary / moon_speed) * 24
    
    # VoC typically lasts 0-48 hours
    # For simplicity, assume VoC if Moon is in last 3° of sign
    # (more sophisticated detection would require aspect calculation)
    is_voc = degrees_to_boundary <= 3.0 and hours_to_boundary <= 12
    
    if is_voc:
        return {
            "is_void_of_course": True,
            "hours_remaining": hours_to_boundary,
            "next_sign": current_sign + 1,
            "effect": "Low-signal period - favor preparation over execution",
            "score_modifier": -0.3,
            "recommended_activities": [
                "Review existing plans",
                "Organize and prepare",
                "Rest and reflect",
                "Avoid major launches or decisions",
            ],
        }
    
    return None


def detect_supermoon_micromoon(
    moon_distance_km: float,
    phase_info: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Detect Supermoon (perigee) or Micromoon (apogee) and amplify effects.
    
    Supermoon: Moon at perigee (~356,500 km)
    Micromoon: Moon at apogee (~406,700 km)
    
    Effect: Amplify/dampen Full/New Moon by ±10-15%
    
    Args:
        moon_distance_km: Moon's distance from Earth in km
        phase_info: Lunar phase info (to check if New/Full)
        
    Returns:
        Supermoon/Micromoon info or None
    """
    # Average distance: ~384,400 km
    # Perigee: ~356,500 km (92.7% of average)
    # Apogee: ~406,700 km (105.8% of average)
    
    AVG_DISTANCE = 384400
    PERIGEE_THRESHOLD = 360000  # Within 360,000 km
    APOGEE_THRESHOLD = 405000   # Beyond 405,000 km
    
    if moon_distance_km < PERIGEE_THRESHOLD:
        # Supermoon - amplify effects
        amplification = 1.15  # +15%
        type_name = "supermoon"
        description = "Enhanced lunar influence - emotions and events amplified"
    elif moon_distance_km > APOGEE_THRESHOLD:
        # Micromoon - dampen effects
        amplification = 0.90  # -10%
        type_name = "micromoon"
        description = "Subdued lunar influence - gentler energies"
    else:
        return None
    
    # Only significant if during New or Full Moon
    if phase_info and phase_info.get("phase_name") in {"new_moon", "full_moon"}:
        return {
            "has_special_moon": True,
            "type": type_name,
            "distance_km": moon_distance_km,
            "amplification_factor": amplification,
            "description": description,
        }
    
    return None


def detect_out_of_bounds_moon(
    moon_declination: float,
) -> Optional[Dict[str, Any]]:
    """
    Detect Out-of-Bounds Moon (declination > ~23.44°).
    
    Effect: Add volatility flag (+0.3 caution), highlight emotional spikes.
    
    Args:
        moon_declination: Moon's declination in degrees
        
    Returns:
        OOB Moon info or None
    """
    # Ecliptic obliquity: ~23.44°
    OBLIQUITY = 23.44
    
    abs_dec = abs(moon_declination)
    
    if abs_dec > OBLIQUITY:
        intensity = "moderate" if abs_dec <= 25 else "strong"
        return {
            "is_out_of_bounds": True,
            "declination": moon_declination,
            "intensity": intensity,
            "caution_modifier": 0.3,
            "description": "Heightened emotional volatility - stay grounded",
            "keywords": ["intense", "unpredictable", "emotional", "volatility"],
        }
    
    return None


# ============================================================================
# ECLIPSES (RARE, VERY HIGH IMPACT)
# ============================================================================

def detect_eclipse(
    moon_lon: float,
    sun_lon: float,
    moon_lat: float,  # Moon's ecliptic latitude
    forecast_datetime: datetime,
    natal_positions: Optional[Dict[str, float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Detect solar and lunar eclipses.
    
    Solar Eclipse: New Moon near nodes (lat ≤ ~1.5°)
    Lunar Eclipse: Full Moon near nodes (lat ≤ ~1.0°)
    
    Weights:
    - Lunar total: +2.0, partial: +1.2
    - Solar total/annular: +2.2, partial: +1.4
    
    Personalization: +20-40% if within 2° of natal Sun/Moon/ASC/MC
    
    Args:
        moon_lon: Moon longitude
        sun_lon: Sun longitude
        moon_lat: Moon's ecliptic latitude (distance from ecliptic)
        forecast_datetime: Current date/time
        natal_positions: Dict of natal positions {body: longitude}
        
    Returns:
        Eclipse info or None
    """
    from .aspects import _angle_diff
    
    # Calculate Sun-Moon angle
    angle = abs(_angle_diff(moon_lon, sun_lon))
    if angle > 180:
        angle = 360 - angle
    
    # Check if near New or Full Moon
    is_new = angle <= 10  # Within 10° of New Moon
    is_full = abs(angle - 180) <= 10  # Within 10° of Full Moon
    
    if not (is_new or is_full):
        return None
    
    # Check if Moon is near nodes (ecliptic latitude close to 0)
    abs_lat = abs(moon_lat)
    
    # Eclipse thresholds (simplified)
    SOLAR_ECLIPSE_LAT = 1.5  # Solar eclipse if lat ≤ 1.5°
    LUNAR_ECLIPSE_LAT = 1.0  # Lunar eclipse if lat ≤ 1.0°
    
    eclipse_info = None
    
    if is_new and abs_lat <= SOLAR_ECLIPSE_LAT:
        # Solar Eclipse
        if abs_lat <= 0.5:
            eclipse_type = "total/annular"
            base_weight = 2.2
        else:
            eclipse_type = "partial"
            base_weight = 1.4
        
        eclipse_info = {
            "has_eclipse": True,
            "eclipse_category": "solar",
            "eclipse_type": eclipse_type,
            "base_weight": base_weight,
            "description": f"Solar Eclipse ({eclipse_type}) - major new chapter",
            "keywords": ["reset", "breakthrough", "new chapter", "fated shift"],
        }
    
    elif is_full and abs_lat <= LUNAR_ECLIPSE_LAT:
        # Lunar Eclipse
        if abs_lat <= 0.3:
            eclipse_type = "total"
            base_weight = 2.0
        else:
            eclipse_type = "partial"
            base_weight = 1.2
        
        eclipse_info = {
            "has_eclipse": True,
            "eclipse_category": "lunar",
            "eclipse_type": eclipse_type,
            "base_weight": base_weight,
            "description": f"Lunar Eclipse ({eclipse_type}) - culmination and release",
            "keywords": ["revelation", "culmination", "release", "transformation"],
        }
    
    if not eclipse_info:
        return None
    
    # Calculate personalization boost
    personalization_boost = 0.0
    if natal_positions:
        key_points = ["Sun", "Moon", "Ascendant", "Midheaven"]
        for point in key_points:
            if point in natal_positions:
                diff = abs(_angle_diff(moon_lon, natal_positions[point]))
                if diff <= 2.0:
                    # Eclipse within 2° of natal key point
                    # Tighter orb = stronger boost
                    boost_factor = 0.4 if diff <= 1.0 else 0.2
                    personalization_boost = max(personalization_boost, boost_factor)
    
    eclipse_info["personalization_boost"] = personalization_boost
    
    # Calculate window phases
    eclipse_info["windows"] = {
        "build": {"hours": -12, "description": "Energy building"},
        "peak": {"hours": 2, "description": "Maximum intensity"},
        "settle": {"hours": 6, "description": "Integration period"},
    }
    
    return eclipse_info


def calculate_eclipse_score(
    eclipse_info: Dict[str, Any],
) -> float:
    """
    Calculate total score modifier for eclipse.
    
    Args:
        eclipse_info: Eclipse info from detect_eclipse
        
    Returns:
        Total score modifier
    """
    if not eclipse_info or not eclipse_info.get("has_eclipse"):
        return 0.0
    
    base_weight = eclipse_info["base_weight"]
    personalization_boost = eclipse_info.get("personalization_boost", 0.0)
    
    # Apply personalization boost (20-40% increase)
    total_score = base_weight * (1 + personalization_boost)
    
    return total_score

