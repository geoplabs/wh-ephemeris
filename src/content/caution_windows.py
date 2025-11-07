from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Mapping, Sequence


UTC = timezone.utc

MAX_ORB_DEGREES = {
    "conjunction": 8.0,
    "sextile": 4.0,
    "trine": 6.0,
    "square": 6.0,
    "opposition": 8.0,
    "quincunx": 3.0,
}

ASPECT_WEIGHTS = {
    "sextile": -0.8,
    "trine": -1.0,
    "square": 1.4,
    "opposition": 1.6,
    "quincunx": 0.8,
}

ASPECT_SYMBOLS = {
    "conjunction": "☌",
    "sextile": "✶",
    "trine": "△",
    "square": "□",
    "opposition": "☍",
    "quincunx": "⚻",
}

MALEFIC_BODIES = {"mars", "saturn"}
BENEFIC_BODIES = {"venus", "jupiter"}

TRANSIT_WEIGHTS = {
    "moon": 1.4,
    "mercury": 1.2,
    "venus": 1.0,
    "sun": 1.0,
    "mars": 1.4,
    "saturn": 1.8,
    "jupiter": 0.8,
    "uranus": 1.2,
    "neptune": 0.8,
    "pluto": 1.3,
    "chiron": 0.8,
}

FAST_BODIES = {"moon", "mercury", "venus", "sun", "mars"}
SLOW_BODIES = {"saturn", "jupiter", "uranus", "neptune", "pluto", "chiron"}

ANGLE_NAMES = {"asc", "ascendant", "mc", "midheaven", "dc", "ic"}

MODALITY_BY_SIGN = {
    "aries": "cardinal",
    "taurus": "fixed",
    "gemini": "mutable",
    "cancer": "cardinal",
    "leo": "fixed",
    "virgo": "mutable",
    "libra": "cardinal",
    "scorpio": "fixed",
    "sagittarius": "mutable",
    "capricorn": "cardinal",
    "aquarius": "fixed",
    "pisces": "mutable",
}


@dataclass
class EventRecord:
    event: Mapping[str, Any]
    score: float
    start: datetime | None
    end: datetime | None
    exact_utc: datetime | None
    local_date: datetime.date | None
    orb: float
    aspect: str
    phase: str
    transit_body: str
    natal_body: str
    natal_type: str
    supportive: bool


@dataclass
class WindowRecord:
    start: datetime
    end: datetime
    contributors: list[EventRecord] = field(default_factory=list)


def _normalize_aspect(aspect: str) -> str:
    lowered = (aspect or "").strip().lower()
    if lowered in {"quin", "quinc", "inconjunct"}:
        return "quincunx"
    return lowered


def _normalize_body(name: str) -> str:
    return (name or "").strip()


def _normalize_body_lower(name: str) -> str:
    return _normalize_body(name).lower()


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _within_orb(orb: float | None, aspect: str) -> bool:
    if orb is None:
        return False
    max_orb = MAX_ORB_DEGREES.get(aspect)
    if max_orb is None:
        return False
    return orb <= max_orb


def _orb_factor(orb: float, aspect: str, power: float = 1.4) -> float:
    max_orb = MAX_ORB_DEGREES[aspect]
    ratio = min(max(orb / max_orb, 0.0), 1.0)
    return max(0.0, 1.0 - math.pow(ratio, power))


def _phase_multiplier(phase: str) -> float:
    if (phase or "").strip().lower() == "separating":
        return 0.6
    return 1.0


def _motion_multiplier(motion: str | None) -> float:
    if (motion or "").strip().lower() == "retrograde":
        return 1.1
    return 1.0


def _transit_weight(body: str) -> float:
    return TRANSIT_WEIGHTS.get(body.lower(), 1.0)


def _natal_weight(body: str, point_type: str) -> float:
    point_lower = (point_type or "").strip().lower()
    body_lower = body.lower()
    if point_lower == "angle" or body_lower in ANGLE_NAMES:
        return 1.6
    if body_lower in {"sun", "moon"}:
        return 1.4
    if body_lower in {"mercury", "venus", "mars"}:
        return 1.2
    return 1.0


def _aspect_weight(aspect: str, transit_body: str, natal_body: str) -> float:
    if aspect == "conjunction":
        transit_lower = transit_body.lower()
        natal_lower = natal_body.lower()
        if transit_lower in MALEFIC_BODIES or natal_lower in MALEFIC_BODIES:
            return 1.2
        if transit_lower in BENEFIC_BODIES or natal_lower in BENEFIC_BODIES:
            return -0.8
        # Reduced from 0.6 to 0.4 for more conservative neutral conjunction scoring
        return 0.4
    return ASPECT_WEIGHTS.get(aspect, 0.0)


