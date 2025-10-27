from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

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
    fix_indefinite_articles,
)
from src.content.archetype_router import classify_event
from src.content.area_selector import rank_events_by_area, summarize_rankings
from src.content.phrasebank import (
    PhraseAsset,
    get_asset,
    seed_from_event,
    select_clause,
)
from src.content.variation import VariationEngine


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


def normalize_bullets(
    bullets: list[str],
    profile_name: str,
    *,
    area: str,
    asset: PhraseAsset | None = None,
    engine: VariationEngine | None = None,
) -> list[str]:
    ordered: Sequence[str] = bullets or []
    if engine and ordered:
        ordered = engine.permutation(f"{area}.bullets", ordered)
    out: list[str] = []
    for idx, raw in enumerate(ordered):
        cleaned = to_you_pov(raw or "", profile_name)
        bullet = imperative_bullet(cleaned, idx, area=area, asset=asset)
        if bullet and bullet not in out:
            out.append(bullet)
    return out[:4]


def normalize_avoid(
    bullets: list[str],
    profile_name: str,
    *,
    area: str,
    asset: PhraseAsset | None = None,
    engine: VariationEngine | None = None,
) -> list[str]:
    ordered: Sequence[str] = bullets or []
    if engine and ordered:
        ordered = engine.permutation(f"{area}.avoid", ordered)
    out: list[str] = []
    for idx, raw in enumerate(ordered):
        cleaned = to_you_pov(raw or "", profile_name)
        bullet = imperative_bullet(cleaned, idx, mode="avoid", area=area, asset=asset)
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


class _TokenDict(dict[str, str]):
    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return ""


def _format_variation_sentences(sentences: Sequence[str], tokens: Mapping[str, str]) -> tuple[str, ...]:
    formatted: list[str] = []
    mapper = _TokenDict(tokens)
    for sentence in sentences:
        text = (sentence or "").format_map(mapper).strip()
        if not text:
            continue
        if text[-1] not in ".!?":
            text = f"{text}."
        formatted.append(fix_indefinite_articles(text))
    return tuple(formatted)


def _append_variation_sentences(base: str, extras: Sequence[str]) -> str:
    extra_list = [text.strip() for text in extras if text and text.strip()]
    if not extra_list:
        return base
    base_clean = (base or "").strip()
    if base_clean and base_clean[-1] not in ".!?":
        base_clean = f"{base_clean}."
    if base_clean:
        combined = " ".join([base_clean, *extra_list]).strip()
    else:
        combined = " ".join(extra_list).strip()
    return fix_indefinite_articles(combined)


