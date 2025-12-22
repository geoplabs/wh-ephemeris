from __future__ import annotations

from datetime import date as Date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .forecasts import YearlyForecastRequest as BaseYearlyForecastRequest


class YearlyForecastRequest(BaseYearlyForecastRequest):
    """Alias to reuse the existing yearly forecast request schema."""

    pass


class EventSummary(BaseModel):
    date: Date
    transit_body: str
    natal_body: Optional[str] = None
    aspect: Optional[str] = None
    score: float
    raw_note: str = ""
    section: Optional[str] = None
    user_friendly_summary: str = ""


class TopEventSummary(BaseModel):
    title: str
    date: Optional[Date] = None
    summary: str
    score: Optional[float] = None
    tags: List[str] = Field(default_factory=list)


class EclipseSummary(BaseModel):
    date: Date
    kind: str
    sign: Optional[str] = None
    house: Optional[str] = None
    guidance: str = ""  # Specific guidance for THIS eclipse (not general lunation guidance)


class MonthlySection(BaseModel):
    month: str
    overview: str
    high_score_days: List[EventSummary] = Field(default_factory=list)
    caution_days: List[EventSummary] = Field(default_factory=list)
    
    # Core life areas (always generated)
    career_and_finance: str  # Work, public life, money, resources (career + money themes)
    love_and_romance: str  # Dating, partnerships, romance (love theme)
    home_and_family: str  # Home, family, roots, community (home_family + community_goals themes)
    health_and_routines: str  # Health, wellness, daily life (health_routines theme)
    
    # Growth areas (combined)
    growth_and_learning: str  # Study, travel, creativity, mindset (study_travel + mindset_communication + creativity_children themes)
    inner_work: str  # Spirituality, inner work, innovation (inner_spiritual + innovation themes)
    
    aspect_grid: List[Dict[str, Any]] = Field(default_factory=list)
    rituals_and_journal: str
    planner_actions: List[str] = Field(default_factory=list)


class YearAtGlance(BaseModel):
    heatmap: List[Dict[str, Any]] = Field(default_factory=list)
    top_events: List[TopEventSummary] = Field(default_factory=list)
    commentary: str


class YearlyForecastReport(BaseModel):
    meta: Dict[str, Any]
    year_at_glance: YearAtGlance
    eclipse_guidance: str = ""  # Full LLM-generated guide (markdown) - rendered once
    eclipses_and_lunations: List[EclipseSummary] = Field(default_factory=list)
    months: List[MonthlySection]
    appendix_all_events: List[EventSummary] = Field(default_factory=list)
    glossary: Dict[str, str] = Field(default_factory=dict)
    interpretation_index: Dict[str, str] = Field(default_factory=dict)


class YearlyForecastReportResponse(BaseModel):
    report: YearlyForecastReport
    pdf_download_url: str
