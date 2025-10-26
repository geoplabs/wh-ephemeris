from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .clean import imperative_bullet, to_you_pov
from .lucky import lucky_from_dominant
from .language import (
    build_career_paragraph,
    build_finance_paragraph,
    build_health_paragraph,
    build_love_paragraph,
    build_love_status,
    build_morning_paragraph,
    build_one_line_summary,
    build_opening_summary,
)
from src.content.archetype_router import classify_event


TEMPLATES_DIR = Path(__file__).resolve().parent


def _env(templates_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def _sign_from_event(event: dict[str, Any]) -> str:
    sign = (
        event.get("sign")
        or event.get("transit_sign")
        or event.get("natal_sign")
        or ""
    )
    if sign:
        return sign
    note = event.get("note") or ""
    if note:
        tail = note.split(";")[-1]
        match = re.search(r"([A-Z][a-z]+)\.?$", tail.strip())
        if match:
            return match.group(1)
    return ""


def derive_dominant(transits: list[dict[str, Any]]) -> tuple[str, str]:
    if not transits:
        return "Sun", "Leo"
    top = sorted(transits, key=lambda x: x.get("score", 0), reverse=True)[0]
    planet = top.get("transit_body") or top.get("body") or "Sun"
    sign = _sign_from_event(top) or "Leo"
    return planet, sign


def top_two_signs(transits: list[dict[str, Any]]) -> list[str]:
    ordered = sorted(transits or [], key=lambda x: x.get("score", 0), reverse=True)
    signs: list[str] = []
    for event in ordered:
        sign = _sign_from_event(event)
        if sign and sign not in signs:
            signs.append(sign)
        if len(signs) == 2:
            break
    if not signs:
        return ["Libra", "Scorpio"]
    if len(signs) == 1:
        fallback = "Scorpio" if signs[0] != "Scorpio" else "Libra"
        signs.append(fallback)
    return signs[:2]


def normalize_bullets(bullets: list[str], profile_name: str) -> list[str]:
    out: list[str] = []
    for idx, raw in enumerate(bullets or []):
        cleaned = to_you_pov(raw or "", profile_name)
        bullet = imperative_bullet(cleaned, idx)
        if bullet and bullet not in out:
            out.append(bullet)
    return out[:4]


def normalize_avoid(bullets: list[str], profile_name: str) -> list[str]:
    out: list[str] = []
    for idx, raw in enumerate(bullets or []):
        cleaned = to_you_pov(raw or "", profile_name)
        bullet = imperative_bullet(cleaned, idx, mode="avoid")
        if bullet and bullet not in out:
            out.append(bullet)
    return out[:4]


def _tone_from_tags(tags: Iterable[str]) -> str:
    for tag in tags:
        if tag.startswith("tone:"):
            return tag.split(":", 1)[1]
    return "neutral"


SECTION_TAGS = {
    "career": {"career", "ambition", "strategy", "discipline"},
    "love": {"love", "relationships", "family", "connection"},
    "health": {"health", "routine", "vitality", "healing", "body"},
    "finance": {"money", "resources", "strategy", "stability"},
}


def _enrich_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for ev in events:
        classification = classify_event(ev)
        tone = _tone_from_tags(classification.get("tags", []))
        score = float(ev.get("score", 0.0) or 0.0)
        enriched.append({"event": ev, "classification": classification, "tone": tone, "score": score})
    enriched.sort(key=lambda item: (abs(item["score"]), item["score"]), reverse=True)
    return enriched


def _section_tone(enriched: list[dict[str, Any]], section: str) -> str:
    target_tags = SECTION_TAGS.get(section, set())
    if not target_tags:
        return "neutral"
    for item in enriched:
        tags = set(item["classification"].get("tags", []))
        if tags.intersection(target_tags):
            return item["tone"]
    return "neutral"


def build_context(option_b_json: dict[str, Any]) -> dict[str, Any]:
    meta = option_b_json.get("meta", {})
    profile_name = option_b_json.get("profile_name") or meta.get("profile_name") or "User"
    date = option_b_json.get("date") or meta.get("date") or ""

    events = option_b_json.get("events") or option_b_json.get("top_events") or []
    dom_planet, dom_sign = derive_dominant(events)
    dominant_signs = top_two_signs(events)
    lucky = lucky_from_dominant(dom_planet, dom_sign)

    enriched_events = _enrich_events(events)
    tone_hints = {section: _section_tone(enriched_events, section) for section in SECTION_TAGS}
    top_classification = enriched_events[0]["classification"] if enriched_events else None

    morning = option_b_json.get("morning_mindset", {})
    career = option_b_json.get("career", {})
    love = option_b_json.get("love", {})
    health = option_b_json.get("health", {})
    finance = option_b_json.get("finance", {})

    ctx: dict[str, Any] = {
        "profile_name": profile_name,
        "date": date,
        "mood": option_b_json.get("mood", "balanced"),
        "theme": option_b_json.get("theme", "Daily Guidance"),
        "opening_summary": build_opening_summary(
            option_b_json.get("theme", ""),
            option_b_json.get("opening_summary", ""),
            dominant_signs,
            profile_name=profile_name,
        ),
        "morning_paragraph": build_morning_paragraph(
            morning.get("paragraph", ""), profile_name, option_b_json.get("theme", "")
        ),
        "mantra": (morning.get("mantra") or "I choose what strengthens me.").strip(),
        "career_paragraph": build_career_paragraph(
            career.get("paragraph", ""), profile_name=profile_name, tone_hint=tone_hints["career"]
        ),
        "career_bullets": normalize_bullets(career.get("bullets", []), profile_name),
        "love_paragraph": build_love_paragraph(
            love.get("paragraph", ""), profile_name=profile_name, tone_hint=tone_hints["love"]
        ),
        "love_attached": build_love_status(
            love.get("attached", ""), "attached", profile_name=profile_name, tone_hint=tone_hints["love"]
        ),
        "love_single": build_love_status(
            love.get("single", ""), "single", profile_name=profile_name, tone_hint=tone_hints["love"]
        ),
        "health_paragraph": build_health_paragraph(
            health.get("paragraph", ""),
            option_b_json.get("theme", ""),
            profile_name=profile_name,
            tone_hint=tone_hints["health"],
        ),
        "health_opts": normalize_bullets(health.get("good_options", []), profile_name),
        "finance_paragraph": build_finance_paragraph(
            finance.get("paragraph", ""),
            option_b_json.get("theme", ""),
            profile_name=profile_name,
            tone_hint=tone_hints["finance"],
        ),
        "finance_bullets": normalize_bullets(finance.get("bullets", []), profile_name),
        "do_today": normalize_bullets(option_b_json.get("do_today", []), profile_name),
        "avoid_today": normalize_avoid(option_b_json.get("avoid_today", []), profile_name),
        "lucky": lucky,
        "one_line_summary": build_one_line_summary(
            option_b_json.get("one_line_summary", ""), option_b_json.get("theme", ""), profile_name=profile_name
        ),
        "tech_notes": {
            "dominant": {"planet": dom_planet, "sign": dom_sign},
            "raw_events": events[:5],
            "classifier": {
                "top_event": {
                    **({} if not enriched_events else enriched_events[0]["event"]),
                    **(top_classification or {}),
                },
                "section_tones": tone_hints,
            },
        },
    }
    return ctx


def render(option_b_json: dict[str, Any], templates_dir: str | None = None) -> str:
    env = _env(Path(templates_dir) if templates_dir else TEMPLATES_DIR)
    tmpl = env.get_template("template.json.j2")
    ctx = build_context(option_b_json)
    return tmpl.render(**ctx)
