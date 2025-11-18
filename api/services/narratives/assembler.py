"""Assemble narrative blocks from rulebook snippets."""
from datetime import date
from typing import Dict, Any, List

from .rulebook import NATAL_SNIPPETS, TRANSIT_SNIPPETS, COMPATIBILITY_SNIPPETS


def interpret_natal(chart_input: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    tone = options.get("tone", "professional")
    length = options.get("length", "medium")
    domains: List[str] = options.get(
        "domains", ["love", "career", "health", "spiritual"]
    )
    sections = {d: NATAL_SNIPPETS.get(d, "") for d in domains}
    return {
        "meta": {"engine_version": "m5.0.0", "tone": tone, "length": length},
        "sections": sections,
        "highlights": ["Sample highlight"],
    }


def _iterate_months(start: date, end: date) -> List[date]:
    months = []
    cur = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while cur <= end_month:
        months.append(cur)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return months


def interpret_transits(
    chart_input: Dict[str, Any],
    window: Dict[str, str],
    options: Dict[str, Any],
    events_by_month: Dict[str, List[Dict[str, Any]]] | None = None,
) -> Dict[str, Any]:
    tone = options.get("tone", "professional")
    length = options.get("length", "short")
    start = date.fromisoformat(window["from"])
    end = date.fromisoformat(window["to"])
    months = _iterate_months(start, end)

    events_by_month = events_by_month or {}

    def _summaries_from_events() -> Dict[str, str]:
        summaries: Dict[str, str] = {}
        for d in months:
            key = d.strftime("%Y-%m")
            events = events_by_month.get(key, [])
            if not events:
                summaries[key] = TRANSIT_SNIPPETS["month"]
                continue
            top = events[0]
            focus_domains = ", ".join(sorted({dom for ev in events for dom in ev.get("domains", [])}))
            tone_hint = top.get("severity", "notable")
            summaries[key] = (
                f"{tone_hint.title()} movements touching {focus_domains or 'multiple areas'}. "
                f"Key window: {top.get('date')} ({top.get('label')})."
            )
        return summaries

    if events_by_month:
        month_summaries = _summaries_from_events()
    else:
        month_summaries = {d.strftime("%Y-%m"): TRANSIT_SNIPPETS["month"] for d in months}

    def _key_dates_from_events() -> List[Dict[str, str]]:
        flattened = [ev | {"month": m} for m, evs in events_by_month.items() for ev in evs]
        top = sorted(
            flattened, key=lambda x: (-(x.get("score") or 0), x.get("date", ""))
        )[:8]
        results: List[Dict[str, str]] = []
        for ev in top:
            results.append(
                {
                    "date": ev.get("date"),
                    "event": ev.get("label"),
                    "note": f"Domains: {', '.join(ev.get('domains', [])) or 'general'}; Severity: {ev.get('severity', 'notable')}",
                }
            )
        return results

    if events_by_month:
        key_dates = _key_dates_from_events()
    else:
        key_dates = [
            {
                "date": window["from"],
                "event": TRANSIT_SNIPPETS["event"],
                "note": "Beginning of the cycle",
            }
        ]

    return {
        "meta": {
            "range": f"{window['from']} to {window['to']}",
            "tone": tone,
            "length": length,
            "events_in_context": bool(events_by_month),
        },
        "month_summaries": month_summaries,
        "key_dates": key_dates,
    }


def interpret_compatibility(
    person_a: Dict[str, Any], person_b: Dict[str, Any], options: Dict[str, Any]
) -> Dict[str, Any]:
    summary = COMPATIBILITY_SNIPPETS["summary"]
    strengths = [COMPATIBILITY_SNIPPETS["strength"]]
    challenges = [COMPATIBILITY_SNIPPETS["challenge"]]
    score = 72
    return {
        "summary": summary,
        "strengths": strengths,
        "challenges": challenges,
        "score": score,
    }
