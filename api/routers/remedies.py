from fastapi import APIRouter, Body
from ..schemas import RemediesComputeRequest, RemediesComputeResponse
from ..services.remedies_engine import compute_remedies

router = APIRouter(prefix="/v1/remedies", tags=["remedies"])


@router.post("/compute", response_model=RemediesComputeResponse)
def compute_remedies_route(
    req: RemediesComputeRequest = Body(
        ...,
        example={
            "chart_input": {
                "system": "vedic",
                "date": "1990-08-18",
                "time": "14:32:00",
                "time_known": True,
                "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            },
            "options": {"allow_gemstones": True},
        },
    )
):
    items = compute_remedies(
        req.chart_input.model_dump(), allow_gemstones=req.options.allow_gemstones
    )
    return RemediesComputeResponse(
        meta={"allow_gemstones": req.options.allow_gemstones},
        remedies=items,
    )
