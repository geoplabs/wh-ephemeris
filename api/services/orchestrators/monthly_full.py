import os, requests, calendar, datetime as dt
from typing import Dict, Any, List, Tuple

from ..mini_calendar_svg import mini_calendar_svg

USE_HTTP = os.getenv("MONTHLY_USE_HTTP", "false").lower() == "true"
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


def get_monthly(chart_input: dict, options: dict) -> dict:
    body = {"chart_input": chart_input, "options": options}
    if USE_HTTP:
        return call("/v1/forecasts/monthly", body)
    from ..forecast_builders import monthly_payload

    data = monthly_payload(chart_input, options)
    return {"events": data["events"], "highlights": data["highlights"]}


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


SUPPORTIVE = {"trine", "sextile"}
CHALLENGING = {"square", "opposition"}


def classify_aspect(a: str) -> str:
    if a in SUPPORTIVE:
        return "supportive"
    if a in CHALLENGING:
        return "challenging"
    return "transformational"


def severity_from_score(score: float) -> str:
    return "major" if score >= 8.5 else "strong" if score >= 7 else "notable" if score >= 5 else "subtle"


def domain_tags(natal_body: str, natal_house: int | None) -> List[str]:
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
    if not tags:
        tags.append("general")
    return list(dict.fromkeys(tags))


def month_window(year: int, month: int) -> Tuple[str, str]:
    _, last = calendar.monthrange(year, month)
    return (f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}")


def week_index(d: dt.date) -> str:
    # Weeks W1..W4/5 by day-of-month (1–7, 8–14, 15–21, 22–end)
    if d.day <= 7:
        return "W1"
    if d.day <= 14:
        return "W2"
    if d.day <= 21:
        return "W3"
    return "W4/5"


def build_viewmodel(
    chart_input: dict,
    options: dict,
    name=None,
    place_label=None,
    include_interpretation=True,
    include_dasha=False,
) -> dict:
    natal = get_natal(chart_input)
    year, month = options["year"], options["month"]
    # Ensure Moon included for monthly granularity unless explicitly removed
    t_bodies = options.get("transit_bodies") or [
        "Sun",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Moon",
    ]
    opt = dict(options)
    opt["transit_bodies"] = t_bodies
    mon = get_monthly(chart_input, opt)  # {"events":[...], "highlights":[...]} shape from M4

    # map natal target → house if known
    houses_known = bool(natal.get("houses"))
    house_of_body = {b["name"]: b.get("house") for b in natal.get("bodies", [])}

    # classify + enrich
    planet_activity = {}
    events = []
    for ev in mon.get("events", []):
        planet_activity[ev["transit_body"]] = planet_activity.get(ev["transit_body"], 0) + 1
        nb, nh = ev["natal_body"], house_of_body.get(ev["natal_body"])
        ev["domains"] = domain_tags(nb, nh)
        ev["severity"] = severity_from_score(ev.get("score", 5))
        events.append(ev)

    # weekly buckets
    wblocks = {"W1": {"events": []}, "W2": {"events": []}, "W3": {"events": []}, "W4/5": {"events": []}}
    for ev in events:
        d = dt.date.fromisoformat(ev["date"])
        wk = week_index(d)
        wblocks[wk]["events"].append(ev)

    def tone_bucket(lst: List[dict]) -> str:
        net = 0
        for e in lst:
            k = classify_aspect(e["aspect"])
            if k == "supportive":
                net += 1
            elif k == "challenging":
                net -= 1
        return "supportive" if net >= 2 else "mixed" if -1 <= net <= 1 else "testing"

    # summaries (AI optional)
    if include_interpretation:
        win = month_window(year, month)
        interp = get_interpret(chart_input, win)
        month_summary = interp.get("month_summaries", {}).get(
            f"{year}-{month:02d}", "A month with activity across personal domains."
        )
    else:
        month_summary = "A month with activity across personal domains."

    totals = {"supportive": 0, "challenging": 0, "transformational": 0}
    for e in events:
        totals[classify_aspect(e["aspect"])] += 1

    key_themes = []
    if totals["supportive"] > totals["challenging"]:
        key_themes.append("Overall supportive opportunities")
    if planet_activity.get("Saturn", 0) >= 3:
        key_themes.append("Responsibility/structure themes")
    if planet_activity.get("Jupiter", 0) >= 3:
        key_themes.append("Growth and learning openings")
    if not key_themes:
        key_themes = ["Mixed influences; pick your windows"]

    # build week blocks
    weeks = {}
    from itertools import islice

    for k, blk in wblocks.items():
        lst = sorted(blk["events"], key=lambda x: (-(x.get("score", 0)), x.get("orb", 9.9)))
        top = list(islice(lst, 5))
        weeks[k] = {
            "summary": "Meaningful movement this week." if lst else "Quieter week.",
            "tone": tone_bucket(lst),
            "top_events": [
                {
                    "title": f'{ev["transit_body"]} {ev["aspect"]} {ev["natal_body"]}',
                    "date": ev["date"],
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
            "calendar": [
                {
                    "date": e["date"],
                    "label": f'{e["transit_body"]} {e["aspect"]} {e["natal_body"]}',
                    "domains": e["domains"],
                }
                for e in sorted(lst, key=lambda x: x["date"])[:10]
            ],
        }

    # key dates = top 6 across the month
    key_dates = [
        {
            "date": e["date"],
            "label": f'{e["transit_body"]} {e["aspect"]} {e["natal_body"]}',
            "domains": e["domains"],
        }
        for e in sorted(events, key=lambda x: -(x.get("score", 0)))[:6]
    ]

    vedic_extras = None
    if chart_input["system"] == "vedic" and include_dasha:
        dash = get_dashas(chart_input)
        # filter dasha periods that overlap month (light: let Codex wire proper date math)
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

    # Mini-calendar highlights
    marked = sorted({int(d["date"].split("-")[2]) for d in key_dates if "date" in d})
    mini_svg = mini_calendar_svg(year, month, marked_days=marked, primary="#4A3AFF")

    vm = {
        "header": {
            "name": name,
            "year": year,
            "month": month,
            "system": chart_input["system"],
            "zodiac": "sidereal" if chart_input["system"] == "vedic" else "tropical",
            "ayanamsha": (chart_input.get("options") or {}).get("ayanamsha"),
            "house_system": (chart_input.get("options") or {}).get(
                "house_system",
                "placidus" if chart_input["system"] == "western" else "whole_sign",
            ),
            "time_known": chart_input.get("time_known", True),
            "place_label": place_label,
        },
        "overview": {
            "month_summary": month_summary,
            "tone": tone_bucket(events),
            "key_themes": key_themes,
            "totals": totals,
            "planet_activity": planet_activity,
        },
        "weeks": weeks,
        "key_dates": key_dates,
        "vedic_extras": vedic_extras,
        "assets": {"mini_calendar_svg": mini_svg, "pdf_download_url": None},
    }
    return vm
