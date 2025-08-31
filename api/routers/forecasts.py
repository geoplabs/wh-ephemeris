from fastapi import APIRouter, Body
from ..schemas import (
    YearlyForecastRequest,
    YearlyForecastResponse,
    MonthlyForecastRequest,
    MonthlyForecastResponse,
)
from ..services.forecast_builders import yearly_payload, monthly_payload

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
    data = yearly_payload(req.chart_input.model_dump(), req.options.model_dump())
    return YearlyForecastResponse(
        meta={"year": req.options.year},
        months=data["months"],
        top_events=data["top_events"],
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
    data = monthly_payload(req.chart_input.model_dump(), req.options.model_dump())
    return MonthlyForecastResponse(
        meta={"year": req.options.year, "month": req.options.month},
        events=data["events"],
        highlights=data["highlights"],
    )
