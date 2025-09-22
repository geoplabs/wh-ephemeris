"""Extended calendar helpers used by the Panchang orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from math import floor
from typing import Dict


def _ensure_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def julian_day(dt_utc: datetime) -> float:
    """Return the astronomical Julian Day number for a UTC moment."""

    dt_utc = _ensure_aware(dt_utc).astimezone(timezone.utc)

    year = dt_utc.year
    month = dt_utc.month
    day = dt_utc.day + (
        dt_utc.hour / 24.0
        + dt_utc.minute / 1440.0
        + dt_utc.second / 86400.0
        + dt_utc.microsecond / 86400_000_000.0
    )

    if month <= 2:
        year -= 1
        month += 12

    a = floor(year / 100)
    b = 2 - a + floor(a / 4)

    return (
        floor(365.25 * (year + 4716))
        + floor(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )


def modified_julian_day(jd: float) -> float:
    return jd - 2400000.5


def vikram_samvat(date_local: datetime) -> int:
    return date_local.year + 57


def shaka_samvat(date_local: datetime) -> int:
    return date_local.year - 78


def gujarati_samvat(date_local: datetime) -> int:
    return date_local.year + 56


def _julian_calendar_to_jd(year: int, month: int, day: float) -> float:
    if month <= 2:
        year -= 1
        month += 12
    return (
        floor(365.25 * (year + 4716))
        + floor(30.6001 * (month + 1))
        + day
        - 1524.5
    )


KALI_YUGA_START_JD = _julian_calendar_to_jd(-3101, 2, 18.0)


def kali_ahargana(date_local: datetime) -> int:
    dt = datetime(
        date_local.year,
        date_local.month,
        date_local.day,
        tzinfo=date_local.tzinfo or timezone.utc,
    )
    jd_today = julian_day(dt.astimezone(timezone.utc))
    return int(floor(jd_today - KALI_YUGA_START_JD))


def national_nirayana_date(date_local: datetime, tz) -> Dict[str, int]:
    local_dt = _ensure_aware(date_local).astimezone(tz)
    date_value = local_dt.date()
    return {"year": date_value.year - 78, "month": date_value.month, "day": date_value.day}


def build_calendars_extended(date_local: datetime, tzinfo) -> Dict[str, object]:
    dt_utc = _ensure_aware(date_local).astimezone(timezone.utc)
    jd = julian_day(dt_utc)
    return {
        "vikram_samvat": vikram_samvat(date_local),
        "shaka_samvat": shaka_samvat(date_local),
        "gujarati_samvat": gujarati_samvat(date_local),
        "kali_ahargana": kali_ahargana(date_local),
        "julian_day": jd,
        "modified_julian_day": modified_julian_day(jd),
        "national_nirayana_date": national_nirayana_date(date_local, tzinfo),
    }
