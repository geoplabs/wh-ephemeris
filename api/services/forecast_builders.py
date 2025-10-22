from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .transits_engine import compute_transits


_AREA_BODY_MAP = {
    "career": {"Sun", "Saturn", "Jupiter", "Midheaven"},
    "love": {"Venus", "Moon", "Mars", "Sun"},
    "health": {"Sun", "Mars", "Moon", "Ascendant", "Chiron"},
    "finance": {"Venus", "Jupiter", "Saturn", "Pluto"},
    "family": {"Moon", "Venus", "Sun"},
    "friendship": {"Venus", "Mercury", "Uranus"},
    "spirituality": {"Neptune", "Pluto", "TrueNode"},
    "personal_growth": {"Jupiter", "TrueNode", "Pluto"},
}


def _shift_date(date_str: str, days: int) -> str:
    base = datetime.fromisoformat(date_str)
    return (base + timedelta(days=days)).date().isoformat()


def _note_parts(note: str) -> tuple[str, str]:
    if not note:
        return "Stay mindful of subtle shifts today.", "Use the quieter tone to observe your rhythms."
    sections = [seg.strip() for seg in note.split(".") if seg.strip()]
    if not sections:
        return note, "Lean into activities that help you stay centered."
    headline = sections[0]
    guidance = ". ".join(sections[1:]) if len(sections) > 1 else "Lean into activities that help you stay centered."
    return headline, guidance


def _mood_from_score(score: float) -> str:
    if score >= 8.0:
        return "vibrant"
    if score >= 6.5:
        return "motivated"
    if score >= 5.0:
        return "steady"
    if score >= 3.5:
        return "reflective"
    return "restorative"


def _area_focus(area: str, events: List[Dict[str, Any]], fallback_guidance: str) -> Dict[str, Any]:
    key = area.lower().replace(" ", "_")
    bodies = _AREA_BODY_MAP.get(key, set())
    ranked = [e for e in events if e["natal_body"] in bodies or e["transit_body"] in bodies]
    ranked.sort(key=lambda e: -e["score"])
    if ranked:
        primary = ranked[0]
        headline, guidance = _note_parts(primary.get("note", ""))
        score = primary.get("score", 0.0)
        return {
            "area": area,
            "score": score,
            "headline": headline,
            "guidance": guidance or fallback_guidance,
            "events": ranked[:3],
        }
    return {
        "area": area,
        "score": 0.0,
        "headline": "Keep things simple and consistent.",
        "guidance": fallback_guidance,
        "events": [],
    }


def yearly_payload(chart_input: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    year = options["year"]
    opts = {
        "from_date": f"{year}-01-01",
        "to_date": f"{year}-12-31",
        "step_days": options.get("step_days", 1),
        "transit_bodies": options.get("transit_bodies"),
        "aspects": options.get("aspects"),
    }
    events = compute_transits(chart_input, opts)
    months = defaultdict(list)
    for e in events:
        key = e["date"][:7]
        months[key].append(e)
    top = sorted(events, key=lambda x: -x["score"])[:20]
    return {"months": dict(months), "top_events": top}


def monthly_payload(chart_input: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    y, m = options["year"], options["month"]
    from_d, to_d = f"{y}-{m:02d}-01", f"{y}-{m:02d}-28"
    opts = {
        "from_date": from_d,
        "to_date": to_d,
        "step_days": options.get("step_days", 1),
        "transit_bodies": options.get("transit_bodies"),
        "aspects": options.get("aspects"),
    }
    events = compute_transits(chart_input, opts)
    highlights = sorted(events, key=lambda x: -x["score"])[:10]
    return {"events": events, "highlights": highlights}


def daily_payload(chart_input: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    date = options["date"]
    window = max(0, int(options.get("window_days", 1)))
    from_d = _shift_date(date, -window)
    to_d = _shift_date(date, window)
    opts = {
        "from_date": from_d,
        "to_date": to_d,
        "step_days": options.get("step_days", 1),
        "transit_bodies": options.get("transit_bodies"),
        "aspects": options.get("aspects"),
        "natal_targets": options.get("natal_targets"),
    }
    events = compute_transits(chart_input, opts)
    core_events = [e for e in events if e["date"] == date]
    reference = core_events if core_events else events
    top_events = sorted(reference, key=lambda x: -x["score"])[:5]
    top_score = top_events[0]["score"] if top_events else 0.0
    profile_name = options.get("profile_name")
    areas = options.get("areas") or ["career", "love", "health", "finance"]
    fallback_guidance = "Use today to nurture steady momentum." if not profile_name else f"{profile_name}, use today to nurture steady momentum."
    if not fallback_guidance.endswith("."):
        fallback_guidance = f"{fallback_guidance}."
    focus = [_area_focus(area, reference, fallback_guidance) for area in areas]
    headline = "A gentle day to focus on your inner compass"
    guidance = fallback_guidance
    if top_events:
        headline, guidance = _note_parts(top_events[0].get("note", ""))
    summary = f"{headline}. {guidance}".strip()
    if not summary.endswith("."):
        summary = f"{summary}."
    if profile_name:
        if summary:
            adjusted = summary[0].lower() + summary[1:] if len(summary) > 1 else summary.lower()
        else:
            adjusted = "stay present with the day."
        summary = f"{profile_name}, {adjusted}"
    mood = _mood_from_score(top_score)
    meta = {
        "date": date,
        "areas": areas,
        "profile_name": profile_name,
        "window_days": window,
    }
    return {
        "meta": meta,
        "summary": summary,
        "mood": mood,
        "focus_areas": focus,
        "events": reference,
        "top_events": top_events,
    }
