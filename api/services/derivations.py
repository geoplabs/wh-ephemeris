from typing import Dict, List
from .constants import SIGN_NAMES

ELEMENT = {
  "Aries":"fire","Leo":"fire","Sagittarius":"fire",
  "Taurus":"earth","Virgo":"earth","Capricorn":"earth",
  "Gemini":"air","Libra":"air","Aquarius":"air",
  "Cancer":"water","Scorpio":"water","Pisces":"water",
}
MODALITY = {
  "Aries":"cardinal","Cancer":"cardinal","Libra":"cardinal","Capricorn":"cardinal",
  "Taurus":"fixed","Leo":"fixed","Scorpio":"fixed","Aquarius":"fixed",
  "Gemini":"mutable","Virgo":"mutable","Sagittarius":"mutable","Pisces":"mutable",
}
EXALT = {"Sun":"Aries","Moon":"Taurus","Mercury":"Virgo","Venus":"Pisces","Mars":"Capricorn","Jupiter":"Cancer","Saturn":"Libra"}
RULERS = {"Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon","Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars","Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"}
OPPOSITE = {"Aries":"Libra","Taurus":"Scorpio","Gemini":"Sagittarius","Cancer":"Capricorn","Leo":"Aquarius","Virgo":"Pisces","Libra":"Aries","Scorpio":"Taurus","Sagittarius":"Gemini","Capricorn":"Cancer","Aquarius":"Leo","Pisces":"Virgo"}


def balances(bodies: list) -> (Dict[str,int], Dict[str,int]):
    e = {"fire":0,"earth":0,"air":0,"water":0}
    m = {"cardinal":0,"fixed":0,"mutable":0}
    for b in bodies:
        s = b["sign"]
        e[ELEMENT[s]] += 1
        m[MODALITY[s]] += 1
    return e, m


def dignities(bodies: list) -> List[Dict[str,str]]:
    out=[]
    for b in bodies:
        p, s = b["name"], b["sign"]
        if EXALT.get(p)==s: dig="exaltation"
        elif OPPOSITE.get(EXALT.get(p,""))==s: dig="fall"
        elif RULERS.get(s)==p: dig="domicile"
        elif OPPOSITE.get(s) and RULERS.get(OPPOSITE[s])==p: dig="detriment"
        else: dig="neutral"
        out.append({"planet":p,"dignity":dig,"sign":s})
    return out


def notes(bodies: list, aspects: list, houses: list|None) -> list[str]:
    ns=[]
    # element dominance
    e, m = balances(bodies)
    top_e = max(e, key=e.get); top_m = max(m, key=m.get)
    if e[top_e] >= 4: ns.append(f"Strong {top_e} emphasis")
    if m[top_m] >= 4: ns.append(f"{top_m.capitalize()} modality emphasis")
    # retrogrades
    rets = [b["name"] for b in bodies if b.get("retro")]
    if rets: ns.append("Retrograde: " + ", ".join(rets))
    # angular emphasis (if houses present)
    if houses:
        angular = [b["name"] for b in bodies if b.get("house") in (1,4,7,10)]
        if len(angular) >= 3: ns.append("Angular emphasis (1/4/7/10)")
    return ns


def snapshot(core):
    sun = next((b for b in core["bodies"] if b["name"]=="Sun"), None)
    moon = next((b for b in core["bodies"] if b["name"]=="Moon"), None)
    asc = None
    if core.get("angles") and core["angles"].get("ascendant") is not None:
        asc_deg = core["angles"]["ascendant"]
        from .constants import sign_name_from_lon
        asc = {"deg": round(asc_deg,2), "sign": sign_name_from_lon(asc_deg)}
    return {
        "sun": sun and {"sign": sun["sign"], "house": sun.get("house")},
        "moon": moon and {"sign": moon["sign"], "house": moon.get("house"), "nakshatra": moon.get("nakshatra")},
        "asc": asc,
    }


def strengths_and_growth(ebal, mbal, digs, aspects):
    pros, cons = [], []
    for k,v in ebal.items():
        if v >= 4: pros.append(f"Strong {k} element")
    for k,v in mbal.items():
        if v >= 4: pros.append(f"{k.capitalize()} emphasis")
    neg = [d for d in digs if d["dignity"] in ("fall","detriment")]
    pos = [d for d in digs if d["dignity"] in ("exaltation","domicile")]
    if pos: pros += [f'{d["planet"]} {d["dignity"]} in {d["sign"]}' for d in pos[:3]]
    if neg: cons += [f'{d["planet"]} {d["dignity"]} in {d["sign"]}' for d in neg[:3]]
    hard = [a for a in aspects if a["type"] in ("square","opposition")]
    soft = [a for a in aspects if a["type"] in ("trine","sextile")]
    if soft: pros.append("Supportive aspect patterns (trines/sextiles)")
    if hard: cons.append("Growth-through-challenge aspects (squares/oppositions)")
    return pros[:6], cons[:6]
