"""Comprehensive Daily Ephemeris Generator.

This module generates detailed daily ephemeris data for an entire year,
including planetary positions, aspects, houses, lunar phases, eclipses,
ingresses, retrograde stations, and Vedic elements.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

import swisseph as swe

from . import ephem
from . import houses as houses_svc
from . import aspects as aspects_svc
from .panchang_algos import (
    compute_tithi,
    compute_nakshatra,
    compute_yoga,
    TITHI_NAMES,
    NAKSHATRA_NAMES,
    YOGA_NAMES,
    MOBILE_KARANAS,
    FIXED_KARANAS,
)


# Extended body list including asteroids
EXTENDED_BODIES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "TrueNode": swe.TRUE_NODE,  # Rahu
    "MeanNode": swe.MEAN_NODE,
    "Chiron": swe.CHIRON,
}

# Asteroids
ASTEROIDS = {
    "Ceres": swe.CERES,
    "Pallas": swe.PALLAS,
    "Juno": swe.JUNO,
    "Vesta": swe.VESTA,
}

# Mean Lilith (Black Moon)
LILITH_CODE = swe.MEAN_APOG

# Zodiac signs
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Aspect definitions with orb tolerances
ASPECTS_CONFIG = {
    "conjunction": {"angle": 0, "symbol": "☌"},
    "opposition": {"angle": 180, "symbol": "☍"},
    "trine": {"angle": 120, "symbol": "△"},
    "square": {"angle": 90, "symbol": "□"},
    "sextile": {"angle": 60, "symbol": "⚹"},
}

# Orb tolerances by planet type
ORB_TOLERANCES = {
    "Sun": 10.0,
    "Moon": 10.0,
    "Mercury": 8.0,
    "Venus": 8.0,
    "Mars": 8.0,
    "Jupiter": 8.0,
    "Saturn": 8.0,
    "Uranus": 10.0,
    "Neptune": 10.0,
    "Pluto": 10.0,
    "Rahu": 8.0,
    "Ketu": 6.0,
    "Lilith": 10.0,
    "Chiron": 6.0,
    "Ceres": 6.0,
    "Pallas": 6.0,
    "Juno": 6.0,
    "Vesta": 6.0,
    "Hygiea": 6.0,
}


def _get_sign_name(longitude: float) -> str:
    """Get zodiac sign name from ecliptic longitude."""
    sign_index = int(longitude / 30) % 12
    return ZODIAC_SIGNS[sign_index]


def _degree_in_sign(longitude: float) -> float:
    """Get degree within sign (0-30)."""
    return longitude % 30


def _to_dms(longitude: float) -> Dict[str, Any]:
    """Convert decimal degrees to degrees, minutes, seconds."""
    degrees = int(longitude)
    minutes_decimal = (longitude - degrees) * 60
    minutes = int(minutes_decimal)
    seconds = (minutes_decimal - minutes) * 60
    sign_num = 1  # Always 1 for tropical
    
    return {
        "degrees": degrees,
        "minutes": minutes,
        "seconds": round(seconds, 2),
        "sign": sign_num
    }


def _calculate_planet_positions(jd: float, lat: float, lon: float, 
                                 sidereal: bool = False, 
                                 ayanamsha: str = "lahiri") -> Dict[str, Dict[str, Any]]:
    """Calculate all planetary and asteroid positions for a given date."""
    
    flag = swe.FLG_SWIEPH | swe.FLG_SPEED
    if sidereal:
        mode = ephem.AYANAMSHA_MAP.get(ayanamsha.lower(), swe.SIDM_LAHIRI)
        swe.set_sid_mode(mode)
        flag |= swe.FLG_SIDEREAL
    
    positions = {}
    
    # Main planets
    for name, code in EXTENDED_BODIES.items():
        try:
            # Use topocentric for Moon, Mercury, Venus (closer bodies)
            body_flag = flag
            if name in ["Moon", "Mercury", "Venus"]:
                body_flag |= swe.FLG_TOPOCTR
                swe.set_topo(lon, lat, 0)  # Set observer location
            
            values, _ = swe.calc_ut(jd, code, body_flag)
            longitude, latitude, distance, speed_lon, speed_lat, speed_dist = values
            
            longitude = longitude % 360.0
            is_retrograde = speed_lon < 0
            
            planet_data = {
                "longitude": round(longitude, 4),
                "latitude": round(latitude, 4),
                "distance": round(distance, 4),
                "speed": round(speed_lon, 4),
                "zodiac_sign": _get_sign_name(longitude),
                "degree_in_sign": round(_degree_in_sign(longitude), 4),
                "is_retrograde": is_retrograde,
                "dms": _to_dms(longitude),
                "calculation_type": "topocentric" if name in ["Moon", "Mercury", "Venus"] else "geocentric"
            }
            
            # Add nakshatra for Moon
            if name == "Moon":
                try:
                    from datetime import timezone as tz
                    dt = swe.revjul(jd, swe.GREG_CAL)
                    moment = datetime(dt[0], dt[1], dt[2], int(dt[3]), int((dt[3]%1)*60), int(((dt[3]%1)*60%1)*60), tzinfo=tz.utc)
                    nak_num, nak_name, nak_pada, nak_start, nak_end = compute_nakshatra(moment, ayanamsha=ayanamsha)
                    
                    # Calculate degree in nakshatra (0-13.333...)
                    nak_span = 360.0 / 27.0  # 13.333... degrees per nakshatra
                    nak_lon_start = (nak_num - 1) * nak_span
                    degree_in_nak = (longitude - nak_lon_start) % nak_span
                    
                    planet_data["nakshatra"] = nak_name
                    planet_data["nakshatra_pada"] = nak_pada
                    planet_data["degree_in_nakshatra"] = round(degree_in_nak, 4)
                except Exception as e:
                    print(f"Error calculating nakshatra: {e}")
            
            # Map TrueNode to Rahu
            display_name = "Rahu" if name == "TrueNode" else name
            positions[display_name] = planet_data
            
        except Exception as e:
            print(f"Error calculating {name}: {e}")
            continue
    
    # Calculate Ketu (opposite of Rahu)
    if "Rahu" in positions:
        rahu_lon = positions["Rahu"]["longitude"]
        ketu_lon = (rahu_lon + 180) % 360.0
        positions["Ketu"] = {
            "longitude": round(ketu_lon, 4),
            "latitude": 0.0,
            "distance": positions["Rahu"]["distance"],
            "speed": round(positions["Rahu"]["speed"], 4),
            "zodiac_sign": _get_sign_name(ketu_lon),
            "degree_in_sign": round(_degree_in_sign(ketu_lon), 4),
            "is_retrograde": True,  # Always retrograde
            "dms": _to_dms(ketu_lon),
        }
    
    # Calculate Lilith (Mean Black Moon)
    try:
        values, _ = swe.calc_ut(jd, LILITH_CODE, flag)
        longitude, latitude, distance, speed_lon, _, _ = values
        longitude = longitude % 360.0
        
        positions["Lilith"] = {
            "longitude": round(longitude, 4),
            "latitude": round(latitude, 4),
            "distance": round(distance, 4),
            "speed": round(speed_lon, 4),
            "zodiac_sign": _get_sign_name(longitude),
            "degree_in_sign": round(_degree_in_sign(longitude), 4),
            "is_retrograde": speed_lon < 0,
            "dms": _to_dms(longitude),
            "calculation_type": "geocentric"
        }
    except Exception as e:
        print(f"Error calculating Lilith: {e}")
    
    # Asteroids
    asteroids = {}
    for name, code in ASTEROIDS.items():
        try:
            values, _ = swe.calc_ut(jd, code, flag)
            longitude, latitude, distance, speed_lon, _, _ = values
            longitude = longitude % 360.0
            
            asteroids[name] = {
                "longitude": round(longitude, 4),
                "latitude": round(latitude, 4),
                "distance": round(distance, 4),
                "speed": round(speed_lon, 4),
                "zodiac_sign": _get_sign_name(longitude),
                "degree_in_sign": round(_degree_in_sign(longitude), 4),
                "is_retrograde": speed_lon < 0,
                "dms": _to_dms(longitude),
                "calculation_type": "geocentric"
            }
        except Exception as e:
            print(f"Error calculating asteroid {name}: {e}")
    
    # Try to get Hygiea (asteroid 10)
    try:
        values, _ = swe.calc_ut(jd, 10, flag)
        longitude, latitude, distance, speed_lon, _, _ = values
        longitude = longitude % 360.0
        
        asteroids["Hygiea"] = {
            "longitude": round(longitude, 4),
            "latitude": round(latitude, 4),
            "distance": round(distance, 4),
            "speed": round(speed_lon, 4),
            "zodiac_sign": _get_sign_name(longitude),
            "degree_in_sign": round(_degree_in_sign(longitude), 4),
            "is_retrograde": speed_lon < 0,
            "dms": _to_dms(longitude),
            "calculation_type": "geocentric"
        }
    except Exception:
        pass
    
    return positions, asteroids


def _calculate_houses(jd: float, lat: float, lon: float) -> Dict[str, Any]:
    """Calculate house cusps and angles."""
    
    try:
        # Placidus houses
        cusps, ascmc = swe.houses(jd, lat, lon, b"P")
        
        house_data = {
            "Placidus": {
                "cusps": [round(cusps[i] % 360.0, 4) for i in range(12)],
                "ascendant": round(ascmc[0] % 360.0, 4),
                "mc": round(ascmc[1] % 360.0, 4),
                "armc": round(ascmc[2] % 360.0, 4),
                "vertex": round(ascmc[3] % 360.0, 4),
            }
        }
        
        return house_data
    except Exception as e:
        print(f"Error calculating houses: {e}")
        return {}


def _angle_diff(a: float, b: float) -> float:
    """Calculate the minimum angular distance between two longitudes."""
    diff = abs(a - b)
    if diff > 180:
        diff = 360 - diff
    return diff


def _calculate_aspects(planets: Dict[str, Dict[str, Any]], 
                       asteroids: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate all aspects between celestial bodies."""
    
    all_bodies = {**planets, **asteroids}
    aspects = []
    
    body_names = list(all_bodies.keys())
    
    for i in range(len(body_names)):
        for j in range(i + 1, len(body_names)):
            planet1 = body_names[i]
            planet2 = body_names[j]
            
            lon1 = all_bodies[planet1]["longitude"]
            lon2 = all_bodies[planet2]["longitude"]
            
            angle_between = _angle_diff(lon1, lon2)
            
            # Check each aspect type
            for aspect_name, aspect_info in ASPECTS_CONFIG.items():
                target_angle = aspect_info["angle"]
                orb = abs(angle_between - target_angle)
                
                # Get orb tolerance (use larger of the two planets)
                orb_tolerance = max(
                    ORB_TOLERANCES.get(planet1, 6.0),
                    ORB_TOLERANCES.get(planet2, 6.0)
                )
                
                if orb <= orb_tolerance:
                    # Calculate exact angle
                    exact_angle = abs(lon1 - lon2)
                    if exact_angle > 180:
                        exact_angle = 360 - exact_angle
                    
                    aspects.append({
                        "planet1": planet1,
                        "planet2": planet2,
                        "aspect": aspect_name.capitalize(),
                        "angle": target_angle,
                        "orb": round(orb, 2),
                        "exact_angle": round(exact_angle, 2),
                        "orb_tolerance": orb_tolerance
                    })
    
    return sorted(aspects, key=lambda x: (x["planet1"], x["planet2"]))


