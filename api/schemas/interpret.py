from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from .charts import ChartInput


class NatalOptions(BaseModel):
    tone: Optional[str] = "professional"
    length: Optional[str] = "medium"
    language: Optional[str] = "en"
    domains: List[str] = ["love", "career", "health", "spiritual"]


class NatalInterpretRequest(BaseModel):
    chart_input: ChartInput
    options: NatalOptions = NatalOptions()


class NatalInterpretResponse(BaseModel):
    meta: Dict[str, Any]
    sections: Dict[str, str]
    highlights: List[str]


class TransitWindow(BaseModel):
    from_: str = Field(..., alias="from")
    to: str

    model_config = {"populate_by_name": True}


class TransitOptions(BaseModel):
    tone: Optional[str] = "professional"
    length: Optional[str] = "short"


class TransitsInterpretRequest(BaseModel):
    chart_input: ChartInput
    window: TransitWindow
    options: TransitOptions = TransitOptions()
    events_by_month: Dict[str, List[Dict[str, Any]]] | None = None


class TransitsInterpretResponse(BaseModel):
    meta: Dict[str, Any]
    month_summaries: Dict[str, str]
    key_dates: List[Dict[str, str]]


class CompatibilityOptions(BaseModel):
    tone: Optional[str] = "professional"
    length: Optional[str] = "short"
    focus: List[str] = ["romance", "communication"]


class CompatibilityInterpretRequest(BaseModel):
    person_a: ChartInput
    person_b: ChartInput
    options: CompatibilityOptions = CompatibilityOptions()


class CompatibilityInterpretResponse(BaseModel):
    summary: str
    strengths: List[str]
    challenges: List[str]
    score: int
