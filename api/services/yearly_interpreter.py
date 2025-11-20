"""Interpret yearly forecast payloads into narrative report sections."""

from __future__ import annotations

import asyncio
import datetime as dt
import re
from typing import Any, Dict, Iterable, List, Optional, Set

from ..schemas.yearly_forecast_report import (
    EclipseSummary,
    EventSummary,
    MonthlySection,
    TopEventSummary,
    YearAtGlance,
    YearlyForecastReport,
)
from .llm_client import LLMUnavailableError, generate_section_text

SUPPORTIVE_ASPECTS = {"trine", "sextile", "conjunction"}
CHALLENGING_ASPECTS = {"square", "opposition", "quincunx"}

SYSTEM_PROMPT = (
    "You are an empathetic, practical astrologer writing a yearly report. "
    "Use second person, encouraging tone, avoid fatalistic language, and never offer medical or financial promises."
)


_THEMES: Dict[str, Set[str]] = {
    "career": {"midheaven", "saturn", "jupiter", "sun", "mars"},
    "relationships": {"venus", "moon", "descendant", "juno"},
    "health": {"chiron", "ascendant", "sun", "mars"},
    "spiritual": {"neptune", "pluto", "true node", "south node"},
    "innovation": {"uranus", "mercury"},
}


def classify_event(event: Dict[str, Any]) -> Set[str]:
    """Assign high-level themes to an event using simple heuristics."""

    themes: Set[str] = set()
    note = (event.get("note") or "").lower()
    bodies = {str(event.get("transit_body", "")).lower(), str(event.get("natal_body", "")).lower()}
    for theme, markers in _THEMES.items():
        if bodies & markers:
            themes.add(theme)
    if any(tok in note for tok in ["career", "work", "income", "finance", "promotion"]):
        themes.add("career")
    if any(tok in note for tok in ["love", "partner", "relationship", "family", "marriage"]):
        themes.add("relationships")
    if any(tok in note for tok in ["health", "vitality", "rest", "energy", "body"]):
        themes.add("health")
    if any(tok in note for tok in ["spiritual", "intuition", "dream", "healing"]):
        themes.add("spiritual")
    if any(tok in note for tok in ["change", "innovation", "reinvent", "pivot"]):
        themes.add("innovation")
    return themes or {"general"}


def _event_summary(event: Dict[str, Any]) -> EventSummary:
    themes = classify_event(event)
    return EventSummary(
        date=dt.date.fromisoformat(str(event.get("date"))),
        transit_body=str(event.get("transit_body")),
        natal_body=event.get("natal_body"),
        aspect=event.get("aspect"),
        score=float(event.get("score", 0.0)),
        raw_note=str(event.get("note") or ""),
        section=next(iter(themes)),
        user_friendly_summary=str(event.get("note") or ""),
    )


def _build_heatmap(months: Dict[str, List[EventSummary]]) -> List[Dict[str, Any]]:
    heatmap = []
    for month, events in months.items():
        intensity = sum(abs(ev.score) for ev in events)
        peak_score = max((ev.score for ev in events), default=0.0)
        heatmap.append({"month": month, "intensity": intensity, "peak_score": peak_score})
    return sorted(heatmap, key=lambda item: item["month"])


def _extract_eclipses(events: Iterable[EventSummary]) -> List[EclipseSummary]:
    eclipses: List[EclipseSummary] = []
    for ev in events:
        note = ev.raw_note.lower()
        if (ev.aspect and ev.aspect.lower() == "eclipse") or any(
            key in note for key in ["eclipse", "new moon", "full moon"]
        ):
            eclipses.append(
                EclipseSummary(
                    date=ev.date,
                    kind=ev.aspect or "eclipse",
                    sign=None,
                    house=None,
                    guidance=ev.user_friendly_summary or ev.raw_note or "Stay observant and grounded.",
                )
            )
    return eclipses


