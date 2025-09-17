"""Panchang viewmodel schemas used by the Panchang API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class Span(BaseModel):
    start_ts: str
    end_ts: str


class LabelledValue(BaseModel):
    display_name: str
    aliases: Dict[str, str]


class SolarVM(BaseModel):
    sunrise: str
    sunset: str
    solar_noon: str
    day_length: str


class LunarVM(BaseModel):
    moonrise: Optional[str] = None
    moonset: Optional[str] = None
    lunar_day_no: int
    paksha: str


class LabelledSpan(Span):
    display_name: str
    aliases: Dict[str, str]


class TithiVM(LabelledSpan):
    number: int
    span_note: Optional[str] = None


class SegmentVM(LabelledSpan):
    number: Optional[int] = None
    pada: Optional[int] = None


class MasaLabel(LabelledValue):
    pass


class MasaVM(BaseModel):
    amanta: MasaLabel
    purnimanta: MasaLabel


class MuhurtaVM(BaseModel):
    abhijit: Optional[Span] = None
    rahu_kal: Span
    gulika_kal: Span
    yamaganda: Span


class HoraSpan(BaseModel):
    start_ts: str
    end_ts: str
    lord: LabelledValue


class WeekdayVM(LabelledValue):
    pass


class LocaleVM(BaseModel):
    lang: str
    script: str


class HeaderVM(BaseModel):
    date_local: str
    weekday: WeekdayVM
    tz: str
    place_label: Optional[str] = None
    system: str
    ayanamsha: str
    locale: LocaleVM


class AssetsVM(BaseModel):
    day_strip_svg: Optional[str] = None
    pdf_download_url: Optional[str] = None


class PanchangViewModel(BaseModel):
    header: HeaderVM
    solar: SolarVM
    lunar: LunarVM
    tithi: TithiVM
    nakshatra: SegmentVM
    yoga: SegmentVM
    karana: SegmentVM
    masa: MasaVM
    samvatsara: Optional[str] = None
    muhurta: Optional[MuhurtaVM] = None
    hora: Optional[List[HoraSpan]] = None
    notes: List[str] = Field(default_factory=list)
    assets: AssetsVM = AssetsVM()
    bilingual: Optional[Dict[str, str]] = None

