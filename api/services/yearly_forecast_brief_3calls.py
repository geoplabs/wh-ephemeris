"""
3-Call Hybrid Approach for Brief Yearly Forecast.
Makes 3 strategic LLM calls instead of 1 (poor quality) or 115 (too slow).
"""

import json
import logging
from datetime import datetime, date as Date
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def generate_monthly_narratives_llm(raw_forecast: Dict[str, Any], req: Any) -> Dict[str, Any]:
    """
    LLM Call 1: Generate rich narratives for ALL 12 months.
    Returns detailed themes and guidance for each month.
    """
    from ..services.llm_client import generate_section_text
    
    year = req.options.year
    months_data = raw_forecast.get("months", {})
    
    # Build month summaries
    month_summaries = []
    for month_key in sorted(months_data.keys()):
        events = months_data[month_key]
        high_events = [e for e in events if e.get("score", 0) > 0.5]
        caution_events = [e for e in events if e.get("score", 0) < -0.5]
        
        top_transits = [
            f"{e.get('transit_body')} {e.get('aspect')} {e.get('natal_body')}"
            for e in sorted(events, key=lambda x: abs(x.get('score', 0)), reverse=True)[:3]
        ]
        
        month_summaries.append({
            "month": month_key,
            "high_count": len(high_events),
            "caution_count": len(caution_events),
            "top_transits": top_transits,
            "total_events": len(events)
        })
    
    system_prompt = """You are an expert astrologer creating rich, engaging monthly forecasts.

TONE: Warm, empowering, specific
FORMAT: Use markdown (### for headings, **bold** for emphasis)
QUALITY: Detailed, personalized, actionable guidance

Return ONLY valid JSON."""

    user_prompt = f"""Generate detailed monthly highlights for all 12 months of {year}.

MONTHLY DATA:
{json.dumps(month_summaries, indent=2)}

For EACH month, provide:
1. **key_theme**: Rich, engaging theme starting with ### Month YYYY Overview (2-3 sentences with specific astrological references)
2. **brief_guidance**: Detailed, actionable guidance (2-3 sentences referencing specific transits and dates)

IMPORTANT:
- Use markdown formatting (### for headings, **bold** for key phrases)
- Reference specific transits and their impacts
- Make it personal and engaging
- Each month should be unique based on its transits

Return this EXACT JSON structure:
{{
  "monthly_highlights": [
    {{
      "month": "2026-01",
      "key_theme": "### January 2026 Overview\\nDetailed theme with specific astrological context...",
      "brief_guidance": "Specific guidance referencing the transits mentioned above. Include actionable advice..."
    }},
    {{
      "month": "2026-02",
      "key_theme": "### February 2026 Overview\\nDetailed theme...",
      "brief_guidance": "Specific guidance..."
    }}
    ... (continue for all 12 months)
  ]
}}

Return ONLY the JSON, no markdown code blocks."""

    try:
        response = await generate_section_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=3500  # Enough for rich content for 12 months
        )
        
        # Parse JSON response
        json_str = response.strip()
        if json_str.startswith("```json"):
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif json_str.startswith("```"):
            json_str = json_str.split("```")[1].split("```")[0].strip()
        
        return json.loads(json_str)
        
    except Exception as e:
        logger.error(f"Monthly narratives LLM call failed: {e}")
        return {"monthly_highlights": []}