def _sign_multiplier(transit_sign: str, natal_sign: str, aspect: str) -> float:
    transit_mod = MODALITY_BY_SIGN.get((transit_sign or "").strip().lower())
    natal_mod = MODALITY_BY_SIGN.get((natal_sign or "").strip().lower())
    if aspect in {"square", "opposition"} and transit_mod and natal_mod and transit_mod == natal_mod:
        return 1.1
    return 1.0


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_event_date(value: str | None) -> date | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        try:
            dt = datetime.strptime(cleaned, "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    else:
        dt = dt.replace(tzinfo=UTC)
    return dt.date()


def _infer_window(event: Mapping[str, Any], exact_utc: datetime | None) -> tuple[datetime, datetime] | None:
    transit_body = _normalize_body_lower(event.get("transit_body"))
    date_str = (event.get("date") or "").strip()
    if exact_utc is not None:
        center = exact_utc.astimezone(UTC)
        
        # Check for enhanced window hours from advanced features
        enhanced_hours = event.get("enhanced_window_hours")
        if enhanced_hours and enhanced_hours > 0:
            # Use enhanced window for outer planets with hard aspects
            delta = timedelta(hours=enhanced_hours)
        elif transit_body == "moon":
            delta = timedelta(minutes=90)
        elif transit_body in {"mercury", "venus", "sun"}:
            delta = timedelta(hours=2)
        elif transit_body == "mars":
            delta = timedelta(hours=3)
        elif transit_body in SLOW_BODIES:
            # Check for station info - stations get extended windows
            station_info = event.get("station_info")
            if station_info and station_info.get("is_station"):
                # Use station window from advanced features
                station_hours = station_info.get("window_hours", 48)
                delta = timedelta(hours=station_hours)
            else:
                return None
        else:
            delta = timedelta(hours=2)
        return center - delta, center + delta

    if transit_body not in FAST_BODIES:
        return None

    if not date_str:
        return None

    try:
        day = datetime.fromisoformat(date_str)
    except ValueError:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None
    if day.tzinfo is None:
        day = day.replace(tzinfo=UTC)
    else:
        day = day.astimezone(UTC)

    if transit_body == "moon":
        start_time = time(10, 0)
        end_time = time(14, 0)
    else:
        start_time = time(12, 0)
        end_time = time(16, 0)
    start = datetime.combine(day.date(), start_time, UTC)
    end = datetime.combine(day.date(), end_time, UTC)
    return start, end


def _support_ratio(contributors: Sequence[EventRecord]) -> float:
    total = sum(abs(record.score) for record in contributors if record.score != 0)
    if total == 0:
        return 0.0
    support = sum(abs(record.score) for record in contributors if record.score < 0)
    return support / total


def _has_angle_trigger(contributors: Sequence[EventRecord]) -> bool:
    for record in contributors:
        event = record.event
        if record.score <= 0:
            continue
        aspect = record.aspect
        if aspect not in {"square", "opposition"}:
            continue
        phase = (record.phase or "").lower()
        if phase != "applying":
            continue
        if record.orb > 1.0:
            continue
        natal_type = (record.natal_type or "").lower()
        natal_body = record.natal_body.lower()
        if natal_type == "angle" or natal_body in ANGLE_NAMES:
            return True
    return False


def _downgrade_severity(level: str) -> str:
    order = ["No flag", "Gentle Note", "Caution", "High Caution"]
    try:
        index = order.index(level)
    except ValueError:
        return level
    if index == 0:
        return level
    return order[index - 1]


def _severity_label(score: float, contributors: Sequence[EventRecord]) -> str:
    if score <= -0.6:
        if any("chiron" in record.transit_body.lower() or "chiron" in record.natal_body.lower() for record in contributors if record.score < 0):
            return "Insight"
        return "Support"
    if score <= 0.4:
        return "No flag"
    if score <= 1.2:
        return "Gentle Note"
    if score <= 2.4:
        return "Caution"
    return "High Caution"


def _note_for_severity(severity: str, contributors: Sequence[EventRecord]) -> str:
    base = {
        "Gentle Note": "Mild friction—go slow on decisions; keep messages short.",
        "Caution": "Expect bumps in this window—clarify, pause, then decide.",
        "High Caution": "Tension is high—avoid big calls if possible.",
        "Support": "Supportive window—simple steps flow; share a kind word.",
        "Insight": "Good time for inner work—small honest adjustments help.",
    }.get(severity)
    if severity in {"Gentle Note", "Caution", "High Caution"}:
        ratio = _support_ratio(contributors)
        if ratio >= 0.35:
            softener = "Tension with support—clarify and proceed in small steps."
            if base:
                return f"{base} {softener}"
            return softener
    return base or ""


def _pro_notes(contributors: Sequence[EventRecord]) -> str:
    if not contributors:
        return ""
    segments: list[str] = []
    for idx, record in enumerate(contributors[:2]):
        body = record.transit_body
        natal = record.natal_body
        symbol = ASPECT_SYMBOLS.get(record.aspect, record.aspect)
        orb_text = f"{record.orb:.2f}°" if record.orb is not None else "?"
        phase = (record.phase or "").lower() or "applying"
        if record.score >= 0:
            descriptor = "dominates" if idx == 0 else "adds friction"
        else:
            descriptor = "provides support"
        segments.append(f"{body}{symbol}{natal} ({orb_text}, {phase}) {descriptor}")
    return "; ".join(segments)


def _event_record(event: Mapping[str, Any]) -> EventRecord | None:
    aspect_raw = event.get("aspect")
    aspect = _normalize_aspect(str(aspect_raw or ""))
    if aspect not in MAX_ORB_DEGREES:
        return None
    orb = _parse_float(event.get("orb"))
    if orb is None or not _within_orb(orb, aspect):
        return None

    transit_body = _normalize_body(event.get("transit_body"))
    natal_body = _normalize_body(event.get("natal_body"))
    transit_lower = transit_body.lower()
    natal_lower = natal_body.lower()

    w_aspect = _aspect_weight(aspect, transit_lower, natal_lower)
    if w_aspect == 0:
        return None

    transit_weight = _transit_weight(transit_lower)
    natal_weight = _natal_weight(natal_body or "", str(event.get("natal_point_type") or ""))
    orb_factor = _orb_factor(orb, aspect)
    phase_multiplier = _phase_multiplier(str(event.get("phase") or ""))
    motion_multiplier = _motion_multiplier(event.get("transit_motion"))
    sign_multiplier = _sign_multiplier(
        str(event.get("transit_sign") or ""),
        str(event.get("natal_sign") or ""),
        aspect,
    )

    # Calculate base score
    base_score = (
        w_aspect
        * transit_weight
        * natal_weight
        * orb_factor
        * phase_multiplier
        * motion_multiplier
        * sign_multiplier
    )
    
    # Use adjusted score from transits_engine if available (includes advanced features)
    # Otherwise fall back to base_score calculated here
    score = event.get("score", base_score)
    
    if score == 0:
        return None

    exact = _parse_iso_utc(event.get("exact_hit_time_utc"))
    start_end = _infer_window(event, exact)
    exact_utc = exact.astimezone(UTC) if exact is not None else None
    if start_end:
        local_date = start_end[0].date()
    elif exact_utc is not None:
        local_date = exact_utc.date()
    else:
        local_date = _parse_event_date(event.get("date"))

    return EventRecord(
        event=event,
        score=score,
        start=start_end[0] if start_end else None,
        end=start_end[1] if start_end else None,
        exact_utc=exact_utc,
        local_date=local_date,
        orb=orb,
        aspect=aspect,
        phase=str(event.get("phase") or ""),
        transit_body=transit_body or "",
        natal_body=natal_body or "",
        natal_type=str(event.get("natal_point_type") or ""),
        supportive=score < 0,
    )


def _window_center(window: WindowRecord) -> datetime:
    return window.start + (window.end - window.start) / 2


def _merge_windows(windows: list[WindowRecord]) -> list[WindowRecord]:
    if not windows:
        return []
    windows.sort(key=lambda item: item.start)
    merged: list[WindowRecord] = [windows[0]]
    # Reduced from 60 to 30 minutes to avoid over-merging distinct Moon windows
    tolerance = timedelta(minutes=30)
    for window in windows[1:]:
        prev = merged[-1]
        if window.start <= prev.end + tolerance:
            prev.end = max(prev.end, window.end)
            prev.contributors.extend(window.contributors)
        else:
            merged.append(window)
    return merged


def _cap_score(score: float) -> float:
    return max(min(score, 3.5), -3.5)


def _format_time_window(start: datetime, end: datetime) -> str:
    start_utc = start.astimezone(UTC)
    end_utc = end.astimezone(UTC)
    start_str = start_utc.strftime("%H:%M")
    end_str = end_utc.strftime("%H:%M")
    window = f"{start_str}-{end_str} UTC"

    # Add clarity when a window continues into the next day (or beyond).
    # This happens for longer influence periods that span midnight in UTC.
    day_delta = (end_utc.date() - start_utc.date()).days
    if day_delta == 1:
        return f"{window} (next day)"
    if day_delta > 1:
        return f"{window} (+{day_delta} days)"
    return window


def compute_caution_windows(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Compute caution/support windows from transit events."""

    records: list[EventRecord] = []
    for event in events:
        if not isinstance(event, Mapping):
            continue
        record = _event_record(event)
        if record is not None:
            records.append(record)

    if not records:
        return []

    windows: list[WindowRecord] = []
    background: list[EventRecord] = []

    for record in records:
        if record.start is not None and record.end is not None:
            windows.append(WindowRecord(start=record.start, end=record.end, contributors=[record]))
        else:
            background.append(record)

    if not windows:
        return []

    merged = _merge_windows(windows)

    # Attach slow/background events with exact timings to nearby windows.
    attached_background: list[EventRecord] = []
    for record in list(background):
        if record.exact_utc is None:
            continue
        best_window: WindowRecord | None = None
        best_distance = timedelta.max
        for window in merged:
            center = _window_center(window)
            distance = abs(center - record.exact_utc)
            if distance <= timedelta(hours=12) and distance < best_distance:
                best_distance = distance
                best_window = window
        if best_window:
            best_window.contributors.append(record)
            attached_background.append(record)

    background = [record for record in background if record not in attached_background]

    # Fix: Only add non-None dates to prevent global boost
    positive_background_dates: set[date] = set()
    for record in background:
        if record.score > 0 and record.local_date is not None:
            positive_background_dates.add(record.local_date)

    results: list[dict[str, Any]] = []

    for window in merged:
        contributors = sorted(window.contributors, key=lambda rec: abs(rec.score), reverse=True)
        if not contributors:
            continue

        raw_score = sum(rec.score for rec in contributors)

        window_date = window.start.date()
        boost = 1.0
        if window_date in positive_background_dates:
            boost = 1.1

        adjusted_score = _cap_score(raw_score * boost)
        severity = _severity_label(adjusted_score, contributors)

        if severity in {"Caution", "High Caution", "Gentle Note"}:
            if all(rec.score <= 0 for rec in contributors):
                severity = "Support" if adjusted_score <= -0.6 else "No flag"

        # Only upgrade to Caution if the aspect is actually challenging (positive score)
        # Don't upgrade supportive aspects (Support/Insight) just because they involve angles
        if _has_angle_trigger(contributors) and severity in {"No flag", "Gentle Note"}:
            severity = "Caution"

        # Only downgrade Moon windows if Moon is the TOP FRICTION driver with wide orb
        top_record = contributors[0]
        if (top_record.transit_body.lower() == "moon" and 
            top_record.score > 0 and 
            top_record.orb > 3.0):
            severity = _downgrade_severity(severity)

        if severity == "No flag":
            continue

        note = _note_for_severity(severity, contributors)

        drivers = []
        for record in contributors[:2]:
            drivers.append(
                {
                    "transit_body": record.transit_body,
                    "natal_body": record.natal_body,
                    "aspect": record.event.get("aspect", record.aspect),
                    "orb": round(record.orb, 2),
                    "phase": record.phase,
                    "weight": round(record.score, 2),
                }
            )

        pro_notes = _pro_notes(contributors)

        start_utc = window.start.astimezone(UTC)
        end_utc = window.end.astimezone(UTC)

        results.append(
            {
                "start_utc": start_utc.isoformat().replace("+00:00", "Z"),
                "end_utc": end_utc.isoformat().replace("+00:00", "Z"),
                "time_window_utc": _format_time_window(start_utc, end_utc),
                "severity": severity,
                "score": round(adjusted_score, 2),
                "drivers": drivers,
                "note": note,
                "pro_notes": pro_notes,
            }
        )

    results.sort(key=lambda item: abs(item["score"]), reverse=True)
    return results[:2]


__all__ = ["compute_caution_windows"]
