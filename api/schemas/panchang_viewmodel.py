"""Panchang viewmodel schemas used by the Panchang API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict


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
    meta: Optional[Dict[str, Any]] = None


class MasaVM(BaseModel):
    amanta: MasaLabel
    purnimanta: MasaLabel


class WindowsEntry(BaseModel):
    kind: str
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None
    note: Optional[str] = None
    value: Optional[str] = None


class WindowsVM(BaseModel):
    auspicious: List[WindowsEntry] = Field(default_factory=list)
    inauspicious: List[WindowsEntry] = Field(default_factory=list)


class SamvatsaraVM(BaseModel):
    vikram: int
    shaka: int


class MasaContextVM(BaseModel):
    amanta_name: str
    purnimanta_name: str


class RituContextVM(BaseModel):
    drik: str
    vedic: str


class ZodiacContextVM(BaseModel):
    sun_sign: str
    moon_sign: str


class ContextVM(BaseModel):
    samvatsara: SamvatsaraVM
    masa: MasaContextVM
    ritu: RituContextVM
    ayana: str
    zodiac: ZodiacContextVM


class ObservanceVM(BaseModel):
    title: str
    type: str


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
    windows: WindowsVM
    context: ContextVM
    observances: List[ObservanceVM] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    assets: AssetsVM = AssetsVM()

