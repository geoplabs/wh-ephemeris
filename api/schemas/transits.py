from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from .charts import ChartInput

class AspectPolicy(BaseModel):
    types: List[str] = ["conjunction","opposition","square","trine","sextile"]
    orb_deg: float = 3.0  # default max orb for transit hits

class TransitsOptions(BaseModel):
    from_date: str  # "YYYY-MM-DD"
    to_date: str
    step_days: int = 1
    transit_bodies: List[str] = ["Sun","Mercury","Venus","Mars","Jupiter","Saturn"]  # include Moon if you want many events
    natal_targets: Optional[List[str]] = None  # None = all planets (+ ASC/MC if time known)
    aspects: AspectPolicy = AspectPolicy()

class TransitEvent(BaseModel):
    date: str
    transit_body: str
    natal_body: str
    aspect: str
    orb: float
    applying: Optional[bool] = None
    score: float
    note: Optional[str] = None
    transit_sign: Optional[str] = None
    natal_sign: Optional[str] = None
    zodiac: Optional[str] = None

class TransitsComputeRequest(BaseModel):
    chart_input: ChartInput
    options: TransitsOptions

class TransitsComputeResponse(BaseModel):
    meta: Dict[str, Any]
    events: List[TransitEvent]
