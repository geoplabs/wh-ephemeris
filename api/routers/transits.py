from fastapi import APIRouter
from ..schemas import TransitsComputeRequest, TransitsComputeResponse
from ..services.transits_engine import compute_transits

router = APIRouter(prefix="/v1/transits", tags=["transits"])

@router.post("/compute", response_model=TransitsComputeResponse)
def compute_transits_route(req: TransitsComputeRequest):
    events = compute_transits(req.chart_input.model_dump(), req.options.model_dump())
    return TransitsComputeResponse(meta={"step_days": req.options.step_days}, events=events)