def build_context(option_b_json: dict[str, Any]) -> dict[str, Any]:
    meta = option_b_json.get("meta", {})
    profile_name = option_b_json.get("profile_name") or meta.get("profile_name") or "User"
    date = option_b_json.get("date") or meta.get("date") or ""

    events = option_b_json.get("events") or option_b_json.get("top_events") or []
    annotated_events, area_rankings = rank_events_by_area(events)
    dom_planet, dom_sign = derive_dominant(annotated_events)
    dominant_signs = top_two_signs(annotated_events)
    lucky = lucky_from_dominant(dom_planet, dom_sign)

    enriched_events = _enrich_events(annotated_events)
    tone_hints = {section: _section_tone(enriched_events, section) for section in SECTION_TAGS}
    top_classification = enriched_events[0]["classification"] if enriched_events else None
    area_summary = summarize_rankings(area_rankings)
    selected_area_events: dict[str, dict[str, Any] | None] = {}
    for area, summary in area_summary.items():
        primary = summary.get("selected") if summary else None
        supporting = summary.get("supporting") if summary else None
        selected_area_events[area] = {
            "selected": primary,
            "primary": primary,
            "supporting": supporting,
            "event": (primary or {}).get("event") if isinstance(primary, Mapping) else None,
            "supporting_event": (supporting or {}).get("event") if isinstance(supporting, Mapping) else None,
            "ranking": summary.get("ranking") if summary else None,
        }

    general_archetype = (top_classification or {}).get("archetype", "Steady Integration")
    general_intensity = (top_classification or {}).get("intensity", "steady")
    general_event = enriched_events[0]["event"] if enriched_events else None
    general_asset = get_asset(general_archetype, general_intensity, "general")
    general_seed = seed_from_event("general", general_event, salt=date or "")
    general_engine = VariationEngine(general_seed)
    general_variations = general_asset.variations(general_seed)
    general_tokens = general_variations.tokens()
    general_tokens.setdefault("area", "general")
    clause_template = (
        general_variations.first("clauses", general_asset.clause_cycle()[0])
        if "clauses" in general_variations
        else None
    )
    if clause_template:
        general_clause = clause_template.format_map(_TokenDict(general_tokens))
    else:
        general_clause = select_clause(
            general_archetype,
            general_intensity,
            "general",
            seed=general_seed,
        )
    general_optional = _format_variation_sentences(
        general_variations.selections("optional_sentences"), general_tokens
    )

    phrase_context: dict[str, dict[str, Any]] = {}
    for area in SECTION_TAGS:
        selected = selected_area_events.get(area)
        event = selected.get("event") if selected else None
        if event:
            classification = classify_event(event)
        else:
            classification = top_classification or {}
        archetype = classification.get("archetype", "Steady Integration")
        intensity = classification.get("intensity", "steady")
        asset = get_asset(archetype, intensity, area)
        seed = seed_from_event(area, event, salt=date or "")
        engine = VariationEngine(seed)
        variations = asset.variations(seed)
        tokens = variations.tokens()
        tokens.setdefault("area", area)
        clause_template = (
            variations.first("clauses", asset.clause_cycle()[0])
            if "clauses" in variations
            else None
        )
        if clause_template:
            clause = clause_template.format_map(_TokenDict(tokens))
        else:
            clause = select_clause(archetype, intensity, area, seed=seed)
        optional_sentences = _format_variation_sentences(
            variations.selections("optional_sentences"), tokens
        )
        phrase_context[area] = {
            "asset": asset,
            "clause": clause,
            "archetype": archetype,
            "intensity": intensity,
            "seed": seed,
            "engine": engine,
            "tokens": tokens,
            "optional_sentences": optional_sentences,
            "variations": variations,
        }

    morning = option_b_json.get("morning_mindset", {})
    career = option_b_json.get("career", {})
    love = option_b_json.get("love", {})
    health = option_b_json.get("health", {})
    finance = option_b_json.get("finance", {})

    area_events: dict[str, dict[str, Any | None]] = {}
    for area in SECTION_TAGS:
        selected = selected_area_events.get(area) or {}
        area_events[area] = {
            "primary": selected.get("event"),
            "supporting": selected.get("supporting_event"),
        }

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
            clause=general_clause,
        ),
        "morning_paragraph": _append_variation_sentences(
            build_morning_paragraph(
                morning.get("paragraph", ""),
                profile_name,
                option_b_json.get("theme", ""),
                event=general_event,
            ),
            general_optional,
        ),
        "mantra": (morning.get("mantra") or "I choose what strengthens me.").strip(),
        "career_paragraph": build_career_paragraph(
            career.get("paragraph", ""),
            profile_name=profile_name,
            tone_hint=tone_hints["career"],
            clause=phrase_context.get("career", {}).get("clause"),
            event=area_events.get("career", {}).get("primary"),
            supporting_event=area_events.get("career", {}).get("supporting"),
        ),
        "career_bullets": normalize_bullets(
            career.get("bullets", []),
            profile_name,
            area="career",
            asset=phrase_context.get("career", {}).get("asset"),
            engine=phrase_context.get("career", {}).get("engine"),
        ),
        "love_paragraph": build_love_paragraph(
            love.get("paragraph", ""),
            profile_name=profile_name,
            tone_hint=tone_hints["love"],
            clause=phrase_context.get("love", {}).get("clause"),
            event=area_events.get("love", {}).get("primary"),
            supporting_event=area_events.get("love", {}).get("supporting"),
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
            clause=phrase_context.get("health", {}).get("clause"),
            event=area_events.get("health", {}).get("primary"),
            supporting_event=area_events.get("health", {}).get("supporting"),
        ),
        "health_opts": normalize_bullets(
            health.get("good_options", []),
            profile_name,
            area="health",
            asset=phrase_context.get("health", {}).get("asset"),
            engine=phrase_context.get("health", {}).get("engine"),
        ),
        "finance_paragraph": build_finance_paragraph(
            finance.get("paragraph", ""),
            option_b_json.get("theme", ""),
            profile_name=profile_name,
            tone_hint=tone_hints["finance"],
            clause=phrase_context.get("finance", {}).get("clause"),
            event=area_events.get("finance", {}).get("primary"),
            supporting_event=area_events.get("finance", {}).get("supporting"),
        ),
        "finance_bullets": normalize_bullets(
            finance.get("bullets", []),
            profile_name,
            area="finance",
            asset=phrase_context.get("finance", {}).get("asset"),
            engine=phrase_context.get("finance", {}).get("engine"),
        ),
        "do_today": normalize_bullets(
            option_b_json.get("do_today", []),
            profile_name,
            area="general",
            asset=general_asset,
            engine=general_engine,
        ),
        "avoid_today": normalize_avoid(
            option_b_json.get("avoid_today", []),
            profile_name,
            area="general",
            asset=general_asset,
            engine=general_engine,
        ),
        "lucky": lucky,
        "one_line_summary": build_one_line_summary(
            option_b_json.get("one_line_summary", ""), option_b_json.get("theme", ""), profile_name=profile_name
        ),
        "area_events": selected_area_events,
    }
    for area in SECTION_TAGS:
        ctx[f"{area}_event"] = area_events.get(area, {}).get("primary")
        ctx[f"{area}_supporting_event"] = area_events.get(area, {}).get("supporting")

    for area in ("career", "love", "health", "finance"):
        extras = phrase_context.get(area, {}).get("optional_sentences", ())
        if extras:
            key = f"{area}_paragraph"
            ctx[key] = _append_variation_sentences(ctx.get(key, ""), extras)

    ctx["tech_notes"] = {
        "dominant": {"planet": dom_planet, "sign": dom_sign},
        "raw_events": annotated_events[:5],
        "classifier": {
            "top_event": {
                **({} if not enriched_events else enriched_events[0]["event"]),
                **(top_classification or {}),
            },
            "section_tones": tone_hints,
        },
        "areas": area_summary,
        "phrases": {
            "general": {
                "archetype": general_archetype,
                "intensity": general_intensity,
                "seed": general_seed,
            },
            **{
                area: {
                    "archetype": details.get("archetype"),
                    "intensity": details.get("intensity"),
                    "seed": details.get("seed"),
                }
                for area, details in phrase_context.items()
            },
        },
    }
    return ctx


def render(option_b_json: dict[str, Any], templates_dir: str | None = None) -> str:
    env = _env(Path(templates_dir) if templates_dir else TEMPLATES_DIR)
    tmpl = env.get_template("template.json.j2")
    ctx = build_context(option_b_json)
    return tmpl.render(**ctx)
