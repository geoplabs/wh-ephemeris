"""Fast, free yearly forecast summary service (NO LLM calls)."""

import logging
import time
from datetime import datetime, date as Date
from typing import Any, Dict, List

from ..schemas.yearly_forecast_summary import (
    YearlyForecastSummaryResponse,
    YearlySummaryOverview,
    ChartSignature,
    KeyMonth,
    QuickLifeArea,
    KeyTransit,
)
from ..schemas.yearly_forecast_report import YearlyForecastRequest
from .yearly_forecast_report import compute_yearly_forecast

logger = logging.getLogger(__name__)


def _extract_chart_signature_from_meta(meta: Dict[str, Any]) -> ChartSignature:
    """Extract chart signature from raw_forecast meta (already calculated)."""
    try:
        natal_chart = meta.get("natal_chart", {})
        bodies = natal_chart.get("bodies", [])
        angles = natal_chart.get("angles", {})  # Dict with ascendant and mc longitudes
        
        sun = next((b for b in bodies if b.get("name") == "Sun"), None)
        moon = next((b for b in bodies if b.get("name") == "Moon"), None)
        
        # Get Ascendant sign from angles
        asc_lon = angles.get("ascendant")
        asc_sign = _lon_to_sign(asc_lon) if asc_lon is not None else "Unknown"
        
        return ChartSignature(
            sun_sign=sun.get("sign", "Unknown") if sun else "Unknown",
            sun_house=sun.get("house", 1) if sun else 1,
            moon_sign=moon.get("sign", "Unknown") if moon else "Unknown",
            moon_house=moon.get("house", 1) if moon else 1,
            ascendant_sign=asc_sign
        )
    except Exception as e:
        logger.error(f"Failed to extract from meta: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Fallback
        return ChartSignature(
            sun_sign="Unknown",
            sun_house=1,
            moon_sign="Unknown",
            moon_house=1,
            ascendant_sign="Unknown"
        )


def _lon_to_sign(lon: float) -> str:
    """Convert ecliptic longitude to zodiac sign."""
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    sign_num = int(lon / 30) % 12
    return signs[sign_num]


def _extract_chart_signature(chart_input: Dict[str, Any]) -> ChartSignature:
    """Extract core natal chart signature (fast, no LLM)."""
    from .orchestrators.natal_full import _compute_core
    import traceback
    
    try:
        natal = _compute_core(chart_input)
        bodies = natal.get("bodies", [])
        angles = natal.get("angles", {})  # Dict with ascendant and mc longitudes
        
        sun = next((b for b in bodies if b.get("name") == "Sun"), None)
        moon = next((b for b in bodies if b.get("name") == "Moon"), None)
        
        # Get Ascendant sign from angles
        asc_lon = angles.get("ascendant")
        asc_sign = _lon_to_sign(asc_lon) if asc_lon is not None else "Unknown"
        
        return ChartSignature(
            sun_sign=sun.get("sign", "Unknown") if sun else "Unknown",
            sun_house=sun.get("house", 1) if sun else 1,
            moon_sign=moon.get("sign", "Unknown") if moon else "Unknown",
            moon_house=moon.get("house", 1) if moon else 1,
            ascendant_sign=asc_sign
        )
    except Exception as e:
        logger.error(f"Failed to extract chart signature: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error(f"Chart input: {chart_input}")
        return ChartSignature(
            sun_sign="Unknown",
            sun_house=1,
            moon_sign="Unknown",
            moon_house=1,
            ascendant_sign="Unknown"
        )


def _generate_yearly_theme(
    chart_sig: ChartSignature,
    top_events: List[Dict],
    avg_score: float
) -> str:
    """Generate yearly theme using templates (fast, no LLM)."""
    
    # Analyze top events
    benefic_count = sum(1 for e in top_events[:10] if e.get("score", 0) > 0.5)
    challenging_count = sum(1 for e in top_events[:10] if e.get("score", 0) < -0.5)
    
    # Check for major themes
    has_jupiter = any("jupiter" in str(e.get("transit_body", "")).lower() for e in top_events[:5])
    has_saturn = any("saturn" in str(e.get("transit_body", "")).lower() for e in top_events[:5])
    has_eclipses = any("eclipse" in str(e.get("note", "")).lower() for e in top_events[:5])
    
    # Build theme based on patterns
    if avg_score >= 6.5:
        energy_phrase = "expansive and opportune"
    elif avg_score >= 5.5:
        energy_phrase = "balanced and progressive"
    else:
        energy_phrase = "introspective and transformative"
    
    # Add specific elements
    themes = []
    if has_jupiter:
        themes.append("growth and abundance")
    if has_saturn:
        themes.append("responsibility and structure")
    if has_eclipses:
        themes.append("significant life transitions")
    
    if not themes:
        themes.append("personal development")
    
    theme = f"This year brings {energy_phrase} energy with emphasis on {', '.join(themes[:2])}. "
    
    # Add Sun sign perspective
    theme += f"As a {chart_sig.sun_sign} Sun, you'll find opportunities to express your natural strengths."
    
    return theme


def _classify_life_area_outlook(events: List[Dict], keywords: List[str]) -> str:
    """Classify life area outlook based on events."""
    relevant_events = []
    for event in events:
        note = str(event.get("note", "")).lower()
        for keyword in keywords:
            if keyword in note:
                relevant_events.append(event)
                break
    
    if not relevant_events:
        return "mixed"
    
    avg_score = sum(e.get("score", 0) for e in relevant_events) / len(relevant_events)
    
    if avg_score > 0.5:
        return "favorable"
    elif avg_score < -0.5:
        return "challenging"
    else:
        return "mixed"


def _generate_life_area_one_liner(area: str, outlook: str, chart_sig: ChartSignature) -> str:
    """Generate template-based one-liner for life area."""
    
    templates = {
        "Career & Finance": {
            "favorable": f"Your {chart_sig.sun_sign} Sun in the {chart_sig.sun_house}th house supports professional growth and financial gains.",
            "mixed": f"Career progress requires patience and strategic planning this year.",
            "challenging": "Focus on building skills and weathering temporary professional challenges."
        },
        "Love & Romance": {
            "favorable": f"With your {chart_sig.moon_sign} Moon, emotional connections deepen and romantic opportunities arise.",
            "mixed": "Relationships evolve through honest communication and mutual understanding.",
            "challenging": "This year emphasizes self-love and clarifying what you seek in partnerships."
        },
        "Home & Family": {
            "favorable": "Domestic life flourishes with opportunities to strengthen family bonds.",
            "mixed": "Home and family require attention but offer stability and grounding.",
            "challenging": "Navigate family dynamics with patience and clear boundaries."
        },
        "Health & Wellness": {
            "favorable": "Physical and mental well-being improve through consistent self-care practices.",
            "mixed": "Maintain routines that support your health and adjust as needed.",
            "challenging": "Prioritize rest, nutrition, and stress management for optimal health."
        },
        "Growth & Learning": {
            "favorable": "Intellectual pursuits and educational opportunities expand your horizons.",
            "mixed": "Learning comes through both planned study and life experiences.",
            "challenging": "Growth requires stepping outside your comfort zone and embracing new perspectives."
        },
        "Inner Work": {
            "favorable": "Spiritual and emotional development brings profound insights and peace.",
            "mixed": "Inner work unfolds gradually through reflection and self-awareness.",
            "challenging": "Face inner shadows with courage to emerge stronger and more authentic."
        }
    }
    
    return templates.get(area, {}).get(outlook, "A year of continued growth in this area.")


async def generate_yearly_forecast_summary(
    req: YearlyForecastRequest
) -> YearlyForecastSummaryResponse:
    """
    Generate FAST, FREE yearly forecast summary (NO LLM calls).
    Target: <5 seconds response time.
    """
    
    start_time = time.time()
    logger.info(f"🚀 Starting FAST summary for year {req.options.year}")
    
    # Step 1: Get raw forecast data (fast - ~3-5 seconds)
    step_start = time.time()
    raw_forecast = await compute_yearly_forecast(
        req.chart_input.model_dump(),
        req.options.model_dump()
    )
    step_time = time.time() - step_start
    logger.info(f"⏱️  [1/3] Raw forecast: {step_time:.2f}s")
    
    # Step 2: Extract natal chart signature from raw_forecast meta (fast - <1 second)
    step_start = time.time()
    
    # Try to extract from raw_forecast first (already calculated)
    meta = raw_forecast.get("meta", {})
    if meta and "natal_chart" in meta:
        # Extract from already calculated natal data
        chart_sig = _extract_chart_signature_from_meta(meta)
    else:
        # Fallback to calculating it
        chart_sig = _extract_chart_signature(req.chart_input.model_dump())
    
    step_time = time.time() - step_start
    logger.info(f"⏱️  [2/3] Chart signature extracted: {step_time:.2f}s")
    
    # Step 3: Build response using templates (fast - <1 second)
    step_start = time.time()
    
    months_data = raw_forecast.get("months", {})
    top_events = raw_forecast.get("top_events", [])
    
    # Calculate month scores
    month_scores = {}
    for month_key, events in months_data.items():
        high = len([e for e in events if e.get("score", 0) > 0.5])
        caution = len([e for e in events if e.get("score", 0) < -0.5])
        score = max(0, min(10, 5.0 + (high - caution) * 0.5))
        month_scores[month_key] = score
    
    avg_score = sum(month_scores.values()) / len(month_scores) if month_scores else 5.0
    
    # Determine energy level
    if avg_score >= 7:
        energy_level = "expansive"
    elif avg_score >= 5:
        energy_level = "balanced"
    else:
        energy_level = "introspective"
    
    # Generate yearly theme (template-based)
    yearly_theme = _generate_yearly_theme(chart_sig, top_events, avg_score)
    
    # Extract top opportunities and challenges
    positive_events = [e for e in top_events if e.get("score", 0) > 0.5][:3]
    challenging_events = [e for e in top_events if e.get("score", 0) < -0.5][:3]
    
    top_opportunities = [
        e.get("note", f"{e.get('transit_body')} {e.get('aspect')} {e.get('natal_body')}")
        for e in positive_events
    ]
    
    top_challenges = [
        e.get("note", f"{e.get('transit_body')} {e.get('aspect')} {e.get('natal_body')}")
        for e in challenging_events
    ]
    
    # Best months
    sorted_months = sorted(month_scores.items(), key=lambda x: x[1], reverse=True)
    best_months = []
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    
    for month_key, score in sorted_months[:3]:
        month_num = int(month_key.split("-")[1])
        energy = "high" if score >= 6.5 else "moderate" if score >= 5.5 else "low"
        
        # Get key event for this month
        month_events = months_data.get(month_key, [])
        key_event = None
        if month_events:
            top_event = max(month_events, key=lambda e: abs(e.get("score", 0)))
            key_event = top_event.get("note", "") if top_event.get("note") else None
        
        best_months.append(KeyMonth(
            month=month_key,
            name=month_names[month_num - 1],
            energy=energy,
            key_event=key_event
        ))
    
    # Life areas (template-based)
    area_keywords = {
        "Career & Finance": ["career", "work", "profession", "10th", "money", "2nd"],
        "Love & Romance": ["love", "romance", "7th", "venus", "partner"],
        "Home & Family": ["home", "family", "4th", "parent"],
        "Health & Wellness": ["health", "6th", "wellness", "body"],
        "Growth & Learning": ["learning", "9th", "education", "jupiter"],
        "Inner Work": ["transformation", "8th", "12th", "spiritual"]
    }
    
    life_areas = []
    all_events = [e for events in months_data.values() for e in events]
    
    for area_name, keywords in area_keywords.items():
        outlook = _classify_life_area_outlook(all_events, keywords)
        one_liner = _generate_life_area_one_liner(area_name, outlook, chart_sig)
        
        life_areas.append(QuickLifeArea(
            area=area_name,
            outlook=outlook,
            one_liner=one_liner
        ))
    
    # Key transits
    key_transits = []
    for event in top_events[:5]:
        if event.get("date"):
            transit_body = event.get("transit_body", "")
            natal_body = event.get("natal_body", "")
            aspect = event.get("aspect", "")
            score = event.get("score", 0)
            
            # Clean transit description
            if natal_body and natal_body not in ["—", "-", "–", "None", ""]:
                event_desc = f"{transit_body} {aspect} natal {natal_body}"
            else:
                event_desc = event.get("note", f"{transit_body} {aspect}")
            
            impact = "positive" if score > 0.3 else "challenging" if score < -0.3 else "neutral"
            
            key_transits.append(KeyTransit(
                date=Date.fromisoformat(event.get("date")),
                event=event_desc,
                impact=impact
            ))
    
    # Build overview
    overview = YearlySummaryOverview(
        year=req.options.year,
        chart_signature=chart_sig,
        yearly_theme=yearly_theme,
        energy_level=energy_level,
        top_opportunities=top_opportunities,
        top_challenges=top_challenges
    )
    
    step_time = time.time() - step_start
    logger.info(f"⏱️  [3/3] Response built: {step_time:.2f}s")
    
    total_time = time.time() - start_time
    logger.info(f"✅ Total summary generation: {total_time:.2f}s")
    
    person_name = req.options.profile_name or "User"
    birth_date = Date.fromisoformat(req.chart_input.date)
    
    return YearlyForecastSummaryResponse(
        person_name=person_name,
        birth_date=birth_date,
        year=req.options.year,
        overview=overview,
        best_months=best_months,
        life_areas=life_areas,
        key_transits=key_transits,
        generated_at=datetime.utcnow().isoformat(),
        system=req.chart_input.system
    )

