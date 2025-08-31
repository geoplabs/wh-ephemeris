from collections import defaultdict
from typing import Dict, Any
from .transits_engine import compute_transits


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
