from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from .charts import ChartInput


class YearlyOptions(BaseModel):
    year: int
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


class YearlyForecastResponse(BaseModel):
    meta: Dict[str, Any]
    months: Dict[str, List[ForecastEvent]]
    top_events: List[ForecastEvent]


class MonthlyForecastResponse(BaseModel):
    meta: Dict[str, Any]
    events: List[ForecastEvent]
    highlights: List[ForecastEvent]
