import os
import requests
from typing import Dict, Any, List, Tuple

from ..derivations import ELEMENT, MODALITY  # reuse maps if exposed
from ..constants import sign_name_from_lon
from ..wheel_svg import simple_wheel_svg  # optional for calendar/timeline icons

USE_HTTP = os.getenv("YEARLY_USE_HTTP", "false").lower() == "true"
BASE = os.getenv("INTERNAL_BASE_URL", "http://localhost:8080")
HEADERS = {"Authorization": os.getenv("INTERNAL_AUTH_HEADER", "")}


def call(path: str, json: dict) -> dict:
    r = requests.post(f"{BASE}{path}", json=json, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()


def get_natal(chart_input: dict) -> dict:
    if USE_HTTP:
        return call("/v1/charts/compute", chart_input)
    from ..orchestrators.natal_full import _compute_core
    return _compute_core(chart_input)


def get_yearly(chart_input: dict, options: dict) -> dict:
    body = {"chart_input": chart_input, "options": options}
    if USE_HTTP:
        return call("/v1/forecasts/yearly", body)
    from ..forecast_builders import yearly_payload
    data = yearly_payload(chart_input, options)
    return {"months": data["months"]}


def get_interpret(chart_input: dict, window: Tuple[str, str]) -> dict:
    body = {
        "chart_input": chart_input,
        "window": {"from": window[0], "to": window[1]},
        "options": {"tone": "professional", "length": "short", "language": "en"},
    }
    if USE_HTTP:
        return call("/v1/interpret/transits", body)
    from ..narratives.assembler import interpret_transits
    return interpret_transits(chart_input, body["window"], body["options"])


def get_dashas(chart_input: dict) -> dict:
    body = {"chart_input": chart_input, "options": {"levels": 2}}
    if USE_HTTP:
        return call("/v1/dashas/compute", body)
    from ..dashas_vimshottari import compute_vimshottari
    ayan = (chart_input.get("options") or {}).get("ayanamsha", "lahiri")
    periods = compute_vimshottari(chart_input, levels=2, ayanamsha=ayan)
    return {"periods": periods}


# ---- helpers ----
SUPPORTIVE = {("trine"), ("sextile")}
CHALLENGING = {("square"), ("opposition")}
TRANSFORM = {("conjunction")}  # treat dynamically via planet pairs if you want


def classify_aspect(a: str) -> str:
    if a in SUPPORTIVE:
        return "supportive"
    if a in CHALLENGING:
        return "challenging"
    return "transformational"


def domain_tags(natal_body: str, natal_house: int | None) -> List[str]:
    # similar to earlier rules; safe fallback if houses unknown
    tags = []
    if natal_body in ("Venus", "7th"):
        tags.append("love")
    if natal_body in ("Sun", "MC"):
        tags.append("career")
    if natal_house in (7,):
        tags.append("love")
    if natal_house in (10,):
        tags.append("career")
    if natal_house in (2, 8):
        tags.append("money")
    if natal_house in (6,):
        tags.append("health")
    if natal_house in (9, 12):
        tags.append("spiritual")
    if len(tags) == 0:
        tags.append("general")
    return list(dict.fromkeys(tags))


def cluster_events(dates: List[str], max_gap: int = 2) -> List[Tuple[str, str]]:
    # simple clustering by date strings (YYYY-MM-DD) assuming they’re sorted
    # leave implementation light; Codex to flesh out.
    return [(dates[0], dates[-1])] if dates else []


def severity_from_score(score: float) -> str:
    return (
        "major"
        if score >= 8.5
        else "strong"
        if score >= 7
        else "notable"
        if score >= 5
        else "subtle"
    )


def month_key(d: str) -> str:
    return d[:7]  # "YYYY-MM"


def tone_bucket(events: List[dict]) -> str:
    net = 0
    for e in events:
        k = classify_aspect(e["aspect"])
        if k == "supportive":
            net += 1
        elif k == "challenging":
            net -= 1
    return "supportive" if net >= 2 else "mixed" if -1 <= net <= 1 else "testing"


def build_viewmodel(
    chart_input: dict,
    options: dict,
    name=None,
    place_label=None,
    include_interpretation=True,
    include_dasha=True,
) -> dict:
    natal = get_natal(chart_input)
    year = options["year"]
    yr = get_yearly(chart_input, options)
    houses_known = bool(natal.get("houses"))
    house_of_body = {b["name"]: b.get("house") for b in natal.get("bodies", [])}
    planet_activity: Dict[str, int] = {}
    all_events: List[Tuple[str, dict]] = []
    for m, items in yr["months"].items():
        for e in items:
            planet_activity[e["transit_body"]] = planet_activity.get(e["transit_body"], 0) + 1
            nb = e["natal_body"]
            nh = house_of_body.get(nb)
            e["domains"] = domain_tags(nb, nh)
            e["severity"] = severity_from_score(e.get("score", 5))
            all_events.append((m, e))

    if include_interpretation:
        interp = get_interpret(chart_input, (f"{year}-01-01", f"{year}-12-31"))
        month_summaries = interp.get("month_summaries", {})
    else:
        month_summaries = {}

    events_by_month: Dict[str, List[dict]] = {}
    for m, e in all_events:
        events_by_month.setdefault(m, []).append(e)

    months: Dict[str, Any] = {}
    key_dates: List[Dict[str, Any]] = []
    for m, lst in events_by_month.items():
        lst_sorted = sorted(lst, key=lambda x: (-(x.get("score", 0)), x.get("orb", 9.9)))
        top = lst_sorted[:5]
        tone = tone_bucket(lst_sorted)
        cal: List[Dict[str, Any]] = []
        for ev in sorted(lst_sorted, key=lambda x: x["date"])[:8]:
            cal.append(
                {
                    "date": ev["date"],
                    "label": f"{ev['transit_body']} {ev['aspect']} {ev['natal_body']}",
                    "domains": ev["domains"],
                }
            )
        months[m] = {
            "summary": month_summaries.get(m, "A month with meaningful movement across personal domains."),
            "tone": tone,
            "top_events": [
                {
                    "title": f"{ev['transit_body']} {ev['aspect']} {ev['natal_body']}",
                    "date": ev["date"],
                    "window": ev.get("window"),
                    "peak_date": ev.get("peak_date", ev["date"]),
                    "transit_body": ev["transit_body"],
                    "natal_body": ev["natal_body"],
                    "aspect": ev["aspect"],
                    "orb": ev["orb"],
                    "applying": ev.get("applying"),
                    "domains": ev["domains"],
                    "severity": ev["severity"],
                    "description": ev.get("description") or ev.get("copy"),
                    "notes": [],
                }
                for ev in top
            ],
            "calendar": cal,
        }

    totals = {"supportive": 0, "challenging": 0, "transformational": 0}
    for _, e in all_events:
        totals[classify_aspect(e["aspect"])] += 1

    key_themes: List[str] = []
    if totals["supportive"] > totals["challenging"]:
        key_themes.append("Overall supportive momentum")
    if planet_activity.get("Saturn", 0) > 6:
        key_themes.append("Saturn emphasizes structure and responsibilities")
    if planet_activity.get("Jupiter", 0) > 6:
        key_themes.append("Jupiter expands growth opportunities")
    if not key_themes:
        key_themes = ["Mixed year with focused windows of progress"]

    domains_summary = {
        "career": "Watch windows near strong Sun/MC and 10th-house activations.",
        "love": "Venus and 7th-house contacts highlight bonding and negotiation.",
        "health": "6th-house and Saturn/Mars contacts advise pacing and routines.",
        "spiritual": "9th/12th-house, Nodes and Neptune encourage reflection.",
    }

    top_global = sorted((e for _, e in all_events), key=lambda x: -(x.get("score", 0)))[:10]
    for ev in top_global:
        key_dates.append(
            {
                "date": ev["date"],
                "label": f"{ev['transit_body']} {ev['aspect']} {ev['natal_body']}",
                "domains": ev["domains"],
            }
        )

    vedic_extras = None
    if chart_input["system"] == "vedic" and include_dasha:
        dash = get_dashas(chart_input)
        periods = [
            {
                "level": p["level"],
                "lord": p["lord"],
                "start": p["start"],
                "end": p["end"],
            }
            for p in dash.get("periods", [])
            if p["level"] in (1, 2)
        ]
        vedic_extras = {"active_periods": periods, "emphasis_notes": []}

    vm = {
        "header": {
            "name": name,
            "year": year,
            "system": chart_input["system"],
            "zodiac": "sidereal" if chart_input["system"] == "vedic" else "tropical",
            "ayanamsha": (chart_input.get("options") or {}).get("ayanamsha"),
            "house_system": (chart_input.get("options") or {}).get(
                "house_system", "placidus" if chart_input["system"] == "western" else "whole_sign"
            ),
            "time_known": chart_input.get("time_known", True),
            "place_label": place_label,
        },
        "overview": {
            "key_themes": key_themes,
            "domains_summary": domains_summary,
            "totals": totals,
            "planet_activity": planet_activity,
        },
        "months": months,
        "key_dates": key_dates,
        "vedic_extras": vedic_extras,
        "assets": {"timeline_svg": None, "calendar_svg": None, "pdf_download_url": None},
    }
    return vm
