from fastapi import APIRouter, HTTPException
from hashlib import sha256
import os
from ..schemas import ComputeRequest, ComputeResponse, BodyOut, MetaOut
from ..services import ephem, houses as houses_svc, aspects as aspects_svc, vedic as vedic_svc
from ..services.constants import sign_name_from_lon

router = APIRouter(prefix="/v1/charts", tags=["charts"])

@router.post("/compute", response_model=ComputeResponse)
def compute_chart(req: ComputeRequest):
    ephem.init_paths(os.getenv("EPHEMERIS_DIR"))
    sidereal = (req.system == "vedic")
    ayan = (req.options or {}).get("ayanamsha","lahiri") if sidereal else None
    house_system = (req.options or {}).get("house_system", "placidus" if not sidereal else "whole_sign")

    # JD
    jd = ephem.to_jd_utc(req.date, req.time, req.place.tz)
    # Positions
    pos = ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayan)

    # Houses / Angles
    angles, out_houses, warnings = None, None, []
    if req.time_known:
        hs = houses_svc.houses(jd, req.place.lat, req.place.lon, system=house_system)
        angles = {"ascendant": round(hs["asc"], 4), "mc": round(hs["mc"], 4)}
        out_houses = [{"num": i+1, "cusp_lon": round(hs["cusps"][i], 4)} for i in range(12)]
        # assign houses to bodies
        body_house = {}
        for name, p in pos.items():
            body_house[name] = houses_svc.house_of(p["lon"], hs["cusps"])
    else:
        warnings.append("Birth time unknown; using solar whole-sign fallback for houses.")
        # House 1 = Sun sign; set houses array to None (since no exact cusps)
        body_house = {}
        sun_lon = pos["Sun"]["lon"]
        # whole-sign assignment by sign offset
        start_sign = int(sun_lon // 30) % 12
        for name, p in pos.items():
            sidx = int(p["lon"] // 30) % 12
            # distance in signs from start_sign, 0..11
            dist = (sidx - start_sign) % 12
            body_house[name] = dist + 1
        angles, out_houses = None, None

    # Bodies out
    bodies = []
    for name, p in pos.items():
        b = BodyOut(
            name=name,
            lon=round(p["lon"], 4),
            sign=sign_name_from_lon(p["lon"]),
            house=body_house.get(name),
            retro=p["retro"],
            speed=round(p["speed_lon"], 6),
        )
        if sidereal and name == "Moon":
            b.nakshatra = vedic_svc.nakshatra_from_lon_sidereal(p["lon"])
        bodies.append(b)

    # Aspects
    asp = aspects_svc.find_aspects(pos)

    # Meta & id
    seed = f"{req.system}|{req.date}|{req.time}|{req.place.lat:.6f}|{req.place.lon:.6f}|{req.place.tz}|{house_system}|{ayan or ''}"
    chart_id = "cht_" + sha256(seed.encode()).hexdigest()[:24]

    meta = MetaOut(
        engine="wh-ephemeris",
        engine_version=ephem.ENGINE_VERSION,
        zodiac="sidereal" if sidereal else "tropical",
        house_system=house_system,
        ayanamsha=ayan,
        backend=("moseph" if os.getenv("EPHEMERIS_BACKEND","swieph")=="moseph" else "swieph"),
        warnings=(warnings or None)
    )
    return ComputeResponse(
        chart_id=chart_id,
        meta=meta,
        angles=angles,
        houses=out_houses,
        bodies=bodies,
        aspects=asp
    )
