from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal

from .charts import ChartInput



class Branding(BaseModel):
    """Optional branding information for a report."""

    logo_url: Optional[str] = None
    primary_hex: Optional[str] = "#4A3AFF"


class ReportCreateRequest(BaseModel):
    """Request payload for enqueuing a report render job."""

    product: str = "western_natal_pdf"
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

