import logging
import traceback
from fastapi import APIRouter, Body, HTTPException

from ..schemas.yearly_forecast_report import YearlyForecastReportResponse, YearlyForecastRequest
from ..schemas.yearly_forecast_brief import BriefYearlyForecastResponse
from ..services.yearly_forecast_report import generate_yearly_forecast_with_pdf
from ..services.yearly_forecast_brief import generate_brief_yearly_forecast
from ..services.llm_client import LLMUnavailableError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/forecasts/yearly", tags=["yearly-forecast"])


@router.post("/forecast", response_model=YearlyForecastReportResponse)
async def yearly_forecast_report(req: YearlyForecastRequest = Body(...)):
    """
    Generate detailed yearly forecast with PDF.
    
    This endpoint:
    - Generates a comprehensive yearly forecast
    - Creates a PDF report
    - Returns JSON data + PDF download URL
    - Suitable for detailed reports
    """
    try:
        return await generate_yearly_forecast_with_pdf(req)
    except LLMUnavailableError as exc:
        logger.error(f"LLM_UNAVAILABLE: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # pragma: no cover - unexpected runtime
        # Log full traceback for debugging
        logger.error(f"YEARLY_FORECAST_ERROR: {exc}")
        logger.error(f"TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate yearly forecast report: {str(exc)}") from exc


@router.post("/brief", response_model=BriefYearlyForecastResponse)
async def yearly_forecast_brief(req: YearlyForecastRequest = Body(...)):
    """
    Generate brief yearly forecast (JSON only, no PDF).
    
    This endpoint:
    - Uses same input as the /forecast endpoint
    - Returns concise JSON summary (no PDF generation)
    - Includes: overview, monthly highlights, life areas, major transits
    - Suitable for: mobile apps, quick previews, API integrations
    - Much faster than PDF endpoint (no PDF rendering)
    
    Response includes:
    - Yearly overview with main themes and energy score
    - 12 monthly highlights with key dates
    - Life area summaries (career, love, health, etc.)
    - Major transits and eclipses
    - Quick recommendations
    """
    try:
        return await generate_brief_yearly_forecast(req)
    except LLMUnavailableError as exc:
        logger.error(f"LLM_UNAVAILABLE (brief): {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # pragma: no cover - unexpected runtime
        logger.error(f"YEARLY_FORECAST_BRIEF_ERROR: {exc}")
        logger.error(f"TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate brief yearly forecast: {str(exc)}") from exc
