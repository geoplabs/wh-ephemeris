from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .forecasts import YearlyForecastRequest as BaseYearlyForecastRequest


class YearlyForecastRequest(BaseYearlyForecastRequest):
    """Alias to reuse the existing yearly forecast request schema."""

    pass


class EventSummary(BaseModel):
    date: date
    transit_body: str
    natal_body: Optional[str] = None
    aspect: Optional[str] = None
    score: float
    raw_note: str = ""
    section: Optional[str] = None
    user_friendly_summary: str = ""


class TopEventSummary(BaseModel):
    title: str
    date: Optional[date] = None
    summary: str
    score: Optional[float] = None
    tags: List[str] = Field(default_factory=list)


class EclipseSummary(BaseModel):
    date: date
    kind: str
    sign: Optional[str] = None
    house: Optional[str] = None
    guidance: str


class MonthlySection(BaseModel):
    month: str
    overview: str
    high_score_days: List[EventSummary] = Field(default_factory=list)
    caution_days: List[EventSummary] = Field(default_factory=list)
    career_and_finance: str
    relationships_and_family: str
    health_and_energy: str
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
    eclipses_and_lunations: List[EclipseSummary] = Field(default_factory=list)
    months: List[MonthlySection]
    appendix_all_events: List[EventSummary] = Field(default_factory=list)
    glossary: Dict[str, str] = Field(default_factory=dict)
    interpretation_index: Dict[str, str] = Field(default_factory=dict)


class YearlyForecastReportResponse(BaseModel):
    report: YearlyForecastReport
    pdf_download_url: str
