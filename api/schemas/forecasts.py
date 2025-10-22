from pydantic import BaseModel
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
    step_days: int = 1
    window_days: int = 1
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


class DailyForecastResponse(BaseModel):
    meta: Dict[str, Any]
    summary: str
    mood: str
    focus_areas: List[DailyFocusArea]
    events: List[ForecastEvent]
    top_events: List[ForecastEvent]
