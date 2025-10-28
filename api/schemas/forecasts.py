from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, conlist
from typing import Optional, List, Dict, Any
from .charts import ChartInput


class YearlyOptions(BaseModel):
    year: int
    user_id: Optional[str] = None
    profile_name: Optional[str] = None
    step_days: int = 1
    include_progressions: bool = True
    transit_bodies: List[str] = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
    aspects: Dict[str, Any] = {
        "types": ["conjunction", "opposition", "square", "trine", "sextile"],
        "orb_deg": 3.0,
    }


class MonthOptions(BaseModel):
    year: int
    month: int
    user_id: Optional[str] = None
    profile_name: Optional[str] = None
    step_days: int = 1
    transit_bodies: List[str] = [
        "Sun",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Moon",
    ]
    aspects: Dict[str, Any] = {
        "types": ["conjunction", "square", "trine", "opposition"],
        "orb_deg": 3.0,
    }


class DailyOptions(BaseModel):
    date: str
    user_id: Optional[str] = None
    profile_name: Optional[str] = None
    use_ai: bool = False  # Enable/disable AI generation (OpenAI)
    step_days: int = 1
    window_days: int = 1
    use_ai: Optional[bool] = None
    areas: List[str] = ["career", "love", "health", "finance"]
    transit_bodies: List[str] = [
        "Sun",
        "Moon",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
    ]
    natal_targets: Optional[List[str]] = None
    aspects: Dict[str, Any] = {
        "types": ["conjunction", "square", "trine", "opposition", "sextile"],
        "orb_deg": 3.0,
    }


class ForecastEvent(BaseModel):
    date: str
    transit_body: str
    natal_body: str
    aspect: str
    orb: float
    score: float
    note: Optional[str] = None
    transit_sign: Optional[str] = None
    natal_sign: Optional[str] = None
    zodiac: Optional[str] = None


class YearlyForecastRequest(BaseModel):
    chart_input: ChartInput
    options: YearlyOptions


class MonthlyForecastRequest(BaseModel):
    chart_input: ChartInput
    options: MonthOptions


class DailyForecastRequest(BaseModel):
    chart_input: ChartInput
    options: DailyOptions


class YearlyForecastResponse(BaseModel):
    meta: Dict[str, Any]
    months: Dict[str, List[ForecastEvent]]
    top_events: List[ForecastEvent]
    pdf_download_url: Optional[str] = None


class MonthlyForecastResponse(BaseModel):
    meta: Dict[str, Any]
    events: List[ForecastEvent]
    highlights: List[ForecastEvent]
    pdf_download_url: Optional[str] = None


class DailyFocusArea(BaseModel):
    area: str
    score: float
    headline: str
    guidance: str
    events: List[ForecastEvent]


class LuckyDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color: str
    time_window: str
    direction: str
    affirmation: str


class CautionWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_window: str
    note: str


class DailyForecastResponse(BaseModel):
    meta: Dict[str, Any]
    summary: str
    mood: str
    focus_areas: List[DailyFocusArea]
    events: List[ForecastEvent]
    top_events: List[ForecastEvent]
    lucky: LuckyDetails


class MorningMindset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph: str
    mantra: str


class SectionWithBullets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph: str
    bullets: conlist(str, min_length=0, max_length=4) = Field(default_factory=list)


class LoveSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph: str
    attached: str
    single: str


class HealthSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph: str
    good_options: conlist(str, min_length=0, max_length=4) = Field(default_factory=list)


class DailyTemplatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_name: str
    date: str
    mood: str
    theme: str
    opening_summary: str
    morning_mindset: MorningMindset
    career: SectionWithBullets
    love: LoveSection
    health: HealthSection
    finance: SectionWithBullets
    do_today: conlist(str, min_length=0, max_length=4) = Field(default_factory=list)
    avoid_today: conlist(str, min_length=0, max_length=4) = Field(default_factory=list)
    caution_window: CautionWindow
    remedies: conlist(str, min_length=0, max_length=4) = Field(default_factory=list)
    lucky: LuckyDetails
    one_line_summary: str
