from fastapi import APIRouter, Body
from ..schemas import CompatibilityComputeRequest, CompatibilityComputeResponse
from ..services.compatibility_engine import synastry, midpoint_composite, aggregate_score

router = APIRouter(prefix="/v1/compatibility", tags=["compatibility"])


@router.post("/compute", response_model=CompatibilityComputeResponse)
def compute_compat(
    req: CompatibilityComputeRequest = Body(
        ...,
        example={
            "person_a": {
                "system": "western",
                "date": "1990-08-18",
                "time": "14:32:00",
                "time_known": True,
                "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            },
            "person_b": {
                "system": "western",
                "date": "1991-03-07",
                "time": "09:15:00",
                "time_known": True,
                "place": {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
            },
            "options": {"include_composite": True},
        },
    )
):
    types = req.options.aspects.get("types", ["conjunction", "opposition", "square", "trine", "sextile"])
    orb = req.options.aspects.get("orb_deg", 4.0)
    syn = synastry(req.person_a.model_dump(), req.person_b.model_dump(), types, orb)
    score = aggregate_score(syn)
    strengths = [f"{s['p1']} {s['type']} {s['p2']}" for s in syn if s["weight"] > 0][:10]
    challenges = [f"{s['p1']} {s['type']} {s['p2']}" for s in syn if s["weight"] < 0][:10]
    comp = (
        midpoint_composite(req.person_a.model_dump(), req.person_b.model_dump())
        if req.options.include_composite
        else None
    )
    return CompatibilityComputeResponse(
        meta={"orb_deg": orb},
        synastry=syn,
        score=score,
        strengths=strengths,
        challenges=challenges,
        composite=comp,
    )