def _calculate_lunar_phase(sun_lon: float, moon_lon: float) -> Dict[str, Any]:
    """Calculate lunar phase information."""
    
    # Calculate angle difference
    angle = (moon_lon - sun_lon) % 360.0
    
    # Determine phase
    if angle < 45:
        phase_name = "New Moon"
    elif angle < 90:
        phase_name = "Waxing Crescent"
    elif angle < 135:
        phase_name = "First Quarter"
    elif angle < 180:
        phase_name = "Waxing Gibbous"
    elif angle < 225:
        phase_name = "Full Moon"
    elif angle < 270:
        phase_name = "Waning Gibbous"
    elif angle < 315:
        phase_name = "Last Quarter"
    else:
        phase_name = "Waning Crescent"
    
    # Calculate illumination (approximate)
    illumination = 50 * (1 - math.cos(math.radians(angle)))
    
    return {
        "phase": phase_name,
        "angle": round(angle, 2),
        "illumination": round(illumination, 1)
    }


def _calculate_tithi_info(jd: float) -> Dict[str, Any]:
    """Calculate Tithi information."""
    
    # Convert JD to datetime for compute_tithi
    from datetime import timezone
    dt = swe.revjul(jd, swe.GREG_CAL)
    moment = datetime(dt[0], dt[1], dt[2], int(dt[3]), int((dt[3]%1)*60), int(((dt[3]%1)*60%1)*60), tzinfo=timezone.utc)
    
    try:
        tithi_num, tithi_name, tithi_start, tithi_end = compute_tithi(moment, ayanamsha="lahiri")
    except Exception as e:
        print(f"Error calculating tithi: {e}")
        return {}
    
    # Calculate angle from Moon-Sun difference
    positions = ephem.positions_ecliptic(jd, sidereal=True, ayanamsha="lahiri")
    moon_lon = positions.get("Moon", {}).get("lon", 0)
    sun_lon = positions.get("Sun", {}).get("lon", 0)
    angle = (moon_lon - sun_lon) % 360.0
    
    # Determine paksha
    if tithi_num <= 15:
        paksha = "Shukla"
    else:
        paksha = "Krishna"
    
    # Extract just the day name (e.g., "Panchami" from "Shukla Panchami")
    day_name = tithi_name.split()[-1] if " " in tithi_name else tithi_name
    
    return {
        "number": tithi_num,
        "name": day_name,
        "paksha": paksha,
        "angle": round(angle, 2),
        "festivals": [],
        "is_special_day": False
    }


