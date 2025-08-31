from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any

from .charts import ChartInput

# Supported report product identifiers
Product = Literal[
    "western_natal_pdf",
    "advanced_natal_pdf",
    "transit_forecast_pdf",
    "yearly_forecast_pdf",
    "monthly_horoscope_pdf",
    "compatibility_pdf",
    "remedies_pdf",
    "spiritual_mission_pdf",
]


class Branding(BaseModel):
    """Optional branding information for a report."""

    logo_url: Optional[str] = None
    primary_hex: Optional[str] = "#4A3AFF"


class ReportCreateRequest(BaseModel):
    """Request payload for enqueuing a report render job."""

    product: Product = "western_natal_pdf"
    chart_input: ChartInput
    partner_chart_input: Optional[ChartInput] = None
    options: Optional[Dict[str, Any]] = None
    branding: Optional[Branding] = Branding()
    idempotency_key: Optional[str] = None


class ReportStatus(BaseModel):
    """Current status of a report job."""

    report_id: str
    status: Literal["queued", "processing", "done", "error"]
    download_url: Optional[str] = None
    error: Optional[str] = None

