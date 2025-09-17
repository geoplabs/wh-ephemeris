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
    MasaLabel,
    MasaVM,
    HeaderVM,
    WeekdayVM,
    LocaleVM,
    Span,
)
from ..panchang_algos import (
    compute_solar_events,
    compute_karana,
    compute_lunar_day,
    compute_masa,
    compute_moon_events,
    compute_nakshatra,
    compute_rashi,
    compute_tithi,
    compute_yoga,
)
from ..muhurta import compute_horas, compute_muhurta_blocks
from ..day_strip_svg import build_day_strip_svg
from ...i18n.resolve import (
    clamp_lang,
    clamp_script,
    vara_label,
    tithi_label,
    nak_label,
    yoga_label,
    karana_label,
    masa_label,
    planet_label,
)


CACHE: Dict[str, tuple[float, PanchangViewModel]] = {}
TTL_SECONDS = 900

PLANET_NAME_TO_INDEX = {
    "Sun": 0,
    "Moon": 1,
    "Mars": 2,
    "Mercury": 3,
    "Jupiter": 4,
    "Venus": 5,
    "Saturn": 6,
}


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


def _normalize_options(options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    opts = dict(options or {})
    opts["ayanamsha"] = opts.get("ayanamsha", "lahiri").lower()
    opts["include_muhurta"] = bool(opts.get("include_muhurta", True))
    opts["include_hora"] = bool(opts.get("include_hora", False))
    opts["lang"] = clamp_lang(opts.get("lang"))
    opts["script"] = clamp_script(opts.get("script"))
    opts["show_bilingual"] = bool(opts.get("show_bilingual", False))
    return opts


def _build_cache_key(date_value: date_cls, place: Dict[str, Any], options: Dict[str, Any]) -> str:
    ayanamsha = options.get("ayanamsha", "lahiri")
    include_muhurta = bool(options.get("include_muhurta", True))
    include_hora = bool(options.get("include_hora", False))
    lang = options.get("lang", "en")
    script = options.get("script", "latin")
    show_bilingual = bool(options.get("show_bilingual", False))
    lat = float(place["lat"])
    lon = float(place["lon"])
    tz = place["tz"]
    return (
        f"panchang:{date_value.isoformat()}:{lat:.4f}:{lon:.4f}:{tz}:{ayanamsha}"
        f":{int(include_muhurta)}:{int(include_hora)}:{lang}:{script}:{int(show_bilingual)}"
    )


def build_viewmodel(system: str, date_str: Optional[str], place: Dict[str, Any], options: Dict[str, Any]) -> PanchangViewModel:
    if system.lower() != "vedic":
        raise ValueError("Only vedic system is supported for Panchang")

    tz = ZoneInfo(place["tz"])
    target_date = _resolve_date(date_str, tz)
    options = _normalize_options(options)

    key = _build_cache_key(target_date, place, options)
    cached = CACHE.get(key)
    now = time.time()
    if cached and cached[0] > now:
        return cached[1]

    vm = _build_viewmodel_uncached(target_date, place, options, tz)
    CACHE[key] = (now + TTL_SECONDS, vm)
    return vm


def _build_viewmodel_uncached(target_date: date_cls, place: Dict[str, Any], options: Dict[str, Any], tz: ZoneInfo) -> PanchangViewModel:
    ayanamsha = options.get("ayanamsha", "lahiri")
    include_muhurta = bool(options.get("include_muhurta", True))
    include_hora = bool(options.get("include_hora", False))
    lang = options.get("lang", "en")
    script = options.get("script", "latin")
    show_bilingual = bool(options.get("show_bilingual", False))

    start_of_day = datetime.combine(target_date, time_cls(0, 0), tzinfo=tz)
    lat = float(place["lat"])
    lon = float(place["lon"])
    elevation = float(place.get("elevation", 0.0))

    sunrise, sunset, next_sunrise = compute_solar_events(start_of_day, lat, lon, elevation)

    if sunrise is None:
        sunrise = start_of_day + timedelta(hours=6)
    if sunset is None:
        sunset = start_of_day + timedelta(hours=18)
    if next_sunrise is None:
        next_sunrise = sunrise + timedelta(days=1)

    solar_noon = sunrise + (sunset - sunrise) / 2

    lunar_day_no, paksha = compute_lunar_day(sunrise)
    paksha_display = paksha.capitalize() + " Paksha"
    moonrise_dt, moonset_dt = compute_moon_events(start_of_day, lat, lon, elevation)
    moonrise = _format_iso(moonrise_dt) if moonrise_dt else None
    moonset = _format_iso(moonset_dt) if moonset_dt else None
    tithi_number, _tithi_name, tithi_start, tithi_end = compute_tithi(sunrise)
    nak_no, _nak_name, nak_pada, nak_start, nak_end = compute_nakshatra(sunrise)
    yoga_number, _yoga_name, yoga_start, yoga_end = compute_yoga(sunrise)
    karana_index, _karana_name, karana_start, karana_end = compute_karana(sunrise)
    amanta_idx, _amanta_name, purnimanta_idx, _purnimanta_name = compute_masa(sunrise)
    _, sun_sign_name, _, moon_sign_name = compute_rashi(sunrise)

    weekday_index = (target_date.weekday() + 1) % 7
    vara = vara_label(weekday_index, lang, script)
    tithi_names = tithi_label(tithi_number, paksha, lang, script)
    nak_names = nak_label(nak_no, lang, script)
    yoga_names = yoga_label(yoga_number, lang, script)
    kar_names = karana_label(karana_index, lang, script)
    amanta_label = masa_label(amanta_idx, lang, script)
    purnimanta_label = masa_label(purnimanta_idx, lang, script)

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
            HoraSpan(
                start_ts=_format_iso(start),
                end_ts=_format_iso(end),
                lord=planet_label(PLANET_NAME_TO_INDEX[lord], lang, script),
            )
            for start, end, lord in horas
        ]

    assets = AssetsVM(day_strip_svg=build_day_strip_svg())

    masa_vm = MasaVM(
        amanta=MasaLabel(**amanta_label),
        purnimanta=MasaLabel(**purnimanta_label),
    )

    bilingual_helper: Optional[Dict[str, str]] = None
    if show_bilingual and lang == "hi":
        bilingual_helper = {
            "tithi_en": tithi_names["aliases"].get("en"),
            "tithi_hi": tithi_names["aliases"].get("hi"),
        }

    vm = PanchangViewModel(
        header=HeaderVM(
            date_local=target_date.isoformat(),
            weekday=WeekdayVM(**vara),
            tz=place["tz"],
            place_label=place.get("query"),
            system="vedic",
            ayanamsha=ayanamsha,
            locale=LocaleVM(lang=lang, script=script),
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
            paksha=paksha_display,
        ),
        tithi=TithiVM(
            number=tithi_number,
            display_name=tithi_names["display_name"],
            aliases=tithi_names["aliases"],
            start_ts=_format_iso(tithi_start),
            end_ts=_format_iso(tithi_end),
            span_note=span_note,
        ),
        nakshatra=SegmentVM(
            number=nak_no,
            display_name=nak_names["display_name"],
            aliases=nak_names["aliases"],
            pada=nak_pada,
            start_ts=_format_iso(nak_start),
            end_ts=_format_iso(nak_end),
        ),
        yoga=SegmentVM(
            display_name=yoga_names["display_name"],
            aliases=yoga_names["aliases"],
            number=yoga_number,
            start_ts=_format_iso(yoga_start),
            end_ts=_format_iso(yoga_end),
        ),
        karana=SegmentVM(
            display_name=kar_names["display_name"],
            aliases=kar_names["aliases"],
            number=karana_index + 1,
            start_ts=_format_iso(karana_start),
            end_ts=_format_iso(karana_end),
        ),
        masa=masa_vm,
        muhurta=muhurta_vm,
        hora=hora_vm,
        notes=[
            "Swiss Ephemeris derived Panchang data for development",
            f"Sun sign: {sun_sign_name}",
            f"Moon sign: {moon_sign_name}",
        ],
        assets=assets,
        bilingual=bilingual_helper,
    )

    return vm

