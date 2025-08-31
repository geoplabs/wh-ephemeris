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
    chart_input: Dict[str, Any], window: Dict[str, str], options: Dict[str, Any]
) -> Dict[str, Any]:
    tone = options.get("tone", "professional")
    length = options.get("length", "short")
    start = date.fromisoformat(window["from"])
    end = date.fromisoformat(window["to"])
    month_summaries = {
        d.strftime("%Y-%m"): TRANSIT_SNIPPETS["month"] for d in _iterate_months(start, end)
    }
    key_dates = [
        {
            "date": window["from"],
            "event": TRANSIT_SNIPPETS["event"],
            "note": "Beginning of the cycle",
        }
    ]
    return {
        "meta": {"range": f"{window['from']} to {window['to']}", "tone": tone, "length": length},
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