async def generate_life_areas_llm(raw_forecast: Dict[str, Any], req: Any) -> Dict[str, Any]:
    """
    LLM Call 2: Generate rich themes for ALL 6 life areas.
    Returns detailed yearly themes and guidance for each area.
    """
    from ..services.llm_client import generate_section_text
    
    year = req.options.year
    months_data = raw_forecast.get("months", {})
    
    # Analyze event patterns across the year
    all_events = []
    for month_key, events in months_data.items():
        all_events.extend(events)
    
    # Group events by type for context
    career_events = [e for e in all_events if any(word in str(e.get("note", "")).lower() for word in ["career", "work", "profession", "midheaven"])]
    love_events = [e for e in all_events if any(word in str(e.get("note", "")).lower() for word in ["love", "romance", "relationship", "venus"])]
    
    system_prompt = """You are an expert astrologer creating rich, personalized yearly themes for life areas.

TONE: Warm, empowering, specific
FORMAT: Use markdown (### for headings, **bold** for emphasis)
QUALITY: Detailed, personalized, forward-looking

Return ONLY valid JSON."""

    user_prompt = f"""Generate detailed yearly themes for all 6 life areas for {year}.

YEARLY CONTEXT:
- Total significant events: {len(all_events)}
- Career-related events: {len(career_events)}
- Love-related events: {len(love_events)}
- System: {req.chart_input.system}

For EACH of these 6 life areas, provide:
1. **yearly_theme**: Rich, engaging theme with markdown formatting (2-3 sentences with astrological context)
2. **brief_guidance**: Specific guidance for the year (2 sentences with actionable advice)

Life Areas:
1. Career & Finance - Professional growth, money, resources
2. Love & Romance - Relationships, partnerships, intimacy
3. Home & Family - Domestic life, family bonds, roots
4. Health & Wellness - Physical health, routines, self-care
5. Growth & Learning - Education, travel, expansion
6. Inner Work - Spirituality, self-discovery, healing

Return this EXACT JSON structure:
{{
  "life_areas": [
    {{
      "area": "Career & Finance",
      "yearly_theme": "### Career and Finance Guidance for {year}\\nDetailed theme with astrological context...",
      "brief_guidance": "Specific actionable guidance for the year..."
    }},
    {{
      "area": "Love & Romance",
      "yearly_theme": "### Love and Romance\\nDetailed theme...",
      "brief_guidance": "Specific guidance..."
    }}
    ... (continue for all 6 areas)
  ]
}}

Return ONLY the JSON, no markdown code blocks."""

    try:
        response = await generate_section_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2500  # Enough for rich content for 6 areas
        )
        
        # Parse JSON response
        json_str = response.strip()
        if json_str.startswith("```json"):
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif json_str.startswith("```"):
            json_str = json_str.split("```")[1].split("```")[0].strip()
        
        return json.loads(json_str)
        
    except Exception as e:
        logger.error(f"Life areas LLM call failed: {e}")
        return {"life_areas": []}


async def generate_eclipses_llm(raw_forecast: Dict[str, Any], req: Any) -> Dict[str, Any]:
    """
    LLM Call 3: Generate rich interpretations for eclipses.
    Returns personalized eclipse impacts and guidance.
    """
    from ..services.llm_client import generate_section_text
    
    eclipse_events = []  # Initialize at top level
    
    try:
        # Extract eclipses from raw monthly events
        months_data = raw_forecast.get("months", {})
        all_events = []
        for month_key, events in months_data.items():
            all_events.extend(events)
        
        # Filter for eclipse events
        for event in all_events:
            note = str(event.get("note", "")).lower()
            aspect = str(event.get("aspect", "")).lower()
            
            is_eclipse = (
                "eclipse" in aspect or 
                "eclipse" in note or
                "solar eclipse" in note or
                "lunar eclipse" in note
            )
            
            if is_eclipse:
                # Extract sign from transit_body (e.g., "Sun in Aries" -> "Aries")
                sign = "Unknown"
                transit_body = event.get("transit_body", "")
                if " in " in transit_body:
                    parts = transit_body.split(" in ")
                    if len(parts) == 2:
                        sign = parts[1].strip()
                
                # Determine eclipse type
                if "solar eclipse" in note or "sun" in transit_body.lower():
                    kind = "Solar Eclipse"
                elif "lunar eclipse" in note or "moon" in transit_body.lower():
                    kind = "Lunar Eclipse"
                else:
                    kind = "Eclipse"
                
                eclipse_events.append({
                    "date": event.get("date"),
                    "type": kind,
                    "sign": sign,
                    "house": event.get("section"),
                    "note": event.get("note", ""),
                })
        
        logger.info(f"Eclipse data available: {len(eclipse_events)} eclipses extracted from {len(all_events)} events")
        if not eclipse_events:
            logger.warning("No eclipse events found in raw forecast")
            return {"eclipses": [], "raw_eclipse_events": []}
        
        # Build eclipse context for LLM
        eclipse_data = []
        for eclipse in eclipse_events:
            eclipse_data.append({
                "date": eclipse.get("date"),
                "type": eclipse.get("type", ""),
                "sign": eclipse.get("sign", ""),
                "house": eclipse.get("house"),
            })
        
        system_prompt = """You are an expert astrologer interpreting eclipses with depth and wisdom.

TONE: Profound, empowering, specific
QUALITY: Detailed, personalized interpretations
FORMAT: 2-3 sentences per eclipse

Return ONLY valid JSON."""

        user_prompt = f"""Generate rich, personalized interpretations for these {len(eclipse_events)} eclipses.

ECLIPSE DATA:
{json.dumps(eclipse_data, indent=2)}

For EACH eclipse, provide:
**brief_impact**: A rich, personalized interpretation (2-3 sentences) that includes:
- Specific date and type
- Impact based on the sign/house
- Actionable guidance
- Empowering perspective

Return this EXACT JSON structure:
{{
  "eclipses": [
    {{
      "date": "2026-02-17",
      "brief_impact": "This Partial Solar Eclipse on February 17, 2026, offers you a unique opportunity... [2-3 detailed sentences with specific guidance]"
    }},
    {{
      "date": "2026-03-03",
      "brief_impact": "The Total Lunar Eclipse on March 3, 2026, brings... [2-3 detailed sentences]"
    }}
    ... (continue for all eclipses)
  ]
}}

Return ONLY the JSON, no markdown code blocks."""

        response = await generate_section_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2000  # Enough for detailed eclipse interpretations
        )
        
        # Parse JSON response
        json_str = response.strip()
        if json_str.startswith("```json"):
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif json_str.startswith("```"):
            json_str = json_str.split("```")[1].split("```")[0].strip()
        
        result = json.loads(json_str)
        # Include raw eclipse events for response builder
        result["raw_eclipse_events"] = eclipse_events
        return result
        
    except Exception as e:
        logger.error(f"Eclipses LLM call failed: {e}")
        return {"eclipses": [], "raw_eclipse_events": eclipse_events}


