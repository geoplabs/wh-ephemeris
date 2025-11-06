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
from ..remedy_templates import remedy_templates_for_planet
from src.content import compute_caution_windows
from src.content.window_resolver import resolve_windows_with_netting
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

CAUTION_ASPECTS = {
    "square",
    "opposition",
    "quincunx",
    "inconjunct",
    "retrograde",
    "semi-square",
    "sesquisquare",
}

CAUTION_KEYWORDS = {
    "pressure",
    "tension",
    "strain",
    "challenge",
    "caution",
    "warning",
    "delay",
    "stress",
    "conflict",
    "pushback",
}

_REPEATED_WORD_PATTERN = re.compile(r"\b(\w+)(\s+\1\b)+", re.IGNORECASE)

CAUTION_FALLBACK_TIME = "All day (general caution)"
CAUTION_FALLBACK_NOTE = "Use this span for careful review and gentler pacing."
MAX_LIST_ITEMS = 4


_BULLET_STOPWORDS = {
    "a",
    "about",
    "and",
    "anchor",
    "as",
    "at",
    "be",
    "build",
    "by",
    "clarity",
    "can",
    "care",
    "for",
    "focus",
    "from",
    "if",
    "in",
    "into",
    "keep",
    "make",
    "move",
    "moves",
    "need",
    "note",
    "of",
    "on",
    "plan",
    "set",
    "share",
    "so",
    "step",
    "support",
    "take",
    "that",
    "the",
    "their",
    "this",
    "through",
    "to",
    "today",
    "update",
    "what",
    "when",
    "with",
    "wins",
    "your",
}


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _strip_dashes(value: str) -> str:
    return value.replace("—", "-").replace("–", "-")


def _ensure_sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    cleaned = _REPEATED_WORD_PATTERN.sub(lambda m: m.group(1), cleaned)
    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


def _looks_challenging(aspect: str, note: str, tone: str, intensity: str) -> bool:
    if tone == "challenge":
        return True
    if intensity in {"intense", "challenge", "hard"}:
        return True
    if any(token in aspect for token in CAUTION_ASPECTS):
        return True
    return any(keyword in note for keyword in CAUTION_KEYWORDS)


def _event_time_window(event: Mapping[str, Any]) -> str:
    for key in ("time_window", "window", "time", "span", "range"):
        candidate = _strip_dashes(_coerce_text(event.get(key)))
        if candidate:
            return candidate
    start = _strip_dashes(_coerce_text(event.get("start_time")))
    end = _strip_dashes(_coerce_text(event.get("end_time")))
    if start and end:
        return f"{start}-{end}"
    return ""


