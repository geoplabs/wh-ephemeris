import os
import requests
from typing import Dict, Any

from ..ephem import ENGINE_VERSION
from ..constants import sign_name_from_lon
from ..derivations import balances, dignities, notes, snapshot, strengths_and_growth
from .. import ephem
from ..houses import houses as houses_svc, house_of
from ..aspects import find_aspects
from ..vedic import nakshatra_from_lon_sidereal
from ..remedies_engine import compute_remedies
from ..dashas_vimshottari import compute_vimshottari
from ..wheel_svg import simple_wheel_svg

USE_HTTP = os.getenv("NATAL_USE_HTTP", "false").lower() == "true"
BASE = os.getenv("INTERNAL_BASE_URL", "http://localhost:8080")
HEADERS = {"Authorization": os.getenv("INTERNAL_AUTH_HEADER", "")}


def _chart_via_api(chart_input):
    r = requests.post(f"{BASE}/v1/charts/compute", json=chart_input, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()


def _interpret_via_api(chart_input):
    body = {
        "chart_input": chart_input,
        "options": {
            "tone": "professional",
            "length": "medium",
            "language": "en",
            "domains": ["love", "career", "health", "spiritual"],
        },
    }
    r = requests.post(f"{BASE}/v1/interpret/natal", json=body, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()


def _remedies_via_api(chart_input):
    r = requests.post(
        f"{BASE}/v1/remedies/compute",
        json={"chart_input": chart_input, "options": {"allow_gemstones": True}},
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def _dashas_via_api(chart_input):
    r = requests.post(
        f"{BASE}/v1/dashas/compute",
        json={"chart_input": chart_input, "options": {"levels": 2}},
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def _compute_core(chart_input: Dict[str, Any]) -> Dict[str, Any]:
    sidereal = chart_input["system"] == "vedic"
    ayan = (
        (chart_input.get("options") or {}).get("ayanamsha", "lahiri")
        if sidereal
        else None
    )
    jd = ephem.to_jd_utc(
        chart_input["date"], chart_input["time"], chart_input["place"]["tz"]
    )
    pos = ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayan)

    angles, out_houses, body_house, warnings = None, None, {}, []
    if chart_input.get("time_known", True):
        hs = houses_svc(
            jd,
            chart_input["place"]["lat"],
            chart_input["place"]["lon"],
            (chart_input.get("options") or {}).get(
                "house_system", "placidus" if not sidereal else "whole_sign"
            ),
        )
        angles = {"ascendant": hs["asc"], "mc": hs["mc"]}
        out_houses = [{"num": i + 1, "cusp_lon": hs["cusps"][i]} for i in range(12)]
        for name, p in pos.items():
            body_house[name] = house_of(p["lon"], hs["cusps"])
    else:
        warnings.append("Birth time unknown; using solar whole-sign fallback for houses.")
        sun_lon = pos["Sun"]["lon"]
        start = int(sun_lon // 30) % 12
        for name, p in pos.items():
            sidx = int(p["lon"] // 30) % 12
            dist = (sidx - start) % 12
            body_house[name] = dist + 1

    bodies = []
    for name, p in pos.items():
        item = {
            "name": name,
            "lon": round(p["lon"], 4),
            "sign": sign_name_from_lon(p["lon"]),
            "house": body_house.get(name),
            "retro": p["retro"],
            "speed": round(p["speed_lon"], 6),
        }
        if sidereal and name == "Moon":
            item["nakshatra"] = nakshatra_from_lon_sidereal(p["lon"])
        bodies.append(item)
    aspects = find_aspects(
        {k: {"lon": v["lon"], "speed_lon": v["speed_lon"]} for k, v in pos.items()}
    )
    return {
        "meta": {
            "engine_version": ENGINE_VERSION,
            "zodiac": "sidereal" if sidereal else "tropical",
            "house_system": (chart_input.get("options") or {}).get(
                "house_system", "placidus" if not sidereal else "whole_sign"
            ),
            "ayanamsha": ayan,
        },
        "angles": angles,
        "houses": out_houses,
        "bodies": bodies,
        "aspects": aspects,
        "warnings": warnings or None,
    }


def build_viewmodel(
    chart_input: Dict[str, Any],
    name: str | None = None,
    place_label: str | None = None,
    include_interpretation: bool = True,
    include_remedies: bool = True,
    include_dasha: bool = True,
) -> Dict[str, Any]:
    if USE_HTTP:
        core = _chart_via_api(chart_input)
    else:
        core = _compute_core(chart_input)

    ebal, mbal = balances(core["bodies"])
    digs = dignities(core["bodies"])
    ns = notes(core["bodies"], core["aspects"], core.get("houses"))
    snap = snapshot(core)
    pros, cons = strengths_and_growth(ebal, mbal, digs, core["aspects"])

    summary = (
        "Snapshot of your natal pattern highlighting elements, modalities and key aspects."
    )
    domains = {
        "love": "Your Venus and 7th-house links describe partnership style.",
        "career": "Sun/MC and 10th-house show vocation themes.",
        "health": "6th-house and Saturn aspects indicate routines and vitality structure.",
        "spiritual": "9th/12th-house and Nodes suggest growth and surrender themes.",
    }
    highlights = []
    if core.get("angles") and any(b.get("house") == 10 for b in core["bodies"]):
        highlights.append("Career/visibility emphasis")
    if ebal["fire"] >= 4:
        highlights.append("Strong fire motivation")

    if include_interpretation:
        if USE_HTTP:
            interp = _interpret_via_api(chart_input)
        else:
            interp = {"summary": summary, "domains": domains, "highlights": highlights}
    else:
        interp = {"summary": None, "domains": {}, "highlights": []}

    remedies = (
        _remedies_via_api(chart_input)["remedies"]
        if (include_remedies and USE_HTTP)
        else (
            compute_remedies(chart_input, allow_gemstones=True)
            if include_remedies
            else []
        )
    )

    vedic_extras = None
    if chart_input["system"] == "vedic":
        cur_dasha = None
        if include_dasha:
            if USE_HTTP:
                periods = _dashas_via_api(chart_input)
            else:
                periods = compute_vimshottari(
                    chart_input,
                    levels=2,
                    ayanamsha=(core["meta"].get("ayanamsha") or "lahiri"),
                )
            maha = next((p for p in periods if p.get("level") == 1), None)
            antar = (
                next(
                    (
                        p
                        for p in periods
                        if p.get("level") == 2 and p.get("parent") == maha["lord"]
                    ),
                    None,
                )
                if maha
                else None
            )
            cur_dasha = {
                "maha": (maha["lord"] if maha else None),
                "antar": (antar["lord"] if antar else None),
                "start": (maha["start"] if maha else None),
                "end": (maha["end"] if maha else None),
            }
        vedic_extras = {
            "moon_nakshatra": next(
                (b.get("nakshatra") for b in core["bodies"] if b["name"] == "Moon"),
                None,
            ),
            "current_dasha": cur_dasha,
        }

    wheel = simple_wheel_svg(core["bodies"])

    vm = {
        "header": {
            "name": name,
            "system": chart_input["system"],
            "zodiac": core["meta"]["zodiac"],
            "house_system": core["meta"]["house_system"],
            "ayanamsha": core["meta"].get("ayanamsha"),
            "time_known": chart_input.get("time_known", True),
            "place_label": place_label,
        },
        "core_chart": {
            "angles": core.get("angles"),
            "houses": core.get("houses"),
            "bodies": core["bodies"],
            "aspects": core["aspects"],
            "warnings": core.get("warnings"),
        },
        "analysis": {
            "elements_balance": ebal,
            "modalities_balance": mbal,
            "dignities": digs,
            "retrogrades": [b["name"] for b in core["bodies"] if b.get("retro")],
            "chart_notes": ns,
            "strengths": pros,
            "growth": cons,
        },
        "interpretation": interp,
        "vedic_extras": vedic_extras,
        "remedies": remedies,
        "assets": {"wheel_svg": wheel, "pdf_download_url": None},
    }
    return vm
