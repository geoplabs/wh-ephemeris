from typing import Optional

from pydantic import BaseModel

from .charts import ChartInput


class ReportCreateRequest(ChartInput):
    """Payload for requesting a new report."""


class ReportStatus(BaseModel):
    id: str
    status: str
    download_url: Optional[str] = None

