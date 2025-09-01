from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

from ..schemas.charts import ChartInput
from ..schemas.yearly_viewmodel import YearlyViewModel
from ..services.orchestrators.yearly_full import build_viewmodel
from ..jobs.queue import enqueue_report_job

router = APIRouter(prefix="/v1/yearly", tags=["yearly"])


class YearlyFullRequest(BaseModel):
    chart_input: ChartInput
    options: Dict[str, Any]
    name: Optional[str] = None
    place_label: Optional[str] = None
    include_interpretation: bool = True
    include_dasha: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chart_input": {
                    "system": "vedic",
                    "date": "1990-08-18",
                    "time": "14:32:00",
                    "time_known": True,
                    "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
                    "options": {"ayanamsha": "lahiri", "house_system": "whole_sign"},
                },
                "options": {
                    "year": 2025,
                    "step_days": 1,
                    "transit_bodies": [
                        "Sun",
                        "Mercury",
                        "Venus",
                        "Mars",
                        "Jupiter",
                        "Saturn",
                    ],
                    "aspects": {
                        "types": [
                            "conjunction",
                            "opposition",
                            "square",
                            "trine",
                            "sextile",
                        ],
                        "orb_deg": 3.0,
                    },
                },
                "name": "Sample User",
                "place_label": "Hyderabad, India",
                "include_interpretation": True,
                "include_dasha": True,
            }
        }
    )


@router.post("/full", response_model=YearlyViewModel)
def yearly_full(req: YearlyFullRequest):
    vm = build_viewmodel(
        req.chart_input.model_dump(),
        req.options,
        name=req.name,
        place_label=req.place_label,
        include_interpretation=req.include_interpretation,
        include_dasha=req.include_dasha,
    )
    return vm


class YearlyReportRequest(YearlyFullRequest):
    branding: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None


@router.post("/full/report")
def yearly_full_report(req: YearlyReportRequest):
    vm = build_viewmodel(
        req.chart_input.model_dump(),
        req.options,
        name=req.name,
        place_label=req.place_label,
        include_interpretation=req.include_interpretation,
        include_dasha=req.include_dasha,
    )
    rid = enqueue_report_job(
        {
            "product": "full_yearly_pdf",
            "viewmodel": vm,
            "branding": req.branding or {},
            "idempotency_key": req.idempotency_key,
        }
    )
    return {"report_id": rid, "status": "queued"}
