"""Panchang viewmodel schemas used by the Panchang API endpoints."""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, List


class Span(BaseModel):
    start_ts: str
    end_ts: str


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


class TithiVM(Span):
    number: int
    name: str
    span_note: Optional[str] = None


class SegmentVM(Span):
    name: str
    number: Optional[int] = None
    pada: Optional[int] = None


class MasaVM(BaseModel):
    amanta_name: str
    purnimanta_name: str


class MuhurtaVM(BaseModel):
    abhijit: Optional[Span] = None
    rahu_kal: Span
    gulika_kal: Span
    yamaganda: Span


class HoraSpan(BaseModel):
    start_ts: str
    end_ts: str
    lord: str


class HeaderVM(BaseModel):
    date_local: str
    weekday: str
    tz: str
    place_label: Optional[str] = None
    system: str
    ayanamsha: str


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
    notes: List[str] = []
    assets: AssetsVM = AssetsVM()