def _calculate_overlap_net_score(
    lucky_event: Mapping[str, Any],
    all_events: Sequence[Mapping[str, Any]],
    lucky_window: str,
    caution_window: str
) -> float:
    """Calculate net score in overlapping region between lucky and caution windows.
    
    Net score = sum of friction scores - sum of support scores in overlap
    Positive = friction dominates, Negative = support dominates
    
    Args:
        lucky_event: The supportive event contributing to lucky window
        all_events: All transit events
        lucky_window: Lucky time window string (e.g., "08:51-10:51 UTC")
        caution_window: Caution time window string (e.g., "13:16-19:16 UTC")
    
    Returns:
        Net score (positive = friction wins, negative = support wins)
    """
    from .lucky import _parse_window_times
    
    # Parse windows
    lucky_span = _parse_window_times(lucky_window)
    caution_span = _parse_window_times(caution_window)
    
    if not lucky_span or not caution_span:
        return 0.0
    
    # Calculate overlap span
    overlap_start = max(lucky_span[0], caution_span[0])
    overlap_end = min(lucky_span[1], caution_span[1])
    
    if overlap_start >= overlap_end:
        return 0.0  # No actual overlap
    
    # Sum friction scores (positive) and support scores (negative) that contribute to this overlap
    # ONLY count events whose INFLUENCE WINDOWS intersect the overlap region
    friction_score = 0.0
    support_score = 0.0
    
    # Define influence window duration by planet (in minutes)
    influence_windows = {
        "moon": 60,        # ±1 hour
        "mercury": 90,     # ±1.5 hours
        "venus": 90,       # ±1.5 hours
        "sun": 120,        # ±2 hours
        "mars": 120,       # ±2 hours
        "jupiter": 180,    # ±3 hours
        "saturn": 180,     # ±3 hours
        "uranus": 180,     # ±3 hours
        "neptune": 180,    # ±3 hours
        "pluto": 180,      # ±3 hours
        "chiron": 120,     # ±2 hours
    }
    
    for event in all_events:
        if not isinstance(event, Mapping):
            continue
        
        score = event.get("score", 0)
        exact_time = event.get("exact_hit_time_utc")
        
        if not exact_time:
            continue
        
        # Parse the exact time and calculate event's influence window
        try:
            from datetime import datetime, timedelta
            exact_time_str = exact_time.replace("Z", "+00:00")
            exact_dt = datetime.fromisoformat(exact_time_str)
            
            # Determine window size based on transit planet
            transit_body = (event.get("transit_body") or "").lower()
            window_minutes = influence_windows.get(transit_body, 120)  # default ±2 hours
            
            # Calculate event's influence window in minutes from midnight
            event_start = exact_dt - timedelta(minutes=window_minutes)
            event_end = exact_dt + timedelta(minutes=window_minutes)
            event_start_min = event_start.hour * 60 + event_start.minute
            event_end_min = event_end.hour * 60 + event_end.minute
            
            # Check if event's window intersects the overlap region
            # Intersection exists if: event_start < overlap_end AND event_end > overlap_start
            if event_end_min <= overlap_start or event_start_min >= overlap_end:
                continue  # No intersection, skip this event
            
        except (ValueError, AttributeError):
            continue  # Can't parse time, skip this event
        
        # Event's window intersects overlap region - count its score
        if score > 0:
            # Friction event - add to friction score
            friction_score += abs(score)
        elif score < 0:
            # Support event - add to support score
            support_score += abs(score)
    
    # Net score: friction - support
    # Positive means friction dominates, negative means support dominates
    net = friction_score - support_score
    
    # Normalize by the size of the overlap window (in hours)
    overlap_hours = (overlap_end - overlap_start) / 60.0
    if overlap_hours > 0:
        net = net / overlap_hours
    
    return net


def _build_caution_window_from_events(
    enriched_events: Sequence[Mapping[str, Any]]
) -> dict[str, str]:
    raw_events: list[Mapping[str, Any]] = []
    for item in enriched_events:
        if not isinstance(item, Mapping):
            continue
        event = item.get("event") if isinstance(item, Mapping) else None
        if isinstance(event, Mapping):
            raw_events.append(event)

    if raw_events:
        windows = compute_caution_windows(raw_events)
        for window in windows:
            severity = window.get("severity")
            if severity not in {"Gentle Note", "Caution", "High Caution"}:
                continue
            time_window = window.get("time_window_utc")
            note_text = window.get("note") or CAUTION_FALLBACK_NOTE
            if time_window:
                return {
                    "time_window": time_window,
                    "note": _ensure_sentence(note_text),
                }

    for item in enriched_events:
        event = item.get("event") if isinstance(item, Mapping) else None
        if not isinstance(event, Mapping):
            continue
        tone = _coerce_text(item.get("tone")) if isinstance(item, Mapping) else ""
        classification = item.get("classification") if isinstance(item, Mapping) else {}
        intensity = _coerce_text((classification or {}).get("intensity"))
        aspect = _coerce_text(event.get("aspect")).lower()
        note = _coerce_text(event.get("note"))
        score = event.get("score", 0)
        # Supportive aspects (score < 0) should NEVER be used for caution
        looks_bad = _looks_challenging(aspect, note.lower(), tone, intensity) and score > 0
        if looks_bad:
            time_window = _event_time_window(event) or CAUTION_FALLBACK_TIME
            note_text = _ensure_sentence(
                _strip_dashes(note) or CAUTION_FALLBACK_NOTE
            )
            return {"time_window": time_window, "note": note_text}

    # Fallback: use the first FRICTION event (score > 0), not supportive events
    if enriched_events:
        for item in enriched_events:
            fallback_event = item.get("event") if isinstance(item, Mapping) else None
            if isinstance(fallback_event, Mapping):
                score = fallback_event.get("score", 0)
                if score > 0:  # Only use friction events for caution fallback
                    time_window = _event_time_window(fallback_event) or CAUTION_FALLBACK_TIME
                    note_text = _ensure_sentence(
                        _strip_dashes(_coerce_text(fallback_event.get("note")))
                        or CAUTION_FALLBACK_NOTE
                    )
                    return {"time_window": time_window, "note": note_text}

    return {"time_window": CAUTION_FALLBACK_TIME, "note": CAUTION_FALLBACK_NOTE}


