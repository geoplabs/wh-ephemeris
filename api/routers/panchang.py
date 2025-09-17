"""Panchang API endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..schemas.panchang_viewmodel import PanchangViewModel
from ..services.orchestrators.panchang_full import build_viewmodel
from ..services.panchang_report import generate_panchang_report


router = APIRouter(prefix="/v1/panchang", tags=["panchang"])


class PanchangRequest(BaseModel):
    system: str = "vedic"
    date: Optional[str] = None
    place: Dict[str, Any]
    options: Dict[str, Any] = {}


@router.post("/compute", response_model=PanchangViewModel)
def panchang_compute(req: PanchangRequest):
    return build_viewmodel(req.system, req.date, req.place, req.options)


@router.get("/today", response_model=PanchangViewModel)
def panchang_today(
    lat: float,
    lon: float,
    tz: str = "Asia/Kolkata",
    ayanamsha: str = "lahiri",
    include_muhurta: bool = True,
    include_hora: bool = False,
    place_label: Optional[str] = None,
    lang: str = "en",
    script: str = "latin",
    show_bilingual: bool = False,
):
    options = {
        "ayanamsha": ayanamsha,
        "include_muhurta": include_muhurta,
        "include_hora": include_hora,
        "lang": lang,
        "script": script,
        "show_bilingual": show_bilingual,
    }
    place = {"lat": lat, "lon": lon, "tz": tz, "query": place_label}
    return build_viewmodel("vedic", None, place, options)


class PanchangReportRequest(BaseModel):
    place: Dict[str, Any]
    date: Optional[str] = None
    options: Dict[str, Any] = {}


@router.post("/report")
def panchang_report(req: PanchangReportRequest):
    vm = build_viewmodel("vedic", req.date, req.place, req.options)
    report = generate_panchang_report(vm)
    return report

