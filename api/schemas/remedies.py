from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from .charts import ChartInput


class RemediesOptions(BaseModel):
    allow_gemstones: bool = True


class RemedyItem(BaseModel):
    planet: str
    issue: str
    recommendation: str
    gemstone: Optional[str] = None
    cautions: List[str] = []


class RemediesComputeRequest(BaseModel):
    chart_input: ChartInput
    options: RemediesOptions = RemediesOptions()


class RemediesComputeResponse(BaseModel):
    meta: Dict[str, Any]
    remedies: List[RemedyItem]