def _is_mercury_chiron_quincunx(event: Mapping[str, Any] | None) -> bool:
    if not isinstance(event, Mapping):
        return False
    transit = _coerce_text(event.get("transit_body")).lower()
    natal = _coerce_text(event.get("natal_body")).lower()
    aspect = _coerce_text(event.get("aspect")).lower()
    if transit != "mercury" or natal != "chiron":
        return False
    return aspect in {"quincunx", "inconjunct"}


def _build_remedies(planet: str, sign: str, theme: str) -> list[str]:
    templates = remedy_templates_for_planet(planet)
    theme_token = (theme or "day").strip().lower() or "day"
    sign_token = (sign or "your sign").strip() or "your sign"
    remedies: list[str] = []
    seen: set[str] = set()
    for template in templates:
        text = template.format(sign=sign_token, theme=theme_token)
        formatted = _ensure_sentence(_strip_dashes(text))
        if formatted:
            lowered = formatted.lower()
            if lowered not in seen:
                remedies.append(formatted)
                seen.add(lowered)
        if len(remedies) >= MAX_LIST_ITEMS:
            break
    if not remedies:
        remedies.append(_ensure_sentence("Ground yourself with three steady breaths."))
    return remedies


def _bullet_tail_key(sentence: str) -> str:
    core = sentence.rstrip(".!?").strip().lower()
    if not core:
        return ""
    parts = core.split()
    if len(parts) <= 3:
        return core
    return " ".join(parts[-3:])


def _bullet_root_tokens(sentence: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z]+", sentence.lower())
    roots: set[str] = set()
    for token in tokens:
        if token in _BULLET_STOPWORDS:
            continue
        if len(token) <= 2:
            continue
        base = token
        if base.endswith("ing") and len(base) > 4:
            base = base[:-3]
        elif base.endswith("ies") and len(base) > 4:
            base = base[:-3] + "y"
        elif base.endswith("s") and len(base) > 3:
            base = base[:-1]
        roots.add(base)
    return roots


def _collect_bullet_roots(sentences: Sequence[str]) -> set[str]:
    combined: set[str] = set()
    for sentence in sentences:
        combined.update(_bullet_root_tokens(sentence))
    return combined


def collect_bullet_roots(sentences: Sequence[str]) -> set[str]:
    """Public helper exposing the normalized bullet roots for ``sentences``."""

    return _collect_bullet_roots(sentences)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = _strip_dashes(value)
        cleaned = " ".join(cleaned.split())
        return cleaned.strip()
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_value(item) for key, item in value.items()}
    return value


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
    forbidden_roots: Iterable[str] | None = None,
) -> list[str]:
    return _normalize_bullet_list(
        bullets,
        profile_name,
        area=area,
        asset=asset,
        engine=engine,
        mode="do",
        forbidden_roots=forbidden_roots,
    )


def normalize_avoid(
    bullets: list[str],
    profile_name: str,
    *,
    area: str,
    asset: PhraseAsset | None = None,
    engine: VariationEngine | None = None,
    forbidden_roots: Iterable[str] | None = None,
) -> list[str]:
    return _normalize_bullet_list(
        bullets,
        profile_name,
        area=area,
        asset=asset,
        engine=engine,
        mode="avoid",
        forbidden_roots=forbidden_roots,
    )