def _calculate_yoga(jd: float) -> str:
    """Calculate Nitya Yoga."""
    
    # Convert JD to datetime
    from datetime import timezone
    dt = swe.revjul(jd, swe.GREG_CAL)
    moment = datetime(dt[0], dt[1], dt[2], int(dt[3]), int((dt[3]%1)*60), int(((dt[3]%1)*60%1)*60), tzinfo=timezone.utc)
    
    try:
        yoga_num, yoga_name, yoga_start, yoga_end = compute_yoga(moment, ayanamsha="lahiri")
        return yoga_name
    except Exception as e:
        print(f"Error calculating yoga: {e}")
        return "Unknown"


def _calculate_karana(jd: float) -> str:
    """Calculate Karana."""
    
    # Get positions
    positions = ephem.positions_ecliptic(jd, sidereal=True, ayanamsha="lahiri")
    moon_lon = positions.get("Moon", {}).get("lon", 0)
    sun_lon = positions.get("Sun", {}).get("lon", 0)
    
    # Calculate Moon-Sun difference
    diff = (moon_lon - sun_lon) % 360.0
    
    # Karana is half of Tithi (6 degrees each)
    karana_index = int(diff / 6.0)
    
    # First 7 Karanas repeat 8 times (0-55)
    # Last 4 Karanas occur once (56-59)
    if karana_index < 57:
        karana_num = karana_index % 7
        return MOBILE_KARANAS[karana_num]
    else:
        fixed_index = min(karana_index - 57, 3)
        return FIXED_KARANAS[fixed_index]


