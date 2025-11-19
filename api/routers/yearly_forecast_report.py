from fastapi import APIRouter, Body, HTTPException

from ..schemas.yearly_forecast_report import YearlyForecastReportResponse, YearlyForecastRequest
from ..services.yearly_forecast_report import generate_yearly_forecast_with_pdf
from ..services.llm_client import LLMUnavailableError

router = APIRouter(prefix="/v1/forecasts/yearly", tags=["yearly-forecast"])


@router.post("/forecast", response_model=YearlyForecastReportResponse)
async def yearly_forecast_report(req: YearlyForecastRequest = Body(...)):
    try:
        return await generate_yearly_forecast_with_pdf(req)
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # pragma: no cover - unexpected runtime
        raise HTTPException(status_code=500, detail="Failed to generate yearly forecast report") from exc