def _normalize_bullet_list(
    bullets: list[str],
    profile_name: str,
    *,
    area: str,
    asset: PhraseAsset | None,
    engine: VariationEngine | None,
    mode: str,
    forbidden_roots: Iterable[str] | None,
) -> list[str]:
    ordered: Sequence[str] = bullets or []
    if engine and ordered:
        tag = f"{area}.{'avoid' if mode == 'avoid' else 'bullets'}"
        ordered = engine.permutation(tag, ordered)
    out: list[str] = []
    used_tails: set[str] = set()
    used_roots: set[str] = set(forbidden_roots or [])
    for idx, raw in enumerate(ordered):
        cleaned = to_you_pov(raw or "", profile_name)
        candidate, tail, roots = _select_bullet_sentence(
            cleaned,
            base_order=idx,
            area=area,
            asset=asset,
            mode=mode,
            used_tails=used_tails,
            used_roots=used_roots,
        )
        if not candidate:
            continue
        if roots and roots.intersection(used_roots):
            continue
        if candidate in out:
            continue
        out.append(candidate)
        if tail:
            used_tails.add(tail)
        if roots:
            used_roots.update(roots)
        if len(out) >= MAX_LIST_ITEMS:
            break
    if mode == "avoid" and not out:
        out.extend(
            [
                "Avoid overextending your energy today.",
                "Skip reactive conversations when clarity is low.",
                "Hold back from impulse spending until timing improves.",
                "Delay tough calls so boundaries stay clear.",
            ][: MAX_LIST_ITEMS]
        )
    return out[:4]


def _select_bullet_sentence(
    text: str,
    *,
    base_order: int,
    area: str,
    asset: PhraseAsset | None,
    mode: str,
    used_tails: set[str],
    used_roots: set[str],
) -> tuple[str | None, str, set[str]]:
    fallback: tuple[str | None, str, set[str]] = (None, "", set())
    for offset in range(4):
        order = base_order + offset
        candidate = imperative_bullet(
            text,
            order,
            mode=mode,
            area=area,
            asset=asset,
        )
        if not candidate:
            continue
        tail = _bullet_tail_key(candidate)
        roots = _bullet_root_tokens(candidate)
        if not fallback[0]:
            fallback = (candidate, tail, roots)
        if tail and tail in used_tails:
            continue
        if roots and roots.intersection(used_roots):
            continue
        return candidate, tail, roots
    return fallback


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
    segments: list[str] = []
    seen: set[str] = set()

    def _append_segments(text: str) -> None:
        for part in re.split(r"(?<=[.!?])\s+", text.strip()):
            cleaned = part.strip()
            if not cleaned:
                continue
            if cleaned[-1] not in ".!?":
                cleaned = f"{cleaned}."
            normalized = cleaned.lower()
            if normalized not in seen:
                segments.append(cleaned)
                seen.add(normalized)

    base_clean = (base or "").strip()
    if base_clean:
        _append_segments(base_clean)
    for sentence in extra_list:
        _append_segments(sentence)
    combined = " ".join(segments).strip()
    return fix_indefinite_articles(combined)


