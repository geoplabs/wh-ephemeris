"""Build a Panchang viewmodel.

This implementation favours deterministic, lightweight calculations so the
API remains responsive inside the development container. The structure of
the returned payload mirrors the production contract which allows clients
and documentation to be exercised end-to-end.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date as date_cls, datetime, time as time_cls, timedelta, timezone
from typing import Any, Dict, Optional, List

from zoneinfo import ZoneInfo

from ...schemas.panchang_viewmodel import (
    AssetsVM,
    PanchangChanges,
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
    WindowsEntry,
    WindowsVM,
    ContextVM,
    SamvatsaraVM,
    MasaContextVM,
    RituContextVM,
    ZodiacContextVM,
    ObservanceVM,
)
from ..panchang_algos import (
    compute_solar_events,
    compute_lunar_day,
    compute_masa,
    compute_moon_events,
    compute_nakshatra,
    compute_rashi,
    compute_tithi,
    compute_yoga,
    enumerate_tithi_periods,
    enumerate_nakshatra_periods,
    enumerate_yoga_periods,
    enumerate_karana_periods,
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
from ..util.place_defaults import normalize_place
from ..ext_calendars import build_calendars_extended
from ..ext_ritu_dinmana import build_ritu_extended, ritu_drik, ritu_vedic
from ..ext_muhurta_extra import build_muhurta_extra
from ..ext_yoga_extended import build_yoga_extended
from ..ext_nivas_shool import build_nivas_and_shool
from ..ext_balam import build_balam
from ..ext_panchaka_lagna import build_panchaka_and_lagna
from ..festivals import festivals_for_date, merge_observances
from ..ritual_notes import notes_for_day
from .. import ephem


logger = logging.getLogger(__name__)


CACHE: Dict[str, tuple[float, PanchangViewModel]] = {}
TTL_SECONDS = 3600  # 1 hour cache for better performance


def _ext_enabled() -> bool:
    return os.getenv("PANCHANG_EXTENDED_ENABLED", "true").lower() == "true"


def _festivals_enabled() -> bool:
    return os.getenv("PANCHANG_EXT_FESTIVALS_ENABLED", "true").lower() == "true"


def _ritu_convention() -> str:
    return os.getenv("RITU_CONVENTION", "drik")

PLANET_NAME_TO_INDEX = {
    "Sun": 0,
    "Moon": 1,
    "Mars": 2,
    "Mercury": 3,
    "Jupiter": 4,
    "Venus": 5,
    "Saturn": 6,
}

RITU_ORDER = [
    "Vasanta",
    "Grishma",
    "Varsha",
    "Sharad",
    "Hemanta",
    "Shishira",
]

ZODIAC_EN = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


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
    include_extensions = bool(options.get("include_extensions", True))
    summary_only = bool(options.get("summary_only", False))
    lang = options.get("lang", "en")
    script = options.get("script", "latin")
    show_bilingual = bool(options.get("show_bilingual", False))
    lat = float(place["lat"])
    lon = float(place["lon"])
    tz = place["tz"]
    return (
        f"panchang:{date_value.isoformat()}:{lat:.4f}:{lon:.4f}:{tz}:{ayanamsha}"
        f":{int(include_muhurta)}:{int(include_hora)}:{int(include_extensions)}:{int(summary_only)}:{lang}:{script}:{int(show_bilingual)}"
    )


def build_viewmodel(
    system: str,
    date_str: Optional[str],
    place: Optional[Dict[str, Any]],
    options: Optional[Dict[str, Any]],
) -> PanchangViewModel:
    if system.lower() != "vedic":
        raise ValueError("Only vedic system is supported for Panchang")

    eff_place, flags = normalize_place(place)
    tz_name = eff_place["tz"]
    tz = ZoneInfo(tz_name)
    target_date = _resolve_date(date_str, tz)
    options = _normalize_options(options)

    if flags["default_reason"]:
        logger.info(
            "panchang.place.defaults",
            extra={
                "reason": flags["default_reason"],
                "lat": eff_place["lat"],
                "lon": eff_place["lon"],
                "tz": tz_name,
            },
        )

    key = _build_cache_key(target_date, eff_place, options)
    cached = CACHE.get(key)
    now = time.time()
    if cached and cached[0] > now:
        return cached[1]

    vm = _build_viewmodel_uncached(target_date, eff_place, options, tz, flags)
    CACHE[key] = (now + TTL_SECONDS, vm)
    return vm


def _build_viewmodel_uncached(
    target_date: date_cls,
    place: Dict[str, Any],
    options: Dict[str, Any],
    tz: ZoneInfo,
    meta_flags: Dict[str, Any],
) -> PanchangViewModel:
    ayanamsha = options.get("ayanamsha", "lahiri")
    include_muhurta = bool(options.get("include_muhurta", True))
    include_hora = bool(options.get("include_hora", False))
    include_extensions = bool(options.get("include_extensions", True))
    summary_only = bool(options.get("summary_only", False))
    lang = options.get("lang", "en")
    script = options.get("script", "latin")
    start_of_day = datetime.combine(target_date, time_cls(0, 0), tzinfo=tz)
    date_local_dt = datetime.combine(target_date, time_cls(12, 0), tzinfo=tz)
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

    observation_utc = date_local_dt.astimezone(timezone.utc)
    jd_observation = observation_utc.timestamp() / 86400.0 + 2440587.5
    sun_long_tropical = ephem.positions_ecliptic(jd_observation, sidereal=False)["Sun"]["lon"]
    sun_long_sidereal = ephem.positions_ecliptic(
        jd_observation, sidereal=True, ayanamsha=ayanamsha
    )["Sun"]["lon"]

    lunar_day_no, paksha = compute_lunar_day(sunrise, ayanamsha=ayanamsha)
    moonrise_dt, moonset_dt = compute_moon_events(start_of_day, lat, lon, elevation)
    moonrise = _format_iso(moonrise_dt) if moonrise_dt else None
    moonset = _format_iso(moonset_dt) if moonset_dt else None
    tithi_number, _tithi_name, tithi_start, tithi_end = compute_tithi(sunrise, ayanamsha=ayanamsha)
    nak_no, _nak_name, nak_pada, nak_start, nak_end = compute_nakshatra(sunrise, ayanamsha=ayanamsha)
    yoga_number, _yoga_name, yoga_start, yoga_end = compute_yoga(sunrise, ayanamsha=ayanamsha)
    amanta_idx, _amanta_name, purnimanta_idx, _purnimanta_name = compute_masa(sunrise, ayanamsha=ayanamsha)
    sun_rashi_index, sun_sign_name, moon_rashi_index, moon_sign_name = compute_rashi(sunrise, ayanamsha=ayanamsha)

    weekday_index = (target_date.weekday() + 1) % 7
    vara = vara_label(weekday_index, lang, script)
    tithi_names = tithi_label(tithi_number, paksha, lang, script)
    nak_names = nak_label(nak_no, lang, script)
    yoga_names = yoga_label(yoga_number, lang, script)
    karana_index = 0
    karana_start = sunrise
    karana_end = next_sunrise
    kar_names = karana_label(karana_index, lang, script)
    amanta_label = masa_label(amanta_idx, lang, script)
    purnimanta_label = masa_label(purnimanta_idx, lang, script)

    window_start_local = sunrise
    window_end_local = next_sunrise
    window_start_utc = window_start_local.astimezone(timezone.utc)
    window_end_utc = window_end_local.astimezone(timezone.utc)

    tithi_periods = enumerate_tithi_periods(
        window_start_utc, window_end_utc, lat, lon, ayanamsha
    )
    nakshatra_periods = enumerate_nakshatra_periods(
        window_start_utc, window_end_utc, lat, lon, ayanamsha
    )
    yoga_periods = enumerate_yoga_periods(
        window_start_utc, window_end_utc, lat, lon, ayanamsha
    )
    karana_periods = enumerate_karana_periods(
        window_start_utc, window_end_utc, lat, lon, ayanamsha
    )

    if karana_periods:
        current = karana_periods[0]
        karana_index = current["number"] - 1
        kar_names = karana_label(karana_index, lang, script)
        karana_start = current["start"].astimezone(tz)
        karana_end = current["end"].astimezone(tz)

    def _to_local_iso(dt: datetime) -> str:
        return _format_iso(dt.astimezone(tz))

    span_note = None
    if tithi_start.date() != tithi_end.date():
        span_note = "Crosses civil midnight"

    weekday = _weekday_name(target_date)
    
    # Skip expensive computations in summary mode
    muhurta_blocks = {}
    if include_muhurta and not summary_only:
        muhurta_blocks = compute_muhurta_blocks(sunrise, sunset, weekday)
    
    # windows will be built later after muhurtas_extra is available
    hora_labels = []
    horas_structured = None
    if include_hora:
        hora_labels = _build_horas(sunrise, sunset, next_sunrise, weekday, lang, script)
        horas_structured = _build_horas_structured(sunrise, sunset, next_sunrise, weekday, lang, script)

    # Skip SVG generation in summary mode
    day_strip_svg = None if summary_only else build_day_strip_svg()
    assets = AssetsVM(day_strip_svg=day_strip_svg)

    ritu_drik_name = ritu_drik(sun_long_tropical)
    ritu_vedic_name = ritu_vedic(sun_long_sidereal)

    masa_vm = MasaVM(
        amanta=MasaLabel(**amanta_label),
        purnimanta=MasaLabel(**purnimanta_label),
    )

    context = _build_context(
        target_date,
        masa_vm,
        sun_sign_name,
        moon_sign_name,
        ritu_drik_name,
        ritu_vedic_name,
    )

    vm = PanchangViewModel(
        header=HeaderVM(
            date_local=target_date.isoformat(),
            weekday=WeekdayVM(**vara),
            tz=place["tz"],
            place_label=place.get("query"),
            system="vedic",
            ayanamsha=ayanamsha,
            locale=LocaleVM(lang=lang, script=script),
            meta=meta_flags,
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
        windows=_build_windows(include_muhurta, muhurta_blocks),  # Initial windows, will be updated later
        context=context,
        observances=[],
        notes=_build_notes(include_hora, hora_labels),
        assets=assets,
        changes=PanchangChanges(
            tithi_periods=[
                {
                    "start_ts": _to_local_iso(period["start"]),
                    "end_ts": _to_local_iso(period["end"]),
                    "number": period.get("number"),
                    "name": period.get("name"),
                }
                for period in tithi_periods
            ],
            nakshatra_periods=[
                {
                    "start_ts": _to_local_iso(period["start"]),
                    "end_ts": _to_local_iso(period["end"]),
                    "number": period.get("number"),
                    "name": period.get("name"),
                    "pada": period.get("pada"),
                }
                for period in nakshatra_periods
            ],
            yoga_periods=[
                {
                    "start_ts": _to_local_iso(period["start"]),
                    "end_ts": _to_local_iso(period["end"]),
                    "number": period.get("number"),
                    "name": period.get("name"),
                }
                for period in yoga_periods
            ],
            karana_periods=[
                {
                    "start_ts": _to_local_iso(period["start"]),
                    "end_ts": _to_local_iso(period["end"]),
                    "number": period.get("number"),
                    "name": period.get("name"),
                    "pada": period.get("pada"),
                }
                for period in karana_periods
            ],
        ),
        horas=horas_structured,  # Include full hora data when include_hora=true
    )

    ext_on = _ext_enabled() and include_extensions
    ext_fest = _festivals_enabled() and include_extensions
    ritu_conv = _ritu_convention()

    # For summary_only mode, skip all expensive extensions
    if summary_only:
        ext_on = False
        ext_fest = False

    if ext_on:
        nak_periods = [period.model_dump() for period in vm.changes.nakshatra_periods]
        now_local = sunrise

        vm.calendars_extended = build_calendars_extended(date_local_dt, tz)
        vm.ritu_extended = build_ritu_extended(
            ritu_conv,
            sun_long_tropical,
            sun_long_sidereal,
            sunrise,
            sunset,
            next_sunrise,
        )
        vm.muhurtas_extra = build_muhurta_extra(
            sunrise,
            sunset,
            next_sunrise,
            solar_noon,
            weekday_index,
            sunset - sunrise,
            nak_periods,
            sun_long_sidereal,
            now_local,
        )
        
        # Update windows with actual muhurta calculations now that muhurtas_extra is available
        vm.windows = _build_windows(include_muhurta, muhurta_blocks, vm.muhurtas_extra)
        yoga_number = vm.yoga.number or 1
        vm.yoga_extended = build_yoga_extended(yoga_number)
        nak_number = vm.nakshatra.number or 1
        vm.nivas_and_shool = build_nivas_and_shool(weekday_index, vm.tithi.number, nak_number)
        moon_rashi = ZODIAC_EN[moon_rashi_index]
        vm.balam = build_balam(moon_rashi, nak_number, next_sunrise)
        vm.panchaka_and_lagna = build_panchaka_and_lagna(
            sunrise,
            sunset,
            nak_number,
            weekday_index,
            lat,
            lon,
            tz,
        )
        vm.ritual_notes = notes_for_day()
    else:
        # Even if extensions are disabled, we should still try to compute basic muhurtas
        # Build a minimal muhurtas_extra for basic calculations
        weekday_index = target_date.weekday()
        nak_periods = [period.model_dump() for period in vm.changes.nakshatra_periods]
        now_local = sunrise
        
        minimal_muhurtas_extra = build_muhurta_extra(
            sunrise,
            sunset,
            next_sunrise,
            solar_noon,
            weekday_index,
            sunset - sunrise,
            nak_periods,
            sun_long_sidereal,
            now_local,
        )
        
        # Update windows with actual calculations even when extensions are disabled
        vm.windows = _build_windows(include_muhurta, muhurta_blocks, minimal_muhurtas_extra)

    if ext_on and ext_fest:
        addl = festivals_for_date(date_local_dt, tz, lat, lon)
        merged = merge_observances(vm.observances, addl)
        vm.observances = [ObservanceVM(**obs) for obs in merged]

    return vm


def _build_windows(
    include_muhurta: bool,
    muhurta_blocks: Dict[str, tuple[datetime, datetime]],
    muhurtas_extra: Optional[Dict[str, List[Dict[str, str]]]] = None,
) -> WindowsVM:
    auspicious: List[WindowsEntry] = []
    inauspicious: List[WindowsEntry] = []

    if include_muhurta:
        abhijit = muhurta_blocks["abhijit"]
        auspicious.append(
            WindowsEntry(
                kind="abhijit",
                start_ts=_format_iso(abhijit[0]),
                end_ts=_format_iso(abhijit[1]),
            )
        )
    else:
        inauspicious.append(
            WindowsEntry(
                kind="abhijit",
                note="Abhijit window skipped by request",
            )
        )

    if include_muhurta:
        for key, kind in (
            ("rahu_kal", "rahu_kalam"),
            ("gulika_kal", "gulikai_kalam"),
            ("yamaganda", "yamaganda"),
        ):
            block = muhurta_blocks[key]
            inauspicious.append(
                WindowsEntry(
                    kind=kind,
                    start_ts=_format_iso(block[0]),
                    end_ts=_format_iso(block[1]),
                )
            )

    # Add actual muhurta calculations from muhurtas_extra if available
    if muhurtas_extra:
        # Add auspicious muhurtas (but skip ones already in basic muhurta_blocks)
        for muhurta in muhurtas_extra.get("auspicious_extra", []):
            kind = muhurta.get("kind")
            # Skip if already handled above
            if kind not in ["abhijit"]:
                start_ts = muhurta.get("start_ts")
                end_ts = muhurta.get("end_ts")
                note = muhurta.get("note")
                if start_ts and end_ts:
                    auspicious.append(
                        WindowsEntry(
                            kind=kind,
                            start_ts=start_ts,
                            end_ts=end_ts,
                            note=note,
                        )
                    )
        
        # Add inauspicious muhurtas from actual calculations
        for muhurta in muhurtas_extra.get("inauspicious_extra", []):
            kind = muhurta.get("kind")
            # Skip if already handled above
            if kind not in ["rahu_kalam", "gulikai_kalam", "yamaganda"]:
                start_ts = muhurta.get("start_ts")
                end_ts = muhurta.get("end_ts")
                note = muhurta.get("note")
                value = muhurta.get("value")
                
                if start_ts and end_ts:
                    inauspicious.append(
                        WindowsEntry(
                            kind=kind,
                            start_ts=start_ts,
                            end_ts=end_ts,
                            note=note,
                            value=value,
                        )
                    )
                elif kind == "baana" and note:
                    # Handle baana which might not have times but has a note
                    inauspicious.append(
                        WindowsEntry(
                            kind=kind,
                            start_ts=start_ts,
                            end_ts=end_ts,
                            note=note,
                            value=value,
                        )
                    )
    elif not muhurtas_extra:
        # Fallback to placeholder entries if muhurtas_extra not available
        auspicious.append(
            WindowsEntry(kind="amrit_kalam", note="Not computed in development build")
        )
        inauspicious.extend(
            [
                WindowsEntry(kind="varjyam", note="Not computed in development build"),
                WindowsEntry(kind="dur_muhurtam", note="Not computed in development build"),
                WindowsEntry(kind="bhadra", note="Not computed in development build"),
                WindowsEntry(kind="ganda_moola", note="Not computed in development build"),
                WindowsEntry(kind="baana", value="None", note="Not computed in development build"),
                WindowsEntry(kind="vidaal_yoga", note="Not computed in development build"),
            ]
        )

    auspicious.sort(key=lambda entry: entry.start_ts or "9999")
    inauspicious.sort(key=lambda entry: entry.start_ts or f"{entry.kind}~")
    return WindowsVM(auspicious=auspicious, inauspicious=inauspicious)


def _build_horas(
    sunrise: datetime,
    sunset: datetime,
    next_sunrise: datetime,
    weekday: str,
    lang: str,
    script: str,
) -> List[str]:
    """Build formatted hora strings for notes field (backward compatibility)."""
    horas = compute_horas(sunrise, sunset, next_sunrise, weekday)
    formatted: List[str] = []
    for start, end, lord in horas:
        label = planet_label(PLANET_NAME_TO_INDEX[lord], lang, script)["display_name"]
        formatted.append(f"{_format_iso(start)}→{_format_iso(end)} {label}")
    return formatted


def _build_horas_structured(
    sunrise: datetime,
    sunset: datetime,
    next_sunrise: datetime,
    weekday: str,
    lang: str,
    script: str,
) -> List[Dict[str, str]]:
    """Build structured hora data for the horas field."""
    horas = compute_horas(sunrise, sunset, next_sunrise, weekday)
    structured: List[Dict[str, str]] = []
    for start, end, lord in horas:
        label = planet_label(PLANET_NAME_TO_INDEX[lord], lang, script)["display_name"]
        structured.append({
            "planet": label,
            "start_ts": _format_iso(start),
            "end_ts": _format_iso(end)
        })
    return structured


def _build_context(
    target_date: date_cls,
    masa_vm: MasaVM,
    sun_sign_name: str,
    moon_sign_name: str,
    ritu_drik_name: str,
    ritu_vedic_name: str,
) -> ContextVM:
    vikram_year = target_date.year + 57
    shaka_year = target_date.year - 78

    # Map masa display name to English default for context summary.
    amanta_name = masa_vm.amanta.aliases.get("en", masa_vm.amanta.display_name)
    purnimanta_name = masa_vm.purnimanta.aliases.get("en", masa_vm.purnimanta.display_name)

    try:
        ritu_index = RITU_ORDER.index(ritu_drik_name)
    except ValueError:
        month_index = target_date.month - 1
        ritu_index = (month_index // 2) % len(RITU_ORDER)
        ritu_drik_name = RITU_ORDER[ritu_index]

    if ritu_vedic_name not in RITU_ORDER:
        ritu_vedic_name = ritu_drik_name

    ayana = "Uttarayana" if ritu_index in (0, 1, 2) else "Dakshinayana"

    sun_sign = _map_zodiac_to_en(sun_sign_name)
    moon_sign = _map_zodiac_to_en(moon_sign_name)

    return ContextVM(
        samvatsara=SamvatsaraVM(vikram=vikram_year, shaka=shaka_year),
        masa=MasaContextVM(amanta_name=amanta_name, purnimanta_name=purnimanta_name),
        ritu=RituContextVM(drik=ritu_drik_name, vedic=ritu_vedic_name),
        ayana=ayana,
        zodiac=ZodiacContextVM(sun_sign=sun_sign, moon_sign=moon_sign),
    )


def _map_zodiac_to_en(name: str) -> str:
    try:
        idx = ZODIAC_EN.index(name)
        return ZODIAC_EN[idx]
    except ValueError:
        # Fallback for Sanskrit spellings.
        mapping = {
            "Mesha": "Aries",
            "Vrishabha": "Taurus",
            "Mithuna": "Gemini",
            "Karka": "Cancer",
            "Simha": "Leo",
            "Kanya": "Virgo",
            "Tula": "Libra",
            "Vrischika": "Scorpio",
            "Dhanu": "Sagittarius",
            "Makara": "Capricorn",
            "Kumbha": "Aquarius",
            "Meena": "Pisces",
        }
        return mapping.get(name, name)


def _build_notes(include_hora: bool, hora_labels: List[str]) -> List[str]:
    notes = ["All times are local with standard refraction.", "Panchang day considered sunrise→next sunrise."]
    if include_hora and hora_labels:
        notes.append("Horas: " + "; ".join(hora_labels))
    return notes

