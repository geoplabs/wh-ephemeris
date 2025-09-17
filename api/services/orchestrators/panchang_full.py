"""Build a Panchang viewmodel.

This implementation favours deterministic, lightweight calculations so the
API remains responsive inside the development container. The structure of
the returned payload mirrors the production contract which allows clients
and documentation to be exercised end-to-end.
"""

from __future__ import annotations

import time
from datetime import date as date_cls, datetime, time as time_cls, timedelta
from typing import Any, Dict, Optional

from zoneinfo import ZoneInfo

from ...schemas.panchang_viewmodel import (
    AssetsVM,
    HoraSpan,
    MuhurtaVM,
    PanchangViewModel,
    SegmentVM,
    SolarVM,
    LunarVM,
    TithiVM,
    MasaVM,
    HeaderVM,
    Span,
)
from ..panchang_algos import (
    compute_karana,
    compute_lunar_day,
    compute_masa,
    compute_moon_events,
    compute_nakshatra,
    compute_tithi,
    compute_yoga,
)
from ..muhurta import compute_horas, compute_muhurta_blocks
from ..day_strip_svg import build_day_strip_svg


CACHE: Dict[str, tuple[float, PanchangViewModel]] = {}
TTL_SECONDS = 900


def _format_iso(dt: datetime) -> str:
    return dt.isoformat()


def _format_duration(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _resolve_date(date_str: Optional[str], tz: ZoneInfo) -> date_cls:
    if date_str:
        return datetime.fromisoformat(date_str).date()
    return datetime.now(tz).date()


def _weekday_name(dt: date_cls) -> str:
    return dt.strftime("%A")


def _build_cache_key(date_value: date_cls, place: Dict[str, Any], options: Dict[str, Any]) -> str:
    ayanamsha = options.get("ayanamsha", "lahiri").lower()
    include_muhurta = bool(options.get("include_muhurta", True))
    include_hora = bool(options.get("include_hora", False))
    lat = float(place["lat"])
    lon = float(place["lon"])
    tz = place["tz"]
    return (
        f"panchang:{date_value.isoformat()}:{lat:.4f}:{lon:.4f}:{tz}:{ayanamsha}"
        f":{int(include_muhurta)}:{int(include_hora)}"
    )


def build_viewmodel(system: str, date_str: Optional[str], place: Dict[str, Any], options: Dict[str, Any]) -> PanchangViewModel:
    if system.lower() != "vedic":
        raise ValueError("Only vedic system is supported for Panchang")

    tz = ZoneInfo(place["tz"])
    target_date = _resolve_date(date_str, tz)
    options = options or {}

    key = _build_cache_key(target_date, place, options)
    cached = CACHE.get(key)
    now = time.time()
    if cached and cached[0] > now:
        return cached[1]

    vm = _build_viewmodel_uncached(target_date, place, options, tz)
    CACHE[key] = (now + TTL_SECONDS, vm)
    return vm


def _build_viewmodel_uncached(target_date: date_cls, place: Dict[str, Any], options: Dict[str, Any], tz: ZoneInfo) -> PanchangViewModel:
    ayanamsha = options.get("ayanamsha", "lahiri").lower()
    include_muhurta = bool(options.get("include_muhurta", True))
    include_hora = bool(options.get("include_hora", False))

    start_of_day = datetime.combine(target_date, time_cls(0, 0), tzinfo=tz)
    sunrise = start_of_day + timedelta(hours=6)
    sunset = start_of_day + timedelta(hours=18)
    next_sunrise = sunrise + timedelta(days=1)
    solar_noon = sunrise + (sunset - sunrise) / 2

    lunar_day_no, paksha = compute_lunar_day(start_of_day)
    moonrise, moonset = compute_moon_events(start_of_day, tz)
    tithi_number, tithi_name, tithi_start, tithi_end = compute_tithi(start_of_day, sunrise)
    nak_no, nak_name, nak_pada, nak_start, nak_end = compute_nakshatra(start_of_day, sunrise)
    yoga_name, yoga_start, yoga_end = compute_yoga(start_of_day, sunrise)
    karana_name, karana_start, karana_end = compute_karana(start_of_day, sunrise)
    amanta, purnimanta = compute_masa(start_of_day)

    span_note = None
    if tithi_start.date() != tithi_end.date():
        span_note = "Crosses civil midnight"

    muhurta_vm: Optional[MuhurtaVM] = None
    hora_vm: Optional[list[HoraSpan]] = None
    weekday = _weekday_name(target_date)
    muhurta_blocks = compute_muhurta_blocks(sunrise, sunset, weekday)
    if include_muhurta:
        muhurta_vm = MuhurtaVM(
            abhijit=Span(start_ts=_format_iso(muhurta_blocks["abhijit"][0]), end_ts=_format_iso(muhurta_blocks["abhijit"][1])),
            rahu_kal=Span(start_ts=_format_iso(muhurta_blocks["rahu_kal"][0]), end_ts=_format_iso(muhurta_blocks["rahu_kal"][1])),
            gulika_kal=Span(start_ts=_format_iso(muhurta_blocks["gulika_kal"][0]), end_ts=_format_iso(muhurta_blocks["gulika_kal"][1])),
            yamaganda=Span(start_ts=_format_iso(muhurta_blocks["yamaganda"][0]), end_ts=_format_iso(muhurta_blocks["yamaganda"][1])),
        )

    if include_hora:
        horas = compute_horas(sunrise, sunset, next_sunrise, weekday)
        hora_vm = [
            HoraSpan(start_ts=_format_iso(start), end_ts=_format_iso(end), lord=lord)
            for start, end, lord in horas
        ]

    assets = AssetsVM(day_strip_svg=build_day_strip_svg())

    vm = PanchangViewModel(
        header=HeaderVM(
            date_local=target_date.isoformat(),
            weekday=weekday,
            tz=place["tz"],
            place_label=place.get("query"),
            system="vedic",
            ayanamsha=ayanamsha,
        ),
        solar=SolarVM(
            sunrise=_format_iso(sunrise),
            sunset=_format_iso(sunset),
            solar_noon=_format_iso(solar_noon),
            day_length=_format_duration(sunset - sunrise),
        ),
        lunar=LunarVM(
            moonrise=moonrise,
            moonset=moonset,
            lunar_day_no=lunar_day_no,
            paksha=paksha,
        ),
        tithi=TithiVM(
            number=tithi_number,
            name=tithi_name,
            start_ts=_format_iso(tithi_start),
            end_ts=_format_iso(tithi_end),
            span_note=span_note,
        ),
        nakshatra=SegmentVM(
            number=nak_no,
            name=nak_name,
            pada=nak_pada,
            start_ts=_format_iso(nak_start),
            end_ts=_format_iso(nak_end),
        ),
        yoga=SegmentVM(name=yoga_name, start_ts=_format_iso(yoga_start), end_ts=_format_iso(yoga_end)),
        karana=SegmentVM(name=karana_name, start_ts=_format_iso(karana_start), end_ts=_format_iso(karana_end)),
        masa=MasaVM(amanta_name=amanta, purnimanta_name=purnimanta),
        muhurta=muhurta_vm,
        hora=hora_vm,
        notes=["Synthetic Panchang data for development"],
        assets=assets,
    )

    return vm