def build_year_overview_prompt(meta: Dict[str, Any], top_events: List[TopEventSummary], heatmap: List[Dict[str, Any]]) -> str:
    return (
        "Summarize the year based on these signals."
        f" Meta: {meta}. Top events: {[e.model_dump() for e in top_events]}. "
        f"Heatmap (month intensity): {heatmap}."
        " Provide a motivating overview for the reader."
    )


def build_month_overview_prompt(month_key: str, month_events: List[EventSummary], themes: Set[str]) -> str:
    condensed = [
        {
            "date": ev.date.isoformat(),
            "transit": ev.transit_body,
            "natal": ev.natal_body,
            "aspect": ev.aspect,
            "score": ev.score,
            "note": ev.raw_note,
            "section": ev.section,
        }
        for ev in month_events[:12]
    ]
    return (
        f"Write a month overview for {month_key} summarizing key themes {sorted(themes)}."
        f" Events: {condensed}. Keep it concise, warm, and action-focused."
    )


def build_section_prompt(month_key: str, theme: str, events_for_theme: List[EventSummary]) -> str:
    compact = [
        {
            "date": ev.date.isoformat(),
            "transit": ev.transit_body,
            "natal": ev.natal_body,
            "aspect": ev.aspect,
            "score": ev.score,
            "note": ev.raw_note,
        }
        for ev in events_for_theme[:8]
    ]
    return (
        f"Create guidance for {theme} in {month_key}."
        f" Focus on supportive, practical suggestions. Events: {compact}."
    )


def build_eclipse_guide_prompt(eclipse_events: List[EclipseSummary]) -> str:
    return (
        "Create a short guide for eclipses and lunations."
        f" Events: {[e.model_dump() for e in eclipse_events]}."
        " Offer grounding, reflective tips and avoid deterministic tone."
    )


def build_rituals_prompt(month_key: str, key_themes: Set[str], hot_days: List[EventSummary], caution_days: List[EventSummary]) -> str:
    return (
        f"Suggest rituals and journal prompts for {month_key}."
        f" Themes: {sorted(key_themes)}. Hot days: {[e.date.isoformat() for e in hot_days[:3]]}."
        f" Caution days: {[e.date.isoformat() for e in caution_days[:3]]}."
    )


async def _call_llm(user_prompt: str, max_tokens: int = 800) -> str:
    """Call LLM and return markdown-formatted response.
    
    Markdown will be parsed and formatted by the PDF renderer:
    - **bold** → bold text
    - ### heading → H3 style
    - #### heading → H4 style
    - Newlines preserved for paragraph breaks
    """
    try:
        return await generate_section_text(SYSTEM_PROMPT, user_prompt, max_tokens=max_tokens)
    except LLMUnavailableError:
        return ""


def _fallback_paragraph(title: str, month_key: Optional[str] = None) -> str:
    if month_key:
        return f"{month_key}: Focus on steady progress, listen to your rhythms, and stay flexible."
    return f"{title}: Stay curious, grounded, and avoid drastic decisions without reflection."


async def _generate_bullets(prompt: str, fallback: List[str]) -> List[str]:
    raw = await _call_llm(prompt, max_tokens=300)
    if not raw:
        return fallback
    bullets = [line.strip("-• ").strip() for line in raw.splitlines() if line.strip()]
    bullets = [b for b in bullets if b]
    return bullets[:8] if bullets else fallback


