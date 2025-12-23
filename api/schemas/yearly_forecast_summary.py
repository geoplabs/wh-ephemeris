"""Schema for fast, free yearly forecast summary."""

from datetime import date as Date
from typing import List, Optional
from pydantic import BaseModel, Field


class ChartSignature(BaseModel):
    """Core natal chart identity."""
    sun_sign: str
    sun_house: int
    moon_sign: str
    moon_house: int
    ascendant_sign: str


class YearlySummaryOverview(BaseModel):
    """High-level yearly overview."""
    year: int
    chart_signature: ChartSignature
    yearly_theme: str  # 1-2 sentences
    energy_level: str  # "expansive", "balanced", "introspective"
    top_opportunities: List[str] = Field(default_factory=list, max_items=3)
    top_challenges: List[str] = Field(default_factory=list, max_items=3)


class KeyMonth(BaseModel):
    """Simplified month highlight."""
    month: str  # "2026-01"
    name: str  # "January"
    energy: str  # "high", "moderate", "low"
    key_event: Optional[str] = None  # Brief description


class QuickLifeArea(BaseModel):
    """Template-based life area summary."""
    area: str
    outlook: str  # "favorable", "mixed", "challenging"
    one_liner: str  # Single sentence summary


class KeyTransit(BaseModel):
    """Top transit for the year."""
    date: Date
    event: str  # "Sun conjunct natal Jupiter"
    impact: str  # "positive", "neutral", "challenging"


class YearlyForecastSummaryResponse(BaseModel):
    """Fast, free yearly forecast summary response."""
    person_name: str
    birth_date: Date
    year: int
    overview: YearlySummaryOverview
    best_months: List[KeyMonth] = Field(default_factory=list, max_items=3)
    life_areas: List[QuickLifeArea] = Field(default_factory=list)
    key_transits: List[KeyTransit] = Field(default_factory=list, max_items=5)
    generated_at: str
    system: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "person_name": "User",
                "birth_date": "1990-05-15",
                "year": 2026,
                "overview": {
                    "year": 2026,
                    "chart_signature": {
                        "sun_sign": "Taurus",
                        "sun_house": 10,
                        "moon_sign": "Cancer",
                        "moon_house": 12,
                        "ascendant_sign": "Leo"
                    },
                    "yearly_theme": "A year of professional growth and emotional depth, with opportunities to align your career ambitions with your inner values.",
                    "energy_level": "expansive",
                    "top_opportunities": [
                        "Career advancement in your field",
                        "Deepening emotional connections",
                        "Financial stability growth"
                    ],
                    "top_challenges": [
                        "Balancing work and personal life",
                        "Managing increased responsibilities",
                        "Adapting to change"
                    ]
                },
                "best_months": [
                    {
                        "month": "2026-03",
                        "name": "March",
                        "energy": "high",
                        "key_event": "Jupiter activates your career sector"
                    }
                ],
                "life_areas": [
                    {
                        "area": "Career",
                        "outlook": "favorable",
                        "one_liner": "Professional opportunities align with your ambitions this year."
                    }
                ],
                "key_transits": [
                    {
                        "date": "2026-03-15",
                        "event": "Jupiter trine natal Sun",
                        "impact": "positive"
                    }
                ],
                "generated_at": "2025-12-23T00:00:00",
                "system": "western"
            }
        }

