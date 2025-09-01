from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class HeaderVM(BaseModel):
    name: Optional[str] = None
    system: str
    zodiac: str
    house_system: str
    ayanamsha: Optional[str] = None
    time_known: bool
    place_label: Optional[str] = None


class AngleVM(BaseModel):
    ascendant: Optional[float] = None
    mc: Optional[float] = None


class HouseVM(BaseModel):
    num: int
    cusp_lon: float


class BodyVM(BaseModel):
    name: str
    sign: str
    house: Optional[int] = None
    lon: float
    retro: Optional[bool] = None
    speed: Optional[float] = None
    nakshatra: Optional[Dict[str, Any]] = None


class AspectVM(BaseModel):
    p1: str
    p2: str
    type: str
    orb: float
    applying: Optional[bool] = None


class AnalysisVM(BaseModel):
    elements_balance: Dict[str, int]
    modalities_balance: Dict[str, int]
    dignities: List[Dict[str, str]]
    retrogrades: List[str]
    chart_notes: List[str]
    strengths: List[str] = []
    growth: List[str] = []


class InterpretationVM(BaseModel):
    summary: Optional[str] = None
    domains: Dict[str, str] = {}
    highlights: List[str] = []


class DashaVM(BaseModel):
    maha: Optional[str] = None
    antar: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None


class VedicExtrasVM(BaseModel):
    moon_nakshatra: Optional[Dict[str, Any]] = None
    current_dasha: Optional[DashaVM] = None


class RemedyVM(BaseModel):
    planet: str
    issue: str
    recommendation: str
    gemstone: Optional[str] = None
    cautions: List[str] = []


class AssetsVM(BaseModel):
    wheel_svg: Optional[str] = None
    pdf_download_url: Optional[str] = None


class CoreChartVM(BaseModel):
    angles: Optional[AngleVM] = None
    houses: Optional[List[HouseVM]] = None
    bodies: List[BodyVM]
    aspects: List[AspectVM]
    warnings: Optional[List[str]] = None


class NatalViewModel(BaseModel):
    header: HeaderVM
    core_chart: CoreChartVM
    analysis: AnalysisVM
    interpretation: InterpretationVM
    vedic_extras: Optional[VedicExtrasVM] = None
    remedies: List[RemedyVM] = []
    assets: AssetsVM = AssetsVM()
