from fastapi import APIRouter
from hashlib import sha256
from typing import List
from ..schemas import ComputeRequest, ComputeResponse, BodyOut, MetaOut

router = APIRouter(prefix="/v1/charts", tags=["charts"])

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

def _deterministic_degrees(seed: str) -> float:
    # Map seed -> [0, 360)
    h = int(sha256(seed.encode()).hexdigest()[:8], 16)
    return (h % 36000) / 100.0

def _sign_from_lon(lon: float) -> str:
    idx = int(lon // 30) % 12
    return SIGNS[idx]

@router.post("/compute", response_model=ComputeResponse)
def compute_chart(req: ComputeRequest):
    # Deterministic-but-fake longitudes so the contract is visible.
    seed = f"{req.system}|{req.date}|{req.time}|{req.place.lat:.4f}|{req.place.lon:.4f}|{req.place.tz}"
    bodies = []
    for name in ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","TrueNode","Chiron"]:
        lon = (_deterministic_degrees(seed + name))
        bodies.append(BodyOut(name=name, lon=round(lon, 2), sign=_sign_from_lon(lon), house=None if not req.time_known else ((int(lon) % 12) + 1)))

    meta = MetaOut(
        zodiac="tropical" if req.system == "western" else "sidereal",
        house_system="placidus" if req.system == "western" else "whole_sign",
        ayanamsha="lahiri" if req.system == "vedic" else None
    )
    chart_id = sha256((seed+"|chart").encode()).hexdigest()[:24]
    return ComputeResponse(
        chart_id=f"cht_{chart_id}",
        meta=meta,
        angles=None if not req.time_known else {"ascendant": round(_deterministic_degrees(seed+"ASC"), 2), "mc": round(_deterministic_degrees(seed+"MC"), 2)},
        houses=None if not req.time_known else [{"num": i+1, "cusp_lon": round((i*30.0) % 360.0, 2)} for i in range(12)],
        bodies=bodies,
        aspects=[],
    )
