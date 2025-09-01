from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class HeaderY(BaseModel):
    name: Optional[str] = None
    year: int
    system: str
    zodiac: str
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
    date: Optional[str] = None
    window: Optional[List[str]] = None
    peak_date: Optional[str] = None
    transit_body: str
    natal_body: str
    aspect: str
    orb: float
    applying: Optional[bool] = None
    domains: List[str] = []
    severity: str
    copy: Optional[str] = None
    notes: List[str] = []


class MonthBlockVM(BaseModel):
    summary: str
    tone: str
    top_events: List[EventVM]
    calendar: List[KeyDateVM]


class OverviewVM(BaseModel):
    key_themes: List[str]
    domains_summary: Dict[str, str]
    totals: Dict[str, int]
    planet_activity: Dict[str, int]


class DashaSliceVM(BaseModel):
    level: int
    lord: str
    start: str
    end: str


class VedicYVM(BaseModel):
    active_periods: List[DashaSliceVM] = []
    emphasis_notes: List[str] = []


class AssetsY(BaseModel):
    timeline_svg: Optional[str] = None
    calendar_svg: Optional[str] = None
    pdf_download_url: Optional[str] = None


class YearlyViewModel(BaseModel):
    header: HeaderY
    overview: OverviewVM
    months: Dict[str, MonthBlockVM]
    key_dates: List[KeyDateVM]
    vedic_extras: Optional[VedicYVM] = None
    assets: AssetsY = AssetsY()
