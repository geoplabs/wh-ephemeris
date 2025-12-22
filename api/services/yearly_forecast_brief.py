"""
Service for generating brief yearly forecasts (JSON only, no PDF).
Provides concise summaries suitable for mobile apps and quick previews.
Uses 3 strategic LLM calls for high-quality content with fast performance.
"""

import logging
import time
import asyncio
from datetime import datetime, date as Date
from typing import Any, Dict, List, Optional

from ..schemas.yearly_forecast_brief import (
    BriefYearlyForecastResponse,
    BriefYearlyOverview,
    BriefMonthHighlight,
    BriefLifeArea,
    BriefTransit,
    BriefEclipse,
)
from ..schemas.yearly_forecast_report import YearlyForecastRequest
from .yearly_forecast_report import compute_yearly_forecast
from .yearly_forecast_brief_3calls import (
    generate_monthly_narratives_llm,
    generate_life_areas_llm,
    generate_eclipses_llm,
    build_response_from_llm_outputs,
)
from .llm_client import LLMUnavailableError

logger = logging.getLogger(__name__)


async def generate_brief_yearly_forecast(
    req: YearlyForecastRequest
) -> BriefYearlyForecastResponse:
    """
    Generate a brief yearly forecast in JSON format with 3 STRATEGIC LLM calls.
    
    This endpoint:
    1. Computes raw forecast data (fast - ~5-10 seconds)
    2. Makes 3 PARALLEL LLM calls for high-quality content:
       - Call 1: All 12 monthly narratives
       - Call 2: All 6 life area themes
       - Call 3: Eclipse interpretations
    3. Returns rich, detailed JSON (no PDF generation)
    4. Balanced: ~16-20 seconds with excellent quality
    
    Args:
        req: YearlyForecastRequest (same as PDF endpoint)
        
    Returns:
        BriefYearlyForecastResponse: Rich JSON forecast with AI-generated content
    """
    
    start_time = time.time()
    logger.info(f"🚀 Starting brief yearly forecast with 3 STRATEGIC LLM calls for year {req.options.year}")
    
    # Step 1: Get raw forecast data (fast - ~5-10 seconds)
    step_start = time.time()
    raw_forecast = await compute_yearly_forecast(
        req.chart_input.model_dump(), 
        req.options.model_dump()
    )
    step_time = time.time() - step_start
    logger.info(f"⏱️  [1/4] Raw forecast computed: {step_time:.2f}s")
    
    # Step 2: Make 3 PARALLEL LLM calls for quality content
    step_start = time.time()
    try:
        # Run 3 focused LLM calls in parallel
        monthly_task = generate_monthly_narratives_llm(raw_forecast, req)
        life_areas_task = generate_life_areas_llm(raw_forecast, req)
        eclipses_task = generate_eclipses_llm(raw_forecast, req)
        
        # Execute all 3 calls in parallel
        monthly_narratives, life_areas_data, eclipses_data = await asyncio.gather(
            monthly_task,
            life_areas_task,
            eclipses_task
        )
        
        step_time = time.time() - step_start
        logger.info(f"⏱️  [2/4] 3 parallel LLM calls completed: {step_time:.2f}s")
        
    except LLMUnavailableError as e:
        logger.error(f"❌ LLM unavailable: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ LLM calls failed: {e}")
        # Re-raise as LLM error
        raise LLMUnavailableError(f"Failed to generate LLM content: {str(e)}") from e
    
    # Step 3: Build structured response from LLM outputs
    step_start = time.time()
    response = build_response_from_llm_outputs(
        monthly_narratives,
        life_areas_data,
        eclipses_data,
        raw_forecast,
        req
    )
    step_time = time.time() - step_start
    logger.info(f"⏱️  [3/4] Response built: {step_time:.2f}s")
    
    total_time = time.time() - start_time
    logger.info(f"✅ Total brief forecast generation time: {total_time:.2f}s")
    
    return response
    
    # Build brief overview from LLM-interpreted report
    step_start = time.time()
    overview = _build_brief_overview(full_report, req.options.year)
    step_time = time.time() - step_start
    logger.info(f"⏱️  [2/9] Overview built: {step_time:.2f}s")
    
    # Build monthly highlights from LLM-interpreted data
    step_start = time.time()
    monthly_highlights = _build_monthly_highlights(full_report.months)
    step_time = time.time() - step_start
    logger.info(f"⏱️  [3/9] Monthly highlights built: {step_time:.2f}s")
    
    # Build life area summaries from LLM-interpreted data
    step_start = time.time()
    life_areas = _build_life_area_summaries(full_report.months)
    step_time = time.time() - step_start
    logger.info(f"⏱️  [4/9] Life areas built: {step_time:.2f}s")
    
    # Extract major transits from LLM-interpreted report
    step_start = time.time()
    major_transits = _extract_major_transits(full_report)
    step_time = time.time() - step_start
    logger.info(f"⏱️  [5/9] Major transits extracted: {step_time:.2f}s")
    
    # Extract eclipses from LLM-interpreted report
    step_start = time.time()
    eclipses = _extract_eclipses(full_report)
    step_time = time.time() - step_start
    logger.info(f"⏱️  [6/9] Eclipses extracted: {step_time:.2f}s")
    
    # Extract retrograde periods from LLM-interpreted report
    step_start = time.time()
    retrograde_periods = _extract_retrogrades(full_report)
    step_time = time.time() - step_start
    logger.info(f"⏱️  [7/9] Retrogrades extracted: {step_time:.2f}s")
    
    # Build recommendations from LLM-interpreted report
    step_start = time.time()
    recommendations = _build_recommendations(full_report)
    step_time = time.time() - step_start
    logger.info(f"⏱️  [8/9] Recommendations built: {step_time:.2f}s")
    
    # Get person name from options or use default
    person_name = req.options.profile_name or "User"
    
    # Build response
    step_start = time.time()
    response = BriefYearlyForecastResponse(
        person_name=person_name,
        birth_date=birth_date,
        year=req.options.year,
        overview=overview,
        monthly_highlights=monthly_highlights,
        life_areas=life_areas,
        major_transits=major_transits,
        eclipses=eclipses,
        retrograde_periods=retrograde_periods,
        recommendations=recommendations,
        generated_at=datetime.utcnow().isoformat(),
        system=req.chart_input.system,
    )
    step_time = time.time() - step_start
    logger.info(f"⏱️  [9/9] Response built: {step_time:.2f}s")
    
    total_time = time.time() - start_time
    logger.info(f"✅ Total brief forecast generation time: {total_time:.2f}s")
    
    return response


