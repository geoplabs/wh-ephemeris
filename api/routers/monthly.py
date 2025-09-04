from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

from ..schemas.charts import ChartInput
from ..schemas.monthly_viewmodel import MonthlyViewModel
from ..services.orchestrators.monthly_full import build_viewmodel
from ..jobs.queue import enqueue_report_job
from ..services.mini_calendar_svg import mini_calendar_svg

router = APIRouter(prefix="/v1/monthly", tags=["monthly"])


class MonthlyFullRequest(BaseModel):
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
                    "month": 9,
                    "step_days": 1,
                    "transit_bodies": [
                        "Sun",
                        "Mercury",
                        "Venus",
                        "Mars",
                        "Jupiter",
                        "Saturn",
                        "Moon",
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


@router.post("/full", response_model=MonthlyViewModel)
def monthly_full(req: MonthlyFullRequest):
    vm = build_viewmodel(
        req.chart_input.model_dump(),
        req.options,
        name=req.name,
        place_label=req.place_label,
        include_interpretation=req.include_interpretation,
        include_dasha=req.include_dasha,
    )
    return vm


class MonthlyReportRequest(MonthlyFullRequest):
    branding: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None


@router.post("/full/report")
def monthly_full_report(req: MonthlyReportRequest):
    vm = build_viewmodel(
        req.chart_input.model_dump(),
        req.options,
        name=req.name,
        place_label=req.place_label,
        include_interpretation=req.include_interpretation,
        include_dasha=req.include_dasha,
    )
    brand = req.branding or {}
    primary = brand.get("primary_hex")
    if primary:
        year = vm["header"]["year"]
        month = vm["header"]["month"]
        marked = [int(d["date"].split("-")[2]) for d in vm["key_dates"]]
        vm["assets"]["mini_calendar_svg"] = mini_calendar_svg(year, month, marked, primary=primary)
    rid = enqueue_report_job(
        {
            "product": "full_monthly_pdf",
            "viewmodel": vm,
            "branding": brand,
            "idempotency_key": req.idempotency_key,
        }
    )
    return {"report_id": rid, "status": "queued"}
