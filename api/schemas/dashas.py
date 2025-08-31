from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from .charts import ChartInput

Level = Literal[1, 2]  # 1 = Mahadasha only, 2 = Maha + Antar

class DashaOptions(BaseModel):
    levels: Level = 2
    ayanamsha: str = "lahiri"  # KP etc. via chart_input.options if you prefer

class DashaComputeRequest(BaseModel):
    chart_input: ChartInput
    options: DashaOptions = DashaOptions()

class DashaPeriod(BaseModel):
    level: int
    lord: str
    start: str  # ISO date
    end: str    # ISO date
    parent: Optional[str] = None  # maha lord for antars

class DashaComputeResponse(BaseModel):
    meta: Dict[str, Any]
    periods: List[DashaPeriod]
