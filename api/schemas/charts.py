from pydantic import BaseModel
from typing import Optional, List, Literal

System = Literal["western", "vedic"]

class Place(BaseModel):
    lat: float
    lon: float
    tz: str
    query: Optional[str] = None

class ChartInput(BaseModel):
    system: System
    date: str  # YYYY-MM-DD
    time: str  # HH:MM:SS
    time_known: bool = True
    place: Place
    options: Optional[dict] = None

class ComputeRequest(ChartInput):
    pass

class BodyOut(BaseModel):
    name: str
    lon: float
    sign: str
    house: Optional[int] = None

class MetaOut(BaseModel):
    engine: str = "mock"
    engine_version: str = "0.0.1-stub"
    zodiac: str
    house_system: str
    ayanamsha: Optional[str] = None

class ComputeResponse(BaseModel):
    chart_id: str
    meta: MetaOut
    angles: Optional[dict] = None
    houses: Optional[list] = None
    bodies: List[BodyOut]
    aspects: list