async def _generate_month_section(month_key: str, events: List[EventSummary]) -> MonthlySection:
    themes: Set[str] = set(ev.section or "general" for ev in events)
    high_score_days = sorted(events, key=lambda e: -e.score)[:8]
    caution_days = [e for e in events if (e.aspect or "").lower() in CHALLENGING_ASPECTS][:6]

    overview_prompt = build_month_overview_prompt(month_key, events, themes)
    career_prompt = build_section_prompt(month_key, "career and finance", [e for e in events if "career" in (e.section or "")])
    relationship_prompt = build_section_prompt(month_key, "relationships and family", [e for e in events if "relationships" in (e.section or "")])
    health_prompt = build_section_prompt(month_key, "health and energy", [e for e in events if "health" in (e.section or "")])
    rituals_prompt = build_rituals_prompt(month_key, themes, high_score_days, caution_days)
    planner_prompt = (
        f"List 3-6 action items for {month_key} based on events {[(e.date.isoformat(), e.section) for e in high_score_days[:5]]}."
        " Keep each action short."
    )

    overview_text, career_text, relationship_text, health_text, rituals_text, planner_bullets = await asyncio.gather(
        _call_llm(overview_prompt),
        _call_llm(career_prompt),
        _call_llm(relationship_prompt),
        _call_llm(health_prompt),
        _call_llm(rituals_prompt),
        _generate_bullets(planner_prompt, ["Mark key dates and pace your commitments."]),
    )

    return MonthlySection(
        month=month_key,
        overview=overview_text or _fallback_paragraph("Overview", month_key),
        high_score_days=high_score_days,
        caution_days=caution_days,
        career_and_finance=career_text or _fallback_paragraph("Career", month_key),
        relationships_and_family=relationship_text or _fallback_paragraph("Relationships", month_key),
        health_and_energy=health_text or _fallback_paragraph("Health", month_key),
        aspect_grid=[
            {
                "date": ev.date.isoformat(),
                "transit": ev.transit_body,
                "natal": ev.natal_body,
                "aspect": ev.aspect,
                "score": ev.score,
            }
            for ev in events[:20]
        ],
        rituals_and_journal=rituals_text or _fallback_paragraph("Rituals", month_key),
        planner_actions=planner_bullets,
    )


async def interpret_yearly_forecast(raw_result: Dict[str, Any]) -> YearlyForecastReport:
    months_raw: Dict[str, List[Dict[str, Any]]] = raw_result.get("months", {}) or {}
    months_events: Dict[str, List[EventSummary]] = {
        month: [_event_summary(e) for e in events] for month, events in months_raw.items()
    }

    top_events = [
        TopEventSummary(
            title=f"{e.get('transit_body')} to {e.get('natal_body')}",
            date=dt.date.fromisoformat(str(e.get("date"))) if e.get("date") else None,
            summary=str(e.get("note") or ""),
            score=float(e.get("score", 0.0)),
            tags=list(classify_event(e)),
        )
        for e in raw_result.get("top_events", [])
    ]

    heatmap = _build_heatmap(months_events)
    all_events_flat: List[EventSummary] = [ev for events in months_events.values() for ev in events]
    eclipses = _extract_eclipses(all_events_flat)

    # LLM driven front matter
    year_overview_prompt = build_year_overview_prompt(raw_result.get("meta", {}), top_events, heatmap)
    eclipse_prompt = build_eclipse_guide_prompt(eclipses)

    year_overview_text, eclipse_text = await asyncio.gather(
        _call_llm(year_overview_prompt), _call_llm(eclipse_prompt)
    )

    month_sections = await asyncio.gather(
        *[_generate_month_section(month, events) for month, events in months_events.items()]
    )

    glossary = {
        "conjunction": "Two points share the same zodiac degree, blending energies.",
        "square": "Tension that pushes for action and adjustment.",
        "trine": "A smooth flow that supports ease and collaboration.",
    }
    interpretation_index = {
        f"{ev.transit_body} to {ev.natal_body}": ev.user_friendly_summary or ev.raw_note for ev in all_events_flat[:50]
    }

    year_at_glance = YearAtGlance(
        heatmap=heatmap,
        top_events=top_events,
        commentary=year_overview_text or _fallback_paragraph("Year overview"),
    )

    if eclipses and eclipse_text:
        # distribute same guidance across eclipses
        eclipses = [e.model_copy(update={"guidance": eclipse_text}) for e in eclipses]

    return YearlyForecastReport(
        meta=raw_result.get("meta", {}),
        year_at_glance=year_at_glance,
        eclipses_and_lunations=eclipses,
        months=sorted(month_sections, key=lambda m: m.month),
        appendix_all_events=sorted(all_events_flat, key=lambda ev: ev.date),
        glossary=glossary,
        interpretation_index=interpretation_index,
    )