def _build_brief_overview(full_report: Any, year: int) -> BriefYearlyOverview:
    """Build concise yearly overview from LLM-interpreted report."""
    
    # Extract top events for main themes (AI-generated titles)
    top_events = full_report.year_at_glance.top_events[:5]
    main_themes = [event.title for event in top_events]
    
    # Calculate average energy score from monthly data
    energy_scores = []
    best_months = []
    challenging_months = []
    
    for month in full_report.months:
        # Calculate month score from high/caution days
        month_score = len(month.high_score_days) - len(month.caution_days)
        energy_scores.append((month.month, month_score))
        
        if month_score >= 3:
            best_months.append(month.month)
        elif month_score <= -3:
            challenging_months.append(month.month)
    
    # Overall energy score (0-10 scale)
    avg_score = sum(score for _, score in energy_scores) / len(energy_scores) if energy_scores else 5.0
    overall_energy_score = max(0, min(10, 5.0 + avg_score))  # Normalize to 0-10
    
    # Determine overall energy type
    if overall_energy_score >= 7:
        overall_energy = "expansive"
    elif overall_energy_score >= 5:
        overall_energy = "balanced"
    else:
        overall_energy = "introspective"
    
    # Extract opportunities and challenges from AI-generated themes
    key_opportunities = [
        theme for theme in main_themes if any(word in theme.lower() for word in ["growth", "opportunity", "success", "expansion", "favor"])
    ][:3]
    
    key_challenges = [
        theme for theme in main_themes if any(word in theme.lower() for word in ["challenge", "caution", "transform", "release", "tension"])
    ][:3]
    
    # Fallback if extraction doesn't work
    if not key_opportunities:
        key_opportunities = ["Personal growth opportunities", "Career advancement", "New connections"]
    if not key_challenges:
        key_challenges = ["Patience required", "Inner work needed", "Balance priorities"]
    
    return BriefYearlyOverview(
        year=year,
        main_themes=main_themes,
        overall_energy=overall_energy,
        energy_score=round(overall_energy_score, 1),
        key_opportunities=key_opportunities,
        key_challenges=key_challenges,
        best_months=best_months[:3],
        challenging_months=challenging_months[:3],
    )


