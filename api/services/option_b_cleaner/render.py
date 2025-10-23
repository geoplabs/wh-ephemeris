from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .clean import clamp_sentences, de_jargon, imperative_bullet, to_you_pov
from .lucky import lucky_from_dominant


TEMPLATES_DIR = Path(__file__).resolve().parent


def _env(templates_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def derive_dominant(transits: list[dict[str, Any]]) -> tuple[str, str]:
    if not transits:
        return "Sun", "Leo"
    top = sorted(transits, key=lambda x: x.get("score", 0), reverse=True)[0]
    planet = top.get("transit_body") or top.get("body") or "Sun"
    note = top.get("note", "")
    sign = top.get("sign") or ""
    if not sign and ";" in note:
        tail = note.split(";")[-1].replace(".", "").strip()
        if tail:
            parts = tail.split()
            if parts:
                sign = parts[-1]
    if not sign:
        sign = "Leo"
    return planet, sign


def normalize_paragraph(text: str, profile_name: str) -> str:
    cleaned = de_jargon(text or "")
    pov = to_you_pov(cleaned, profile_name)
    return clamp_sentences(pov, max_sentences=2)


def normalize_bullets(bullets: list[str], profile_name: str) -> list[str]:
    out: list[str] = []
    for raw in bullets or []:
        cleaned = to_you_pov(raw or "", profile_name)
        bullet = imperative_bullet(cleaned)
        if bullet and bullet not in out:
            out.append(bullet)
    return out[:4]


def build_context(option_b_json: dict[str, Any]) -> dict[str, Any]:
    meta = option_b_json.get("meta", {})
    profile_name = option_b_json.get("profile_name") or meta.get("profile_name") or "User"
    date = option_b_json.get("date") or meta.get("date") or ""

    events = option_b_json.get("events") or option_b_json.get("top_events") or []
    dom_planet, dom_sign = derive_dominant(events)
    lucky = lucky_from_dominant(dom_planet, dom_sign)

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
        "opening_summary": normalize_paragraph(option_b_json.get("opening_summary", ""), profile_name),
        "morning_paragraph": normalize_paragraph(morning.get("paragraph", ""), profile_name),
        "mantra": to_you_pov(morning.get("mantra", "I choose what strengthens me."), profile_name),
        "career_paragraph": normalize_paragraph(career.get("paragraph", ""), profile_name),
        "career_bullets": normalize_bullets(career.get("bullets", []), profile_name),
        "love_paragraph": normalize_paragraph(love.get("paragraph", ""), profile_name),
        "love_attached": normalize_paragraph(love.get("attached", ""), profile_name),
        "love_single": normalize_paragraph(love.get("single", ""), profile_name),
        "health_paragraph": normalize_paragraph(health.get("paragraph", ""), profile_name),
        "health_opts": normalize_bullets(health.get("good_options", []), profile_name),
        "finance_paragraph": normalize_paragraph(finance.get("paragraph", ""), profile_name),
        "finance_bullets": normalize_bullets(finance.get("bullets", []), profile_name),
        "do_today": normalize_bullets(option_b_json.get("do_today", []), profile_name),
        "avoid_today": normalize_bullets(option_b_json.get("avoid_today", []), profile_name),
        "lucky": lucky,
        "one_line_summary": normalize_paragraph(option_b_json.get("one_line_summary", ""), profile_name),
        "tech_notes": {
            "dominant": {"planet": dom_planet, "sign": dom_sign},
            "raw_events": events[:5],
        },
    }
    return ctx


def render(option_b_json: dict[str, Any], templates_dir: str | None = None) -> str:
    env = _env(Path(templates_dir) if templates_dir else TEMPLATES_DIR)
    tmpl = env.get_template("template.json.j2")
    ctx = build_context(option_b_json)
    return tmpl.render(**ctx)
