"""
Schema for brief yearly forecast JSON response.
Provides a concise summary without generating a PDF.
"""

from __future__ import annotations

from datetime import date as Date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NotableDate(BaseModel):
    """A notable date with context."""
    date: Date
    type: str  # "opportunity", "caution", "eclipse", "major_transit"
    event: str  # What's happening (e.g., "Mars trine Jupiter", "Solar Eclipse")
    brief_note: str  # Why it's notable (1 sentence)


class BriefMonthHighlight(BaseModel):
    """Brief monthly highlight."""
    month: str  # "January", "February", etc.
    month_number: int  # 1-12
    key_theme: str  # Main theme for the month
    energy_score: float  # 0-10 scale
    energy_level: str  # "very favorable", "good", "balanced", "challenging", "difficult"
    notable_dates: List[NotableDate] = Field(default_factory=list)
    brief_guidance: str  # 1-2 sentences


class BriefLifeArea(BaseModel):
    """Brief summary for a life area."""
    area: str  # "Career", "Love", "Health", etc.
    yearly_theme: str  # Main theme for the year
    score: float = Field(..., ge=0, le=10, description="Energy score for this life area (0-10)")
    key_months: List[str] = Field(default_factory=list)  # ["March", "August"]
    brief_guidance: str  # 2-3 sentences


class BriefTransit(BaseModel):
    """Brief transit description."""
    planet: str
    event_type: str  # "ingress", "retrograde", "direct"
    date: Date
    sign: Optional[str] = None
    impact_summary: str  # 1 sentence


class BriefEclipse(BaseModel):
    """Brief eclipse description."""
    date: Date
    type: str  # "solar" or "lunar"
    eclipse_kind: str  # "total", "annular", "partial"
    sign: str
    house: Optional[int] = None
    brief_impact: str  # 1-2 sentences


class BriefYearlyOverview(BaseModel):
    """Overall yearly summary."""
    year: int
    main_themes: List[str] = Field(default_factory=list)  # 3-5 main themes
    overall_energy: str  # "expansive", "introspective", "transformative", etc.
    energy_score: float  # 0-10 scale for the year
    key_opportunities: List[str] = Field(default_factory=list)  # 3-5 opportunities
    key_challenges: List[str] = Field(default_factory=list)  # 3-5 challenges
    best_months: List[str] = Field(default_factory=list)  # ["March", "July"]
    challenging_months: List[str] = Field(default_factory=list)


class BriefYearlyForecastResponse(BaseModel):
    """
    Brief yearly forecast response - concise JSON format.
    No PDF generation, just essential information.
    """
    
    # Metadata
    person_name: Optional[str] = None
    birth_date: Date
    year: int
    
    # Overview
    overview: BriefYearlyOverview
    
    # Monthly highlights (12 entries, one per month)
    monthly_highlights: List[BriefMonthHighlight] = Field(default_factory=list)
    
    # Life area summaries (6-8 main areas)
    life_areas: List[BriefLifeArea] = Field(default_factory=list)
    
    # Major transits (top 10-15 most significant)
    major_transits: List[BriefTransit] = Field(default_factory=list)
    
    # Eclipses for the year
    eclipses: List[BriefEclipse] = Field(default_factory=list)
    
    # Retrogrades (Mercury, Venus, Mars if applicable)
    retrograde_periods: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Quick recommendations
    recommendations: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Quick tips: 'do_more', 'avoid', 'focus_on'"
    )
    
    # Generation metadata
    generated_at: str
    system: str  # "vedic" or "western"


# Request schema can reuse the existing one
from .yearly_forecast_report import YearlyForecastRequest

__all__ = [
    "BriefYearlyForecastResponse",
    "BriefYearlyOverview",
    "BriefMonthHighlight",
    "BriefLifeArea",
    "BriefTransit",
    "BriefEclipse",
    "NotableDate",
    "YearlyForecastRequest",  # Re-export for convenience
]