def _build_monthly_highlights(months: List[Any]) -> List[BriefMonthHighlight]:
    """Build brief monthly highlights from LLM-interpreted monthly data."""
    
    highlights = []
    
    for i, month_data in enumerate(months, 1):
        # Calculate energy score for month
        high_count = len(month_data.high_score_days)
        caution_count = len(month_data.caution_days)
        energy_score = max(0, min(10, 5.0 + (high_count - caution_count) * 0.5))
        
        # Determine energy level label based on score
        if energy_score >= 8.0:
            energy_level = "very favorable"
        elif energy_score >= 6.0:
            energy_level = "good"
        elif energy_score >= 4.0:
            energy_level = "balanced"
        elif energy_score >= 2.0:
            energy_level = "challenging"
        else:
            energy_level = "difficult"
        
        # Extract key theme from AI-generated overview (first sentence)
        overview_parts = month_data.overview.split('.')
        key_theme = overview_parts[0] if overview_parts else "General activities"
        
        # Get notable dates
        notable_dates = [event.date for event in month_data.high_score_days[:3]]
        
        # Create brief guidance from AI overview (first 2 sentences)
        brief_guidance = '. '.join(overview_parts[:2]) + '.' if len(overview_parts) >= 2 else month_data.overview
        if len(brief_guidance) > 200:
            brief_guidance = brief_guidance[:197] + "..."
        
        highlights.append(
            BriefMonthHighlight(
                month=month_data.month,
                month_number=i,
                key_theme=key_theme,
                energy_score=round(energy_score, 1),
                energy_level=energy_level,
                notable_dates=notable_dates,
                brief_guidance=brief_guidance,
            )
        )
    
    return highlights


