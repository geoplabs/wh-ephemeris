"""Helper functions for single LLM call brief forecast generation."""

import json
import logging
from datetime import date as Date
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def get_brief_system_prompt() -> str:
    """System prompt for brief yearly forecast generation."""
    return """You are an expert astrologer creating brief yearly forecasts.

Generate a concise, empowering yearly forecast with:
- 12 monthly highlights (2-3 sentences each)
- 6 life area summaries (2 sentences each with themes)
- Overall yearly themes and energy
- Key opportunities and challenges

TONE: Warm, empowering, practical
FORMAT: Brief but meaningful - focus on actionable insights
OUTPUT: Return valid JSON only, no markdown, no explanations"""


def build_brief_forecast_prompt(raw_forecast: Dict[str, Any], req: Any) -> str:
    """Build comprehensive prompt for single LLM call."""
    
    year = req.options.year
    system = req.chart_input.system
    
    # Extract key data from raw forecast
    months_data = raw_forecast.get("months", {})
    top_events = raw_forecast.get("top_events", [])[:10]
    eclipses = raw_forecast.get("eclipses", [])
    
    # Build month summaries for context
    month_summaries = []
    for month_key in sorted(months_data.keys()):
        events = months_data[month_key]
        high_events = [e for e in events if e.get("score", 0) > 0.5]
        caution_events = [e for e in events if e.get("score", 0) < -0.5]
        
        month_summaries.append({
            "month": month_key,
            "high_count": len(high_events),
            "caution_count": len(caution_events),
            "top_events": [
                f"{e.get('transit_body')} {e.get('aspect')} {e.get('natal_body')}"
                for e in sorted(events, key=lambda x: abs(x.get('score', 0)), reverse=True)[:3]
            ]
        })
    
    prompt = f"""Generate a brief {year} yearly forecast for a {system} chart.

YEAR DATA:
- System: {system}
- Year: {year}
- Top Events: {len(top_events)}
- Eclipses: {len(eclipses)}

MONTHLY SUMMARY:
{json.dumps(month_summaries, indent=2)}

TOP YEARLY EVENTS:
{json.dumps([{
    "date": e.get("date"),
    "transit": f"{e.get('transit_body')} {e.get('aspect')} {e.get('natal_body')}",
    "score": e.get("score")
} for e in top_events], indent=2)}

ECLIPSES:
{json.dumps([{
    "date": e.get("date"),
    "type": e.get("kind"),
    "sign": e.get("sign")
} for e in eclipses], indent=2)}

Generate a JSON response with this EXACT structure:
{{
  "yearly_overview": {{
    "main_themes": ["theme 1", "theme 2", "theme 3"],
    "overall_energy": "expansive|balanced|introspective",
    "key_opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"],
    "key_challenges": ["challenge 1", "challenge 2", "challenge 3"]
  }},
  "monthly_highlights": [
    {{
      "month": "2026-01",
      "key_theme": "Brief theme for January",
      "brief_guidance": "2-3 sentences of guidance for January"
    }},
    ... (12 months total)
  ],
  "life_areas": [
    {{
      "area": "Career & Finance",
      "yearly_theme": "Brief theme for career/finance",
      "brief_guidance": "2 sentences of guidance"
    }},
    {{
      "area": "Love & Romance",
      "yearly_theme": "Brief theme for love",
      "brief_guidance": "2 sentences of guidance"
    }},
    {{
      "area": "Home & Family",
      "yearly_theme": "Brief theme for home/family",
      "brief_guidance": "2 sentences of guidance"
    }},
    {{
      "area": "Health & Wellness",
      "yearly_theme": "Brief theme for health",
      "brief_guidance": "2 sentences of guidance"
    }},
    {{
      "area": "Growth & Learning",
      "yearly_theme": "Brief theme for growth",
      "brief_guidance": "2 sentences of guidance"
    }},
    {{
      "area": "Inner Work",
      "yearly_theme": "Brief theme for inner work",
      "brief_guidance": "2 sentences of guidance"
    }}
  ],
  "recommendations": {{
    "do_more": ["action 1", "action 2", "action 3"],
    "avoid": ["avoid 1", "avoid 2", "avoid 3"],
    "focus_on": ["focus 1", "focus 2", "focus 3"]
  }}
}}

Return ONLY valid JSON, no markdown, no code blocks."""
    
    return prompt


