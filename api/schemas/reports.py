from pydantic import BaseModel
from typing import Optional

class ReportCreateResponse(BaseModel):
    id: str
    status: str

class ReportStatusResponse(BaseModel):
    id: str
    status: str
    download_url: Optional[str] = None
