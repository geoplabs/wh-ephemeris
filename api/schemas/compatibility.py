from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from .charts import ChartInput


class CompatibilityOptions(BaseModel):
    aspects: Dict[str, Any] = {
        "types": ["conjunction", "opposition", "square", "trine", "sextile"],
        "orb_deg": 4.0,
    }
    include_composite: bool = True


class SynAspect(BaseModel):
    p1: str
    p2: str
    type: str
    orb: float
    weight: float


class CompositePoint(BaseModel):
    name: str
    lon: float
    sign: str
    house: Optional[int]


class CompatibilityComputeRequest(BaseModel):
    person_a: ChartInput
    person_b: ChartInput
    options: CompatibilityOptions = CompatibilityOptions()


class CompatibilityComputeResponse(BaseModel):
    meta: Dict[str, Any]
    synastry: List[SynAspect]
    score: float
    strengths: List[str]
    challenges: List[str]
    composite: Optional[List[CompositePoint]] = None