def _build_life_area_summaries(months: List[Any]) -> List[BriefLifeArea]:
    """Build life area summaries from LLM-interpreted monthly data."""
    
    life_areas = []
    
    # Define life areas and their corresponding fields in monthly data
    area_mappings = {
        "Career & Finance": "career_and_finance",
        "Love & Romance": "love_and_romance",
        "Home & Family": "home_and_family",
        "Health & Wellness": "health_and_routines",
        "Growth & Learning": "growth_and_learning",
        "Inner Work": "inner_work",
    }
    
    for area_name, field_name in area_mappings.items():
        # Collect themes and calculate scores from each month's AI-generated content
        monthly_themes = []
        key_months = []
        content_scores = []
        
        # Keywords for sentiment analysis
        positive_keywords = [
            "opportunity", "growth", "expansion", "success", "favorable", "support", 
            "strengthen", "improve", "excel", "thrive", "prosper", "advance", "benefit",
            "positive", "fortune", "luck", "harmony", "flow", "ease", "progress"
        ]
        negative_keywords = [
            "challenge", "difficulty", "tension", "stress", "caution", "delay", 
            "obstacle", "conflict", "struggle", "pressure", "limitation", "setback",
            "careful", "mindful", "patience", "avoid", "warning", "concern"
        ]
        
        for month_data in months:
            content = getattr(month_data, field_name, "")
            if content and len(content) > 50:  # Substantial AI-generated content
                # Extract first sentence as theme
                theme = content.split('.')[0]
                monthly_themes.append(theme)
                key_months.append(month_data.month)
                
                # Analyze content for sentiment and calculate score
                content_lower = content.lower()
                positive_count = sum(1 for word in positive_keywords if word in content_lower)
                negative_count = sum(1 for word in negative_keywords if word in content_lower)
                
                # Content length bonus (more content = more significant)
                length_factor = min(len(content) / 500, 1.0)  # Cap at 500 chars
                
                # Calculate month score for this area
                # Base: 5.0, add positive sentiment, subtract negative, add length bonus
                month_score = 5.0 + (positive_count * 0.5) - (negative_count * 0.3) + (length_factor * 1.0)
                content_scores.append(month_score)
        
        # Determine yearly theme (most common theme or first significant one)
        yearly_theme = monthly_themes[0] if monthly_themes else f"Focus on {area_name.lower()}"
        
        # Calculate area score (0-10 scale) - average of all month scores
        if content_scores:
            area_score = sum(content_scores) / len(content_scores)
            area_score = max(0, min(10, area_score))  # Clamp to 0-10
        else:
            area_score = 5.0
        
        # Select top 3 key months (spread throughout year)
        if len(key_months) > 3:
            # Pick first, middle, and last
            key_months = [key_months[0], key_months[len(key_months)//2], key_months[-1]]
        
        # Create brief guidance from AI-generated content
        brief_guidance = f"{yearly_theme}. Key focus in {', '.join(key_months[:2])}."
        if len(brief_guidance) > 200:
            brief_guidance = brief_guidance[:197] + "..."
        
        life_areas.append(
            BriefLifeArea(
                area=area_name,
                yearly_theme=yearly_theme,
                score=round(area_score, 1),
                key_months=key_months[:3],
                brief_guidance=brief_guidance,
            )
        )
    
    return life_areas


def _extract_major_transits(full_report: Any) -> List[BriefTransit]:
    """Extract major transits from LLM-interpreted report."""
    
    transits = []
    
    # Look through top events for transit information (AI-generated summaries)
    for event in full_report.year_at_glance.top_events[:10]:
        # Extract transit info from AI-generated event
        if hasattr(event, 'date') and event.date:
            # Use AI-generated summary (truncated)
            summary = event.summary[:100] + "..." if len(event.summary) > 100 else event.summary
            
            transits.append(
                BriefTransit(
                    planet="Various",  # Could be parsed from title
                    event_type="major_aspect",
                    date=event.date,
                    impact_summary=summary,
                )
            )
    
    return transits


def _extract_eclipses(full_report: Any) -> List[BriefEclipse]:
    """Extract eclipse information with AI-generated guidance."""
    
    eclipses = []
    
    for eclipse_data in full_report.eclipses_and_lunations:
        # Parse eclipse kind from the kind field
        eclipse_kind = eclipse_data.kind.lower()
        if "solar" in eclipse_kind:
            eclipse_type = "solar"
        elif "lunar" in eclipse_kind:
            eclipse_type = "lunar"
        else:
            eclipse_type = "unknown"
        
        # Extract eclipse subtype
        if "total" in eclipse_kind:
            subtype = "total"
        elif "annular" in eclipse_kind:
            subtype = "annular"
        elif "partial" in eclipse_kind:
            subtype = "partial"
        else:
            subtype = "unknown"
        
        # Parse house number if available
        house = None
        if eclipse_data.house:
            try:
                house = int(eclipse_data.house.replace("House", "").strip())
            except:
                pass
        
        # Use AI-generated guidance (truncated)
        ai_guidance = eclipse_data.guidance[:150] + "..." if len(eclipse_data.guidance) > 150 else eclipse_data.guidance
        
        eclipses.append(
            BriefEclipse(
                date=eclipse_data.date,
                type=eclipse_type,
                eclipse_kind=subtype,
                sign=eclipse_data.sign or "Unknown",
                house=house,
                brief_impact=ai_guidance,
            )
        )
    
    return eclipses


def _extract_retrogrades(full_report: Any) -> List[Dict[str, Any]]:
    """Extract retrograde period information with AI-generated insights."""
    
    retrogrades = []
    
    # Look for retrograde mentions in AI-generated top events
    for event in full_report.year_at_glance.top_events:
        if "retrograde" in event.title.lower():
            # Use AI-generated summary (truncated)
            summary = event.summary[:100] + "..." if len(event.summary) > 100 else event.summary
            
            retrogrades.append({
                "title": event.title,
                "date": str(event.date) if event.date else None,
                "summary": summary,
            })
    
    return retrogrades[:5]  # Top 5 retrogrades


def _build_recommendations(full_report: Any) -> Dict[str, List[str]]:
    """Build recommendations from AI-interpreted report."""
    
    # Extract action items from the first month's planner (AI-generated)
    do_more = []
    if full_report.months and full_report.months[0].planner_actions:
        do_more = full_report.months[0].planner_actions[:3]
    
    # If not enough, use defaults
    if len(do_more) < 3:
        do_more = [
            "Focus on your key opportunities",
            "Plan important activities during favorable months",
            "Leverage high-energy days for major decisions",
        ]
    
    recommendations = {
        "do_more": do_more,
        "avoid": [
            "Making rushed decisions during challenging periods",
            "Overcommitting during caution days",
            "Ignoring rest and self-care",
        ],
        "focus_on": [
            "Personal growth and learning",
            "Building strong relationships",
            "Maintaining work-life balance",
        ],
    }
    
    return recommendations

