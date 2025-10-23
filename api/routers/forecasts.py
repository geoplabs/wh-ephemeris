from fastapi import APIRouter, Body, Request, Response, HTTPException
from ..schemas import (
    YearlyForecastRequest,
    YearlyForecastResponse,
    MonthlyForecastRequest,
    MonthlyForecastResponse,
    DailyForecastRequest,
    DailyForecastResponse,
    DailyTemplatedResponse,
)
import logging

from ..services.forecast_builders import yearly_payload, monthly_payload, daily_payload
from ..services.forecast_reports import generate_yearly_pdf, generate_monthly_pdf
from ..services.daily_template import generate_daily_template


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/forecasts", tags=["forecasts"])


@router.post("/daily", response_model=DailyForecastResponse)
def compute_daily(
    req: DailyForecastRequest = Body(
        ...,
        example={
            "chart_input": {
                "system": "western",
                "date": "1990-08-18",
                "time": "14:32:00",
                "time_known": True,
                "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            },
            "options": {
                "date": "2024-01-15",
                "profile_name": "Asha",
                "areas": ["career", "love", "health"],
            },
        },
    )
):
    chart_input = req.chart_input.model_dump()
    options = req.options.model_dump()
    data = daily_payload(chart_input, options)
    return DailyForecastResponse(**data)


@router.post("/daily/forecast", response_model=DailyTemplatedResponse)
def compute_daily_forecast(
    request: Request,
    response: Response,
    req: DailyForecastRequest = Body(
        ...,
        example={
            "chart_input": {
                "system": "western",
                "date": "1990-08-18",
                "time": "14:32:00",
                "time_known": True,
                "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            },
            "options": {
                "date": "2024-01-15",
                "profile_name": "Asha",
                "use_ai": True,
                "areas": ["career", "love", "health", "finance"],
            },
        },
    ),
):
    chart_input = req.chart_input.model_dump()
    options = req.options.model_dump()
    base_daily = daily_payload(chart_input, options)
    base_json = DailyForecastResponse(**base_daily).model_dump(mode="json")
    use_ai = options.get("use_ai", False)  # Default to False for backward compatibility
    result = generate_daily_template(base_json, request.headers, use_ai=use_ai)

    headers = {
        "ETag": result.etag,
        "Cache-Control": result.cache_control,
    }
    if result.not_modified:
        return Response(status_code=304, headers=headers)

    response.headers.update(headers)
    if result.payload is None:
        raise HTTPException(status_code=500, detail="Unable to build daily template")
    return result.payload


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