def build_response_from_llm_outputs(
    monthly_narratives: Dict[str, Any],
    life_areas_data: Dict[str, Any],
    eclipses_data: Dict[str, Any],
    raw_forecast: Dict[str, Any],
    req: Any
) -> Any:
    """
    Build the final BriefYearlyForecastResponse from the 3 LLM outputs + raw data.
    """
    from ..schemas.yearly_forecast_brief import (
        BriefYearlyForecastResponse,
        BriefYearlyOverview,
        BriefMonthHighlight,
        BriefLifeArea,
        BriefTransit,
        BriefEclipse,
    )
    
    logger.info("Building response from 3 LLM outputs")
    
    # Extract data
    months_data = raw_forecast.get("months", {})
    top_events = raw_forecast.get("top_events", [])
    
    # Build overview
    main_themes = [
        event.get("transit_body", "") + " to " + event.get("natal_body", "")
        for event in top_events[:5]
    ]
    
    # Calculate overall energy score
    total_score = 0
    month_count = 0
    for month_key in months_data:
        events = months_data[month_key]
        high = len([e for e in events if e.get("score", 0) > 0.5])
        caution = len([e for e in events if e.get("score", 0) < -0.5])
        total_score += high - caution
        month_count += 1
    
    avg_score = total_score / month_count if month_count > 0 else 0
    energy_score = max(0, min(10, 5.0 + avg_score * 0.5))
    
    if energy_score >= 7:
        overall_energy = "expansive"
    elif energy_score >= 5:
        overall_energy = "balanced"
    else:
        overall_energy = "introspective"
    
    overview = BriefYearlyOverview(
        year=req.options.year,
        main_themes=main_themes,
        overall_energy=overall_energy,
        energy_score=round(energy_score, 1),
        key_opportunities=["Personal growth opportunities", "Career advancement", "New connections"],
        key_challenges=["Patience required", "Inner work needed", "Balance priorities"],
        best_months=[],
        challenging_months=[]
    )
    
    # Build monthly highlights from LLM output
    llm_months = {m["month"]: m for m in monthly_narratives.get("monthly_highlights", [])}
    monthly_highlights = []
    
    for i, month_key in enumerate(sorted(months_data.keys()), 1):
        events = months_data[month_key]
        high_events = [e for e in events if e.get("score", 0) > 0.5]
        caution_events = [e for e in events if e.get("score", 0) < -0.5]
        
        month_score = max(0, min(10, 5.0 + (len(high_events) - len(caution_events)) * 0.5))
        
        if month_score >= 8.0:
            energy_level = "very favorable"
        elif month_score >= 6.0:
            energy_level = "good"
        elif month_score >= 4.0:
            energy_level = "balanced"
        elif month_score >= 2.0:
            energy_level = "challenging"
        else:
            energy_level = "difficult"
        
        llm_month = llm_months.get(month_key, {})
        
        # Get notable dates from high events
        notable_dates = [
            Date.fromisoformat(e.get("date"))
            for e in sorted(high_events, key=lambda x: x.get("score", 0), reverse=True)[:3]
            if e.get("date")
        ]
        
        monthly_highlights.append(
            BriefMonthHighlight(
                month=month_key,
                month_number=i,
                key_theme=llm_month.get("key_theme", "Monthly energy and transits"),
                energy_score=round(month_score, 1),
                energy_level=energy_level,
                notable_dates=notable_dates,
                brief_guidance=llm_month.get("brief_guidance", "Focus on the key transits this month.")
            )
        )
    
    # Build life areas from LLM output
    llm_areas = {a["area"]: a for a in life_areas_data.get("life_areas", [])}
    life_areas = []
    
    for area_name in ["Career & Finance", "Love & Romance", "Home & Family", "Health & Wellness", "Growth & Learning", "Inner Work"]:
        llm_area = llm_areas.get(area_name, {})
        
        # Calculate score based on content sentiment
        theme = llm_area.get("yearly_theme", "")
        guidance = llm_area.get("brief_guidance", "")
        combined_text = (theme + " " + guidance).lower()
        
        positive_words = ["opportunity", "growth", "success", "favorable", "support", "strengthen", "improve", "excel", "thrive", "prosper"]
        negative_words = ["challenge", "difficulty", "tension", "stress", "caution", "delay", "obstacle", "conflict", "struggle"]
        
        pos_count = sum(1 for word in positive_words if word in combined_text)
        neg_count = sum(1 for word in negative_words if word in combined_text)
        
        area_score = max(0, min(10, 5.0 + (pos_count * 0.5) - (neg_count * 0.3) + (len(combined_text) / 500)))
        
        life_areas.append(
            BriefLifeArea(
                area=area_name,
                yearly_theme=theme or f"{area_name} focus for the year",
                score=round(area_score, 1),
                key_months=[],
                brief_guidance=guidance or f"Focus on {area_name.lower()} throughout the year."
            )
        )
    
    # Extract major transits
    major_transits = []
    for event in top_events[:10]:
        if event.get("date"):
            major_transits.append(
                BriefTransit(
                    planet=event.get("transit_body", "Planet"),
                    event_type=event.get("aspect", "aspect"),
                    date=Date.fromisoformat(event.get("date")),
                    impact_summary=event.get("note", f"{event.get('transit_body')} {event.get('aspect')} {event.get('natal_body')}")[:100]
                )
            )
    
    # Build eclipses from LLM output
    llm_eclipses = {e["date"]: e for e in eclipses_data.get("eclipses", [])}
    raw_eclipse_events = eclipses_data.get("raw_eclipse_events", [])
    eclipse_list = []
    
    logger.info(f"Building eclipse list from {len(raw_eclipse_events)} raw events and {len(llm_eclipses)} LLM outputs")
    
    for eclipse in raw_eclipse_events:
        if eclipse.get("date"):
            eclipse_type_str = eclipse.get("type", "").lower()
            if "solar" in eclipse_type_str:
                ecl_type = "solar"
            elif "lunar" in eclipse_type_str:
                ecl_type = "lunar"
            else:
                ecl_type = "unknown"
            
            # Parse eclipse note for subtype
            note = eclipse.get("note", "").lower()
            if "total" in note:
                subtype = "total"
            elif "annular" in note:
                subtype = "annular"
            elif "partial" in note:
                subtype = "partial"
            else:
                subtype = "unknown"
            
            llm_eclipse = llm_eclipses.get(eclipse.get("date"), {})
            
            eclipse_list.append(
                BriefEclipse(
                    date=Date.fromisoformat(eclipse.get("date")),
                    type=ecl_type,
                    eclipse_kind=subtype,
                    sign=eclipse.get("sign", "Unknown"),
                    house=None,
                    brief_impact=llm_eclipse.get("brief_impact", eclipse.get("note", "Eclipse brings transformation"))[:200]
                )
            )
    
    logger.info(f"Built {len(eclipse_list)} eclipse summaries")
    
    # Build recommendations (can enhance with LLM later if needed)
    recommendations = {
        "do_more": ["Focus on opportunities", "Plan during favorable periods", "Trust your intuition"],
        "avoid": ["Rushing decisions", "Overcommitting", "Ignoring self-care"],
        "focus_on": ["Personal growth", "Relationships", "Balance"]
    }
    
    person_name = req.options.profile_name or "User"
    birth_date = Date.fromisoformat(req.chart_input.date)
    
    return BriefYearlyForecastResponse(
        person_name=person_name,
        birth_date=birth_date,
        year=req.options.year,
        overview=overview,
        monthly_highlights=monthly_highlights,
        life_areas=life_areas,
        major_transits=major_transits,
        eclipses=eclipse_list,
        retrograde_periods=[],
        recommendations=recommendations,
        generated_at=datetime.utcnow().isoformat(),
        system=req.chart_input.system,
    )