def parse_llm_response_to_brief(llm_response: str, raw_forecast: Dict[str, Any], req: Any) -> Any:
    """Parse LLM JSON response and build BriefYearlyForecastResponse."""
    from ..schemas.yearly_forecast_brief import (
        BriefYearlyForecastResponse,
        BriefYearlyOverview,
        BriefMonthHighlight,
        BriefLifeArea,
        BriefTransit,
        BriefEclipse,
    )
    from datetime import datetime
    
    try:
        # Try to extract JSON from response (in case LLM adds markdown)
        json_str = llm_response.strip()
        if json_str.startswith("```json"):
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif json_str.startswith("```"):
            json_str = json_str.split("```")[1].split("```")[0].strip()
        
        llm_data = json.loads(json_str)
        
        # Extract data from raw forecast for additional info
        months_data = raw_forecast.get("months", {})
        top_events = raw_forecast.get("top_events", [])
        eclipses = raw_forecast.get("eclipses", [])
        
        # Build overview
        yearly_overview = llm_data.get("yearly_overview", {})
        
        # Calculate overall energy score from months
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
        
        overview = BriefYearlyOverview(
            year=req.options.year,
            main_themes=yearly_overview.get("main_themes", [])[:5],
            overall_energy=yearly_overview.get("overall_energy", "balanced"),
            energy_score=round(energy_score, 1),
            key_opportunities=yearly_overview.get("key_opportunities", [])[:3],
            key_challenges=yearly_overview.get("key_challenges", [])[:3],
            best_months=[],
            challenging_months=[]
        )
        
        # Build monthly highlights
        monthly_highlights = []
        llm_months = {m["month"]: m for m in llm_data.get("monthly_highlights", [])}
        
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
        
        # Build life areas with sentiment scores
        life_areas = []
        for llm_area in llm_data.get("life_areas", []):
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
                    area=llm_area.get("area", "Life Area"),
                    yearly_theme=theme,
                    score=round(area_score, 1),
                    key_months=[],
                    brief_guidance=guidance
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
                        impact_summary=f"{event.get('transit_body')} {event.get('aspect')} {event.get('natal_body')}"[:100]
                    )
                )
        
        # Extract eclipses
        eclipse_list = []
        for eclipse in eclipses:
            if eclipse.get("date"):
                eclipse_kind = eclipse.get("kind", "").lower()
                if "solar" in eclipse_kind:
                    ecl_type = "solar"
                elif "lunar" in eclipse_kind:
                    ecl_type = "lunar"
                else:
                    ecl_type = "unknown"
                
                if "total" in eclipse_kind:
                    subtype = "total"
                elif "annular" in eclipse_kind:
                    subtype = "annular"
                elif "partial" in eclipse_kind:
                    subtype = "partial"
                else:
                    subtype = "unknown"
                
                eclipse_list.append(
                    BriefEclipse(
                        date=Date.fromisoformat(eclipse.get("date")),
                        type=ecl_type,
                        eclipse_kind=subtype,
                        sign=eclipse.get("sign", "Unknown"),
                        house=None,
                        brief_impact=eclipse.get("guidance", "Eclipse brings transformation")[:150]
                    )
                )
        
        # Get recommendations
        recommendations = llm_data.get("recommendations", {
            "do_more": ["Focus on opportunities", "Plan during favorable periods", "Trust your intuition"],
            "avoid": ["Rushing decisions", "Overcommitting", "Ignoring self-care"],
            "focus_on": ["Personal growth", "Relationships", "Balance"]
        })
        
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
        
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        logger.error(f"Response was: {llm_response[:500]}")
        raise


def build_fallback_brief_response(raw_forecast: Dict[str, Any], req: Any) -> Any:
    """Build fallback response if LLM fails."""
    from ..schemas.yearly_forecast_brief import (
        BriefYearlyForecastResponse,
        BriefYearlyOverview,
        BriefMonthHighlight,
        BriefLifeArea,
        BriefTransit,
        BriefEclipse,
    )
    from datetime import datetime
    
    logger.warning("Using fallback response (no LLM)")
    
    person_name = req.options.profile_name or "User"
    birth_date = Date.fromisoformat(req.chart_input.date)
    
    # Basic overview
    overview = BriefYearlyOverview(
        year=req.options.year,
        main_themes=["Yearly transits and aspects"],
        overall_energy="balanced",
        energy_score=5.0,
        key_opportunities=["Personal growth", "New experiences", "Connections"],
        key_challenges=["Patience", "Balance", "Timing"],
        best_months=[],
        challenging_months=[]
    )
    
    # Generic monthly highlights
    months_data = raw_forecast.get("months", {})
    monthly_highlights = []
    
    for i, month_key in enumerate(sorted(months_data.keys()), 1):
        events = months_data[month_key]
        high_count = len([e for e in events if e.get("score", 0) > 0.5])
        caution_count = len([e for e in events if e.get("score", 0) < -0.5])
        score = max(0, min(10, 5.0 + (high_count - caution_count) * 0.5))
        
        monthly_highlights.append(
            BriefMonthHighlight(
                month=month_key,
                month_number=i,
                key_theme="Monthly transits and aspects",
                energy_score=round(score, 1),
                energy_level="balanced" if 4 <= score <= 6 else ("good" if score > 6 else "challenging"),
                notable_dates=[],
                brief_guidance="Focus on the planetary energies this month."
            )
        )
    
    # Generic life areas
    life_areas = [
        BriefLifeArea(area="Career & Finance", yearly_theme="Professional development", score=5.0, key_months=[], brief_guidance="Focus on steady progress."),
        BriefLifeArea(area="Love & Romance", yearly_theme="Relationship growth", score=5.0, key_months=[], brief_guidance="Nurture connections."),
        BriefLifeArea(area="Home & Family", yearly_theme="Family bonds", score=5.0, key_months=[], brief_guidance="Strengthen foundations."),
        BriefLifeArea(area="Health & Wellness", yearly_theme="Self-care", score=5.0, key_months=[], brief_guidance="Maintain routines."),
        BriefLifeArea(area="Growth & Learning", yearly_theme="Expansion", score=5.0, key_months=[], brief_guidance="Explore new horizons."),
        BriefLifeArea(area="Inner Work", yearly_theme="Self-discovery", score=5.0, key_months=[], brief_guidance="Reflect and grow."),
    ]
    
    return BriefYearlyForecastResponse(
        person_name=person_name,
        birth_date=birth_date,
        year=req.options.year,
        overview=overview,
        monthly_highlights=monthly_highlights,
        life_areas=life_areas,
        major_transits=[],
        eclipses=[],
        retrograde_periods=[],
        recommendations={
            "do_more": ["Plan ahead", "Stay flexible", "Trust timing"],
            "avoid": ["Rushing", "Overcommitting", "Ignoring intuition"],
            "focus_on": ["Growth", "Balance", "Connections"]
        },
        generated_at=datetime.utcnow().isoformat(),
        system=req.chart_input.system,
    )

