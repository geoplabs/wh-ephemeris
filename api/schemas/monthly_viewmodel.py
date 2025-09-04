from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class HeaderM(BaseModel):
    name: Optional[str] = None
    year: int
    month: int  # 1..12
    system: str  # western | vedic
    zodiac: str  # tropical | sidereal
    ayanamsha: Optional[str] = None
    house_system: str
    time_known: bool
    place_label: Optional[str] = None


class KeyDateVM(BaseModel):
    date: str
    label: str
    domains: List[str] = []


class EventVM(BaseModel):
    title: str
    date: str
    transit_body: str
    natal_body: str
    aspect: str
    orb: float
    applying: Optional[bool] = None
    domains: List[str] = []
    severity: str  # subtle | notable | strong | major
    copy: Optional[str] = None
    notes: List[str] = []


class WeekBlockVM(BaseModel):
    summary: str
    tone: str  # supportive | mixed | testing
    top_events: List[EventVM]
    calendar: List[KeyDateVM]


class OverviewM(BaseModel):
    month_summary: str  # 3–5 lines
    tone: str  # supportive | mixed | testing
    key_themes: List[str]
    totals: Dict[str, int]  # supportive/challenging/transformational
    planet_activity: Dict[str, int]  # counts by transit planet


class VedicMVM(BaseModel):
    active_periods: List[Dict[str, Any]] = []  # dasha slices overlapping the month
    emphasis_notes: List[str] = []


class AssetsM(BaseModel):
    mini_calendar_svg: Optional[str] = None
    pdf_download_url: Optional[str] = None


class MonthlyViewModel(BaseModel):
    header: HeaderM
    overview: OverviewM
    weeks: Dict[str, WeekBlockVM]  # "W1", "W2", "W3", "W4/5"
    key_dates: List[KeyDateVM]
    vedic_extras: Optional[VedicMVM] = None
    assets: AssetsM = AssetsM()
