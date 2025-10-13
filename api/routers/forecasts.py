from fastapi import APIRouter, Body
from ..schemas import (
    YearlyForecastRequest,
    YearlyForecastResponse,
    MonthlyForecastRequest,
    MonthlyForecastResponse,
)
import logging

from ..services.forecast_builders import yearly_payload, monthly_payload
from ..services.forecast_reports import generate_yearly_pdf, generate_monthly_pdf


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/forecasts", tags=["forecasts"])


@router.post("/yearly", response_model=YearlyForecastResponse)
def compute_yearly(
    req: YearlyForecastRequest = Body(
        ...,
        example={
            "chart_input": {
                "system": "western",
                "date": "1990-08-18",
                "time": "14:32:00",
                "time_known": True,
                "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            },
            "options": {"year": 1991},
        },
    )
):
    chart_input = req.chart_input.model_dump()
    options = req.options.model_dump()
    data = yearly_payload(chart_input, options)
    pdf_url = None
    try:
        _, pdf_url = generate_yearly_pdf(chart_input, options, data)
    except Exception:
        logger.exception("yearly_pdf_generation_failed")
    return YearlyForecastResponse(
        meta={"year": req.options.year},
        months=data["months"],
        top_events=data["top_events"],
        pdf_download_url=pdf_url,
    )


@router.post("/monthly", response_model=MonthlyForecastResponse)
def compute_monthly(
    req: MonthlyForecastRequest = Body(
        ...,
        example={
            "chart_input": {
                "system": "western",
                "date": "1990-08-18",
                "time": "14:32:00",
                "time_known": True,
                "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            },
            "options": {"year": 1990, "month": 9},
        },
    )
):
    chart_input = req.chart_input.model_dump()
    options = req.options.model_dump()
    data = monthly_payload(chart_input, options)
    pdf_url = None
    try:
        _, pdf_url = generate_monthly_pdf(chart_input, options, data)
    except Exception:
        logger.exception("monthly_pdf_generation_failed")
    return MonthlyForecastResponse(
        meta={"year": req.options.year, "month": req.options.month},
        events=data["events"],
        highlights=data["highlights"],
        pdf_download_url=pdf_url,
    )