def _detect_ingresses(prev_positions: Dict[str, Dict[str, Any]], 
                      curr_positions: Dict[str, Dict[str, Any]],
                      date_str: str, jd: float) -> List[Dict[str, Any]]:
    """Detect sign changes (ingresses) between two days."""
    
    ingresses = []
    
    for planet_name in curr_positions.keys():
        if planet_name not in prev_positions:
            continue
        
        prev_sign = prev_positions[planet_name].get("zodiac_sign")
        curr_sign = curr_positions[planet_name].get("zodiac_sign")
        
        if prev_sign and curr_sign and prev_sign != curr_sign:
            # Estimate time of ingress (simplified - middle of day)
            ingress_jd = jd - 0.25  # Approximate
            
            dt = swe.revjul(ingress_jd, swe.GREG_CAL)
            time_utc = f"{int(dt[3]):02d}:{int((dt[3]%1)*60):02d}:{int(((dt[3]%1)*60%1)*60):02d}"
            
            ingresses.append({
                "julian_day": round(ingress_jd, 9),
                "date": date_str,
                "time": {
                    "utc": time_utc,
                    "utc_iso": f"{date_str}T{time_utc}",
                    "utc_date": date_str,
                    "utc_full": f"{date_str} {time_utc} UTC"
                },
                "new_sign": curr_sign,
                "planet": planet_name
            })
    
    return ingresses


