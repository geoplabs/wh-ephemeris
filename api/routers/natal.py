from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

from ..schemas.charts import ChartInput
from ..schemas.viewmodels import NatalViewModel
from ..services.orchestrators.natal_full import build_viewmodel
from ..jobs.queue import enqueue_report_job

router = APIRouter(prefix="/v1/natal", tags=["natal"])


class FullNatalRequest(BaseModel):
    chart_input: ChartInput
    name: Optional[str] = None
    place_label: Optional[str] = None
    include_interpretation: bool = True
    include_remedies: bool = True
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
                "name": "Sample User",
                "place_label": "Hyderabad, India",
                "include_interpretation": True,
                "include_remedies": True,
                "include_dasha": True,
            }
        }
    )


@router.post("/full", response_model=NatalViewModel)
def full_natal(req: FullNatalRequest):
    vm = build_viewmodel(
        req.chart_input.model_dump(),
        name=req.name,
        place_label=req.place_label,
        include_interpretation=req.include_interpretation,
        include_remedies=req.include_remedies,
        include_dasha=req.include_dasha,
    )
    return vm


class FullNatalReportRequest(FullNatalRequest):
    branding: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None


@router.post("/full/report")
def full_natal_report(req: FullNatalReportRequest):
    vm = build_viewmodel(
        req.chart_input.model_dump(),
        name=req.name,
        place_label=req.place_label,
        include_interpretation=req.include_interpretation,
        include_remedies=req.include_remedies,
        include_dasha=req.include_dasha,
    )
    job = {
        "product": "full_natal_pdf",
        "viewmodel": vm,
        "branding": req.branding or {},
        "idempotency_key": req.idempotency_key,
    }
    rid = enqueue_report_job(job)
    return {"report_id": rid, "status": "queued"}
