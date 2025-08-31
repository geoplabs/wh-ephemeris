from pydantic import BaseModel
from typing import Optional, List, Literal, Dict, Any

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
    retro: Optional[bool] = None
    speed: Optional[float] = None
    # optional vedic
    nakshatra: Optional[Dict[str,Any]] = None

class MetaOut(BaseModel):
    engine: str = "wh-ephemeris"
    engine_version: str
    zodiac: str
    house_system: str
    ayanamsha: Optional[str] = None
    backend: Optional[str] = None
    warnings: Optional[List[str]] = None

class ComputeResponse(BaseModel):
    chart_id: str
    meta: MetaOut
    angles: Optional[dict] = None
    houses: Optional[list] = None
    bodies: List[BodyOut]
    aspects: list
