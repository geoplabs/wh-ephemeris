from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from .charts import ComputeRequest


class ReportProduct(str, Enum):
    western_natal_pdf = "western_natal_pdf"


class ReportStatusEnum(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    error = "error"


class Branding(BaseModel):
    logo_url: Optional[str] = None
    primary_hex: Optional[str] = None


class ReportCreateRequest(BaseModel):
    product: ReportProduct
    chart_input: ComputeRequest
    branding: Optional[Branding] = None
    idempotency_key: Optional[str] = None


class ReportCreateResponse(BaseModel):
    report_id: str
    status: ReportStatusEnum
    queued_at: datetime


class ReportStatus(BaseModel):
    report_id: str
    status: ReportStatusEnum
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None
