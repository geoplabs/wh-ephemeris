from fastapi import APIRouter
from ..schemas import DashaComputeRequest, DashaComputeResponse
from ..services.dashas_vimshottari import compute_vimshottari

router = APIRouter(prefix="/v1/dashas", tags=["dashas"])

@router.post("/compute", response_model=DashaComputeResponse)
def compute_dashas(req: DashaComputeRequest):
    # Force Vedic assumptions regardless of chart_input.system (dashas are Vedic)
    ayan = (req.chart_input.options or {}).get("ayanamsha","lahiri")
    periods = compute_vimshottari(req.chart_input.model_dump(), levels=req.options.levels, ayanamsha=ayan)
    return DashaComputeResponse(
        meta={"system":"vedic","ayanamsha":ayan,"levels":req.options.levels},
        periods=periods
    )