def _detect_retrograde_stations(prev_positions: Dict[str, Dict[str, Any]], 
                                 curr_positions: Dict[str, Dict[str, Any]],
                                 date_str: str, jd: float) -> List[Dict[str, Any]]:
    """Detect retrograde stations (direct to retrograde or vice versa)."""
    
    stations = []
    
    # Only check outer planets that can go retrograde
    check_planets = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    
    for planet_name in check_planets:
        if planet_name not in prev_positions or planet_name not in curr_positions:
            continue
        
        prev_retro = prev_positions[planet_name].get("is_retrograde", False)
        curr_retro = curr_positions[planet_name].get("is_retrograde", False)
        
        if prev_retro != curr_retro:
            station_type = "retrograde" if curr_retro else "direct"
            
            # Estimate time (simplified)
            station_jd = jd - 0.25
            dt = swe.revjul(station_jd, swe.GREG_CAL)
            time_utc = f"{int(dt[3]):02d}:{int((dt[3]%1)*60):02d}:{int(((dt[3]%1)*60%1)*60):02d}"
            
            stations.append({
                "julian_day": round(station_jd, 9),
                "date": date_str,
                "time": {
                    "utc": time_utc,
                    "utc_iso": f"{date_str}T{time_utc}",
                    "utc_date": date_str,
                    "utc_full": f"{date_str} {time_utc} UTC"
                },
                "planet": planet_name,
                "station_type": station_type
            })
    
    return stations


import math


def generate_daily_ephemeris(year: int, 
                             lat: float = 40.7128,  # Default: New York
                             lon: float = -74.0060,
                             output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate comprehensive daily ephemeris data for an entire year.
    
    Args:
        year: Target year (e.g., 2026)
        lat: Observer latitude
        lon: Observer longitude
        output_file: Optional path to save JSON output
    
    Returns:
        Dictionary with daily ephemeris data
    """
    
    print(f"Generating comprehensive ephemeris for year {year}...")
    print(f"Observer location: {lat}°, {lon}°")
    
    ephemeris_data = {}
    prev_positions = None
    
    # Generate for each day of the year
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    
    current_date = start_date
    day_count = 0
    
    while current_date <= end_date:
        day_count += 1
        date_str = current_date.strftime("%Y-%m-%d")
        
        if day_count % 30 == 0:
            print(f"  Processing day {day_count}/365: {date_str}")
        
        # Calculate Julian Day for noon UTC
        jd = swe.julday(current_date.year, current_date.month, current_date.day, 12.0, swe.GREG_CAL)
        
        # Get weekday
        weekday = current_date.strftime("%A")
        
        # Calculate all positions
        planets, asteroids = _calculate_planet_positions(jd, lat, lon)
        
        # Calculate houses
        houses = _calculate_houses(jd, lat, lon)
        
        # Calculate aspects
        aspects = _calculate_aspects(planets, asteroids)
        
        # Lunar phase
        sun_lon = planets.get("Sun", {}).get("longitude", 0)
        moon_lon = planets.get("Moon", {}).get("longitude", 0)
        lunar_phase = _calculate_lunar_phase(sun_lon, moon_lon)
        
        # Tithi
        tithi = _calculate_tithi_info(jd)
        
        # Yoga
        yoga = _calculate_yoga(jd)
        
        # Karana
        karana = _calculate_karana(jd)
        
        # Detect ingresses
        ingresses = []
        if prev_positions:
            ingresses = _detect_ingresses(prev_positions, planets, date_str, jd)
        
        # Detect retrograde stations
        retrograde_stations = []
        if prev_positions:
            retrograde_stations = _detect_retrograde_stations(prev_positions, planets, date_str, jd)
        
        # Build daily data
        day_data = {
            "julian_day": round(jd, 1),
            "weekday": weekday,
            "eclipse_window_active": False,  # TODO: Implement eclipse detection
            "planets": planets,
            "asteroids": asteroids,
            "houses": houses,
            "aspects": aspects,
            "lunar": {
                "phase": lunar_phase,
                "tithi": tithi,
                "yoga": yoga,
                "karana": karana
            },
            "eclipses": [],  # TODO: Implement eclipse detection
            "ingresses": ingresses,
            "retrograde_stations": retrograde_stations,
            "vedic_changes": {},  # TODO: Track tithi/yoga/karana changes during day
            "nakshatra_changes": []  # TODO: Track nakshatra changes during day
        }
        
        ephemeris_data[date_str] = day_data
        
        # Store for next iteration
        prev_positions = planets.copy()
        
        # Move to next day
        current_date += timedelta(days=1)
    
    print(f"✓ Generated ephemeris for {day_count} days")
    
    # Save to file if requested
    if output_file:
        print(f"Saving to {output_file}...")
        with open(output_file, 'w') as f:
            json.dump(ephemeris_data, f, indent=2)
        print(f"✓ Saved to {output_file}")
    
    return ephemeris_data


if __name__ == "__main__":
    import sys
    
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    output = sys.argv[2] if len(sys.argv) > 2 else f"ephemeris_{year}.json"
    
    generate_daily_ephemeris(year, output_file=output)

