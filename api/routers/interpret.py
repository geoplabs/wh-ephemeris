from fastapi import APIRouter, Body

from ..schemas import (
    NatalInterpretRequest,
    NatalInterpretResponse,
    TransitsInterpretRequest,
    TransitsInterpretResponse,
    CompatibilityInterpretRequest,
    CompatibilityInterpretResponse,
)
from ..services.narratives.assembler import (
    interpret_natal,
    interpret_transits,
    interpret_compatibility,
)

router = APIRouter(prefix="/v1/interpret", tags=["interpret"])


@router.post("/natal", response_model=NatalInterpretResponse)
def interpret_natal_endpoint(
    req: NatalInterpretRequest = Body(
        ...,
        example={
            "chart_input": {
                "system": "western",
                "date": "1990-08-18",
                "time": "14:32:00",
                "time_known": True,
                "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            },
            "options": {"tone": "mystical", "length": "medium"},
        },
    )
) -> NatalInterpretResponse:
    data = interpret_natal(req.chart_input.model_dump(), req.options.model_dump())
    return NatalInterpretResponse(**data)


@router.post("/transits", response_model=TransitsInterpretResponse)
def interpret_transits_endpoint(
    req: TransitsInterpretRequest = Body(
        ...,
        example={
            "chart_input": {
                "system": "western",
                "date": "1990-08-18",
                "time": "14:32:00",
                "time_known": True,
                "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            },
            "window": {"from": "2025-01-01", "to": "2025-06-30"},
            "options": {"tone": "professional", "length": "short"},
        },
    )
) -> TransitsInterpretResponse:
    data = interpret_transits(
        req.chart_input.model_dump(),
        {"from": req.window.from_, "to": req.window.to},
        req.options.model_dump(),
        req.events_by_month or {},
    )
    return TransitsInterpretResponse(**data)


@router.post("/compatibility", response_model=CompatibilityInterpretResponse)
def interpret_compatibility_endpoint(
    req: CompatibilityInterpretRequest = Body(
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
            "options": {"tone": "casual", "length": "short"},
        },
    )
) -> CompatibilityInterpretResponse:
    data = interpret_compatibility(
        req.person_a.model_dump(), req.person_b.model_dump(), req.options.model_dump()
    )
    return CompatibilityInterpretResponse(**data)