def build_context(option_b_json: dict[str, Any]) -> dict[str, Any]:
    meta = option_b_json.get("meta", {})
    profile_name = option_b_json.get("profile_name") or meta.get("profile_name") or "User"
    date = option_b_json.get("date") or meta.get("date") or ""

    events = option_b_json.get("events") or option_b_json.get("top_events") or []
    annotated_events, area_rankings = rank_events_by_area(events)
    dom_planet, dom_sign = derive_dominant(annotated_events)
    dominant_signs = top_two_signs(annotated_events)
    
    enriched_events = _enrich_events(annotated_events)
    tone_hints = {section: _section_tone(enriched_events, section) for section in SECTION_TAGS}
    top_classification = enriched_events[0]["classification"] if enriched_events else None
    area_summary = summarize_rankings(area_rankings)
    
    # Extract raw events for window resolution
    raw_events: list[Mapping[str, Any]] = []
    for item in enriched_events:
        if not isinstance(item, Mapping):
            continue
        event = item.get("event") if isinstance(item, Mapping) else None
        if isinstance(event, Mapping):
            raw_events.append(event)
    
    # Step 1: Calculate CAUTION window independently (DO NOT TOUCH based on lucky)
    caution_window = _build_caution_window_from_events(enriched_events)
    
    # Step 2: Calculate LUCKY candidates independently
    # Get all supportive events sorted by score
    supportive_events = []
    for event in annotated_events:
        if not isinstance(event, Mapping):
            continue
        aspect = (event.get("aspect") or "").lower()
        transit_body = (event.get("transit_body") or "").lower()
        score = event.get("score", 0)
        exact_time = event.get("exact_hit_time_utc")
        
        supportive_aspects = {"trine", "sextile"}
        benefic_bodies = {"venus", "jupiter"}
        is_supportive = aspect in supportive_aspects or (aspect == "conjunction" and transit_body in benefic_bodies)
        
        if is_supportive and exact_time:
            supportive_events.append(event)
    
    # Sort by absolute score (strongest first)
    supportive_events.sort(key=lambda e: abs(e.get("score", 0)), reverse=True)
    
    # Step 3: Apply netting validation logic for lucky window
    lucky = None
    caution_time_str = caution_window.get("time_window") if caution_window else None
    
    for idx, candidate_event in enumerate(supportive_events):
        # Calculate lucky window for this candidate
        from .lucky import _calculate_lucky_window_from_exact_time
        candidate_time_window = _calculate_lucky_window_from_exact_time(
            candidate_event.get("exact_hit_time_utc"),
            candidate_event.get("transit_body", dom_planet)
        )
        
        if not candidate_time_window:
            continue
        
        # Check if it overlaps with caution window
        if caution_time_str:
            from .lucky import _parse_window_times, _windows_overlap
            overlaps = _windows_overlap(candidate_time_window, caution_time_str)
            
            if overlaps:
                # Calculate net score in overlap region
                net_score = _calculate_overlap_net_score(
                    candidate_event,
                    enriched_events,
                    candidate_time_window,
                    caution_time_str
                )
                
                abs_net = abs(net_score)
                
                # Decision rules
                if abs_net < 0.5:
                    # Near zero (mixed) - skip this candidate, try next
                    continue
                elif 0.5 <= abs_net < 1.5:
                    # Soft/moderate - compare with 2nd best non-overlapping
                    if idx + 1 < len(supportive_events):
                        second_event = supportive_events[idx + 1]
                        second_time_window = _calculate_lucky_window_from_exact_time(
                            second_event.get("exact_hit_time_utc"),
                            second_event.get("transit_body", dom_planet)
                        )
                        if second_time_window and not _windows_overlap(second_time_window, caution_time_str):
                            # Compare scores - use stronger one
                            if abs(second_event.get("score", 0)) > abs(candidate_event.get("score", 0)):
                                # Second is stronger and doesn't overlap - use it
                                lucky = lucky_from_dominant(dom_planet, dom_sign, time_window=second_time_window)
                                break
                    # Either no second candidate or first is stronger - use first
                    lucky = lucky_from_dominant(dom_planet, dom_sign, time_window=candidate_time_window)
                    break
                else:
                    # Strong dominance (≥1.5) - use it regardless of overlap
                    lucky = lucky_from_dominant(dom_planet, dom_sign, time_window=candidate_time_window)
                    break
            else:
                # No overlap - use this candidate
                lucky = lucky_from_dominant(dom_planet, dom_sign, time_window=candidate_time_window)
                break
        else:
            # No caution window - use first candidate
            lucky = lucky_from_dominant(dom_planet, dom_sign, time_window=candidate_time_window)
            break
    
    # Fallback if no lucky from exact transits
    if not lucky:
        lucky = lucky_from_dominant(dom_planet, dom_sign, events=annotated_events, caution_window_str=caution_time_str)
    
    remedy_lines = _build_remedies(dom_planet, dom_sign, option_b_json.get("theme", ""))
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

    career_paragraph = build_career_paragraph(
        career.get("paragraph", ""),
        profile_name=profile_name,
        tone_hint=tone_hints["career"],
        clause=phrase_context.get("career", {}).get("clause"),
        event=area_events.get("career", {}).get("primary"),
        supporting_event=area_events.get("career", {}).get("supporting"),
    )
    career_bullets = normalize_bullets(
        career.get("bullets", []),
        profile_name,
        area="career",
        asset=phrase_context.get("career", {}).get("asset"),
        engine=phrase_context.get("career", {}).get("engine"),
    )
    love_paragraph = build_love_paragraph(
        love.get("paragraph", ""),
        profile_name=profile_name,
        tone_hint=tone_hints["love"],
        clause=phrase_context.get("love", {}).get("clause"),
        event=area_events.get("love", {}).get("primary"),
        supporting_event=area_events.get("love", {}).get("supporting"),
    )
    love_attached = build_love_status(
        love.get("attached", ""), "attached", profile_name=profile_name, tone_hint=tone_hints["love"]
    )
    love_single = build_love_status(
        love.get("single", ""), "single", profile_name=profile_name, tone_hint=tone_hints["love"]
    )
    health_paragraph = build_health_paragraph(
        health.get("paragraph", ""),
        option_b_json.get("theme", ""),
        profile_name=profile_name,
        tone_hint=tone_hints["health"],
        clause=phrase_context.get("health", {}).get("clause"),
        event=area_events.get("health", {}).get("primary"),
        supporting_event=area_events.get("health", {}).get("supporting"),
    )
    health_events = area_events.get("health", {})
    if _is_mercury_chiron_quincunx(health_events.get("primary")) or _is_mercury_chiron_quincunx(
        health_events.get("supporting")
    ):
        adjustment_sentence = (
            "Subtle Mercury-Chiron tension calls for micro-adjustments: notice discomfort, then tweak routine rather than pushing through."
        )
        health_paragraph = _append_variation_sentences(health_paragraph, (adjustment_sentence,))
    health_opts = normalize_bullets(
        health.get("good_options", []),
        profile_name,
        area="health",
        asset=phrase_context.get("health", {}).get("asset"),
        engine=phrase_context.get("health", {}).get("engine"),
    )
    finance_paragraph = build_finance_paragraph(
        finance.get("paragraph", ""),
        option_b_json.get("theme", ""),
        profile_name=profile_name,
        tone_hint=tone_hints["finance"],
        clause=phrase_context.get("finance", {}).get("clause"),
        event=area_events.get("finance", {}).get("primary"),
        supporting_event=area_events.get("finance", {}).get("supporting"),
    )
    finance_bullets = normalize_bullets(
        finance.get("bullets", []),
        profile_name,
        area="finance",
        asset=phrase_context.get("finance", {}).get("asset"),
        engine=phrase_context.get("finance", {}).get("engine"),
    )

    general_do = normalize_bullets(
        option_b_json.get("do_today", []),
        profile_name,
        area="general",
        asset=general_asset,
        engine=general_engine,
    )
    positive_roots = _collect_bullet_roots(
        career_bullets + health_opts + finance_bullets + general_do
    )
    general_avoid = normalize_avoid(
        option_b_json.get("avoid_today", []),
        profile_name,
        area="general",
        asset=general_asset,
        engine=general_engine,
        forbidden_roots=positive_roots,
    )

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
        "career_paragraph": career_paragraph,
        "career_bullets": career_bullets,
        "love_paragraph": love_paragraph,
        "love_attached": love_attached,
        "love_single": love_single,
        "health_paragraph": health_paragraph,
        "health_opts": health_opts,
        "finance_paragraph": finance_paragraph,
        "finance_bullets": finance_bullets,
        "do_today": general_do,
        "avoid_today": general_avoid,
        "caution_window": caution_window,
        "remedies": remedy_lines[:MAX_LIST_ITEMS],
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
    return _sanitize_value(ctx)


def render(option_b_json: dict[str, Any], templates_dir: str | None = None) -> str:
    env = _env(Path(templates_dir) if templates_dir else TEMPLATES_DIR)
    tmpl = env.get_template("template.json.j2")
    ctx = build_context(option_b_json)
    return tmpl.render(**ctx)
