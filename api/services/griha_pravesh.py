"""Griha Pravesh (Housewarming) Muhurat Calculation.

This module calculates auspicious timings for Griha Pravesh ceremonies based on
Vedic astrology principles, considering Tithi, Nakshatra, Yoga, Karana, and Lagna.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from zoneinfo import ZoneInfo
import swisseph as swe

from . import ephem
from .panchang_algos import (
    compute_tithi,
    compute_nakshatra,
    compute_yoga,
)
from .muhurta import compute_muhurta_blocks


# Auspicious elements for Griha Pravesh
FAVORABLE_TITHIS = [2, 3, 5, 7, 10, 11, 12, 13]  # Shukla Paksha (waxing moon)
AVOID_TITHIS = [4, 6, 8, 9, 14, 15, 29, 30]  # Inauspicious Tithis

FAVORABLE_NAKSHATRAS = [
    1,   # Ashwini
    4,   # Rohini
    5,   # Mrigashira
    7,   # Punarvasu
    8,   # Pushya
    12,  # Uttara Phalguni
    13,  # Hasta
    14,  # Chitra
    15,  # Swati
    17,  # Anuradha
    21,  # Uttara Ashadha
    22,  # Shravana
    23,  # Dhanishta
    26,  # Uttara Bhadrapada
    27,  # Revati
]

AVOID_NAKSHATRAS = [
    3,   # Ardra
    6,   # Ashlesha
    9,   # Magha
    16,  # Vishakha
    18,  # Jyeshtha
    19,  # Mula
]

FAVORABLE_YOGAS = [
    1,   # Vishkambha
    2,   # Preeti
    3,   # Ayushman
    4,   # Saubhagya
    7,   # Shobhana
    8,   # Shukla
    9,   # Brahma
    10,  # Indra
    11,  # Vaidhriti
    16,  # Siddhi
]

AVOID_YOGAS = [
    6,   # Vajra
    14,  # Vyaghata
    15,  # Harshana
    17,  # Vyatipata
    22,  # Shula
    23,  # Ganda
    24,  # Vriddhi
    27,  # Parigha
]

BHADRA_KARANA = 7  # Vishti/Bhadra - most inauspicious

FAVORABLE_WEEKDAYS = [0, 1, 3, 4, 5]  # Sunday, Monday, Wednesday, Thursday, Friday
AVOID_WEEKDAYS = [2, 6]  # Tuesday, Saturday

FAVORABLE_LAGNAS = [
    "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
    "Libra", "Sagittarius", "Aquarius", "Pisces"
]

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


def _get_karana_number(moon_sun_diff: float) -> int:
    """Calculate Karana number (1-60) from Moon-Sun difference."""
    # Karana is half of Tithi (6 degrees each)
    karana_index = int(moon_sun_diff / 6.0)
    
    # First 7 Karanas repeat 8 times (1-56)
    # Last 4 Karanas (Shakuni, Chatushpada, Naga, Kimstughna) occur once (57-60)
    if karana_index < 57:
        return (karana_index % 7) + 1
    else:
        return karana_index - 49  # Maps 57-60 to special Karanas 8-11


def _get_ascendant(jd: float, lat: float, lon: float) -> Tuple[str, float]:
    """Calculate the ascendant (Lagna) for a given Julian Day and location."""
    try:
        houses = swe.houses(jd, lat, lon, b"P")  # Placidus house system
        asc_lon = houses[1][0]  # Ascendant longitude
        sign_index = int(asc_lon / 30)
        sign_name = SIGN_NAMES[sign_index]
        return sign_name, asc_lon
    except Exception:
        return "Unknown", 0.0


def _calculate_karana_for_time(dt: datetime, ayanamsha: str = "lahiri") -> int:
    """Calculate Karana number for a specific datetime."""
    jd = dt.timestamp() / 86400.0 + 2440587.5
    
    # Get ecliptic positions
    positions = ephem.positions_ecliptic(jd, sidereal=True, ayanamsha=ayanamsha)
    moon_lon = positions["Moon"]["lon"]
    sun_lon = positions["Sun"]["lon"]
    
    # Calculate Moon-Sun difference
    diff = (moon_lon - sun_lon) % 360.0
    
    return _get_karana_number(diff)


def _is_bhadra_karana(karana_num: int) -> bool:
    """Check if the Karana is Bhadra (Vishti) - inauspicious."""
    return karana_num == BHADRA_KARANA


def calculate_griha_pravesh_muhurat(
    date: datetime,
    lat: float,
    lon: float,
    tz: ZoneInfo,
    sunrise: datetime,
    sunset: datetime,
    tithi_number: int,
    nakshatra_number: int,
    yoga_number: int,
    weekday_index: int,
    ayanamsha: str = "lahiri",
    tithi_name: str = "",
    nakshatra_name: str = "",
    yoga_name: str = "",
    weekday_name: str = "",
) -> Dict[str, Any]:
    """
    Calculate Griha Pravesh muhurat for a given date.
    
    Considers all traditional factors including:
    - Tithi (Lunar day) - favorable and avoid lists
    - Nakshatra (Lunar mansion) - auspicious nakshatras
    - Yoga (Nitya Yoga) - favorable yogas
    - Weekday - suitable days for home-related activities
    - Lagna (Ascendant) - favorable rising signs
    - Karana - avoids Bhadra/Vishti
    - Inauspicious periods - filters out Rahu Kalam, Gulika Kalam, and Yamaganda
    
    Returns a dictionary with:
    - overall_rating: "excellent", "good", "fair", "poor", "avoid"
    - favorable_windows: List of time windows suitable for ceremony (all inauspicious periods filtered)
    - factors: Breakdown of each astrological factor
    - recommendations: Textual recommendations
    """
    
    # Evaluate each factor
    tithi_score = _evaluate_tithi(tithi_number)
    nakshatra_score = _evaluate_nakshatra(nakshatra_number)
    yoga_score = _evaluate_yoga(yoga_number)
    weekday_score = _evaluate_weekday(weekday_index)
    
    # Find favorable time windows (consider Lagna and Karana)
    favorable_windows = _find_favorable_windows(
        date, lat, lon, tz, sunrise, sunset, ayanamsha
    )
    
    # Calculate overall rating
    overall_score = tithi_score + nakshatra_score + yoga_score + weekday_score
    overall_rating = _calculate_overall_rating(overall_score, favorable_windows)
    
    # Generate recommendations
    recommendations = _generate_recommendations(
        tithi_score, nakshatra_score, yoga_score, weekday_score,
        favorable_windows, tithi_number, nakshatra_number, yoga_number
    )
    
    return {
        "overall_rating": overall_rating,
        "overall_score": overall_score,
        "favorable_windows": favorable_windows,
        "factors": {
            "tithi": {
                "number": tithi_number,
                "name": tithi_name,
                "score": tithi_score,
                "assessment": _score_to_assessment(tithi_score),
            },
            "nakshatra": {
                "number": nakshatra_number,
                "name": nakshatra_name,
                "score": nakshatra_score,
                "assessment": _score_to_assessment(nakshatra_score),
            },
            "yoga": {
                "number": yoga_number,
                "name": yoga_name,
                "score": yoga_score,
                "assessment": _score_to_assessment(yoga_score),
            },
            "weekday": {
                "index": weekday_index,
                "name": weekday_name,
                "score": weekday_score,
                "assessment": _score_to_assessment(weekday_score),
            },
        },
        "recommendations": recommendations,
    }


def _evaluate_tithi(tithi_number: int) -> int:
    """Evaluate Tithi favorability. Returns score: 3=excellent, 2=good, 1=ok, 0=avoid, -1=highly avoid."""
    if tithi_number in AVOID_TITHIS:
        return -1
    elif tithi_number in FAVORABLE_TITHIS:
        if tithi_number in [2, 3, 5, 10, 11, 13]:  # Best Tithis
            return 3
        else:
            return 2
    else:
        return 1


def _evaluate_nakshatra(nakshatra_number: int) -> int:
    """Evaluate Nakshatra favorability."""
    if nakshatra_number in AVOID_NAKSHATRAS:
        return -1
    elif nakshatra_number in FAVORABLE_NAKSHATRAS:
        if nakshatra_number in [8, 22, 26]:  # Pushya, Shravana, Uttara Bhadrapada - best
            return 3
        else:
            return 2
    else:
        return 1


def _evaluate_yoga(yoga_number: int) -> int:
    """Evaluate Yoga favorability."""
    if yoga_number in AVOID_YOGAS:
        return -1
    elif yoga_number in FAVORABLE_YOGAS:
        if yoga_number in [16, 2, 3]:  # Siddhi, Preeti, Ayushman - best
            return 3
        else:
            return 2
    else:
        return 1


def _evaluate_weekday(weekday_index: int) -> int:
    """Evaluate weekday favorability."""
    if weekday_index in AVOID_WEEKDAYS:
        return 0
    elif weekday_index in FAVORABLE_WEEKDAYS:
        if weekday_index in [0, 4]:  # Sunday, Thursday - best
            return 2
        else:
            return 1
    else:
        return 1


def _time_overlaps_with_period(
    check_start: datetime,
    check_end: datetime,
    period_start: datetime,
    period_end: datetime,
) -> bool:
    """Check if a time range overlaps with an inauspicious period."""
    # Periods overlap if one starts before the other ends
    return check_start < period_end and check_end > period_start


def _is_in_inauspicious_period(
    check_start: datetime,
    check_end: datetime,
    muhurta_blocks: Dict[str, Tuple[datetime, datetime]],
) -> Tuple[bool, Optional[str]]:
    """
    Check if a time window falls within any inauspicious period.
    
    Returns:
        Tuple of (is_inauspicious, reason)
    """
    # Check Rahu Kalam
    rahu_start, rahu_end = muhurta_blocks["rahu_kal"]
    if _time_overlaps_with_period(check_start, check_end, rahu_start, rahu_end):
        return True, "Rahu Kalam"
    
    # Check Gulika Kalam
    gulika_start, gulika_end = muhurta_blocks["gulika_kal"]
    if _time_overlaps_with_period(check_start, check_end, gulika_start, gulika_end):
        return True, "Gulika Kalam"
    
    # Check Yamaganda
    yamaganda_start, yamaganda_end = muhurta_blocks["yamaganda"]
    if _time_overlaps_with_period(check_start, check_end, yamaganda_start, yamaganda_end):
        return True, "Yamaganda"
    
    return False, None


def _find_favorable_windows(
    date: datetime,
    lat: float,
    lon: float,
    tz: ZoneInfo,
    sunrise: datetime,
    sunset: datetime,
    ayanamsha: str,
) -> List[Dict[str, Any]]:
    """
    Find favorable time windows during the day considering Lagna, Karana, 
    and inauspicious periods (Rahu Kalam, Gulika Kalam, Yamaganda).
    Checks hourly from sunrise to sunset.
    """
    windows = []
    
    # Calculate inauspicious time blocks for the day
    weekday_name = sunrise.strftime("%A")
    muhurta_blocks = compute_muhurta_blocks(sunrise, sunset, weekday_name)
    
    # Check every hour from sunrise to sunset
    current = sunrise
    while current < sunset:
        # Calculate for this hour
        jd = current.astimezone(tz).timestamp() / 86400.0 + 2440587.5
        window_end = min(current + timedelta(hours=1), sunset)
        
        # Get Lagna
        lagna_sign, lagna_lon = _get_ascendant(jd, lat, lon)
        
        # Get Karana
        karana_num = _calculate_karana_for_time(current.astimezone(tz), ayanamsha)
        is_bhadra = _is_bhadra_karana(karana_num)
        
        # Check if this hour is favorable
        is_favorable_lagna = lagna_sign in FAVORABLE_LAGNAS
        
        # Check for inauspicious periods (Rahu Kalam, Gulika, Yamaganda)
        is_inauspicious, inauspicious_reason = _is_in_inauspicious_period(
            current, window_end, muhurta_blocks
        )
        
        # Only add window if ALL conditions are favorable
        if is_favorable_lagna and not is_bhadra and not is_inauspicious:
            # This is a good window
            # Calculate quality rating
            quality = "excellent" if lagna_sign in ["Cancer", "Taurus", "Leo"] else "good"
            
            windows.append({
                "start_ts": current.isoformat(),
                "end_ts": window_end.isoformat(),
                "lagna": lagna_sign,
                "karana_number": karana_num,
                "quality": quality,
            })
        
        current += timedelta(hours=1)
    
    return windows


def _calculate_overall_rating(score: int, windows: List[Dict[str, Any]]) -> str:
    """Calculate overall rating based on score and available windows."""
    if score < 0 or len(windows) == 0:
        return "avoid"
    elif score >= 10 and len(windows) >= 3:
        return "excellent"
    elif score >= 7 and len(windows) >= 2:
        return "good"
    elif score >= 4 and len(windows) >= 1:
        return "fair"
    elif len(windows) >= 1:
        return "fair"
    else:
        return "poor"


def _score_to_assessment(score: int) -> str:
    """Convert numeric score to textual assessment."""
    if score == 3:
        return "excellent"
    elif score == 2:
        return "good"
    elif score == 1:
        return "ok"
    elif score == 0:
        return "neutral"
    else:
        return "avoid"


def _generate_recommendations(
    tithi_score: int,
    nakshatra_score: int,
    yoga_score: int,
    weekday_score: int,
    windows: List[Dict[str, Any]],
    tithi_num: int,
    nakshatra_num: int,
    yoga_num: int,
) -> List[str]:
    """Generate human-readable recommendations."""
    recommendations = []
    
    # Overall assessment
    if tithi_score < 0 or nakshatra_score < 0 or yoga_score < 0:
        recommendations.append("⚠️ This date has inauspicious factors. Consider choosing another date.")
    elif len(windows) == 0:
        recommendations.append(
            "⚠️ No favorable time windows available. Filtered out periods include: "
            "Rahu Kalam, Gulika Kalam, Yamaganda, Bhadra Karana, and unfavorable Lagna."
        )
    elif tithi_score >= 2 and nakshatra_score >= 2 and yoga_score >= 2 and len(windows) >= 2:
        recommendations.append("✅ This is an excellent date for Griha Pravesh ceremony!")
        recommendations.append("ℹ️ All recommended times avoid Rahu Kalam and other inauspicious periods.")
    elif len(windows) >= 1:
        recommendations.append("✓ This date is suitable for Griha Pravesh with careful timing.")
        recommendations.append("ℹ️ Recommended times avoid Rahu Kalam, Gulika Kalam, and Yamaganda.")
    
    # Specific recommendations for each factor
    if tithi_score < 0:
        recommendations.append(f"❌ Tithi {tithi_num} is inauspicious for new beginnings.")
    elif tithi_score >= 3:
        recommendations.append(f"✅ Tithi {tithi_num} is highly favorable for Griha Pravesh.")
    
    if nakshatra_score < 0:
        recommendations.append(f"❌ Nakshatra {nakshatra_num} is not recommended for permanent activities.")
    elif nakshatra_score >= 3:
        recommendations.append(f"✅ Nakshatra {nakshatra_num} is one of the best for home-related ceremonies.")
    
    if yoga_score < 0:
        recommendations.append(f"❌ Yoga {yoga_num} brings inauspicious influences.")
    elif yoga_score >= 3:
        recommendations.append(f"✅ Yoga {yoga_num} brings success and accomplishment.")
    
    # Time window recommendations
    if len(windows) > 0:
        best_window = windows[0]
        start_time = datetime.fromisoformat(best_window["start_ts"])
        recommendations.append(
            f"🕐 Best time window: {start_time.strftime('%I:%M %p')} "
            f"(Lagna: {best_window['lagna']})"
        )
    
    return recommendations

