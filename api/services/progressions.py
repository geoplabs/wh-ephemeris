from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from . import ephem


def _to_dt(chart_input: Dict[str, Any]) -> datetime:
    from zoneinfo import ZoneInfo

    dt_local = datetime.fromisoformat(f"{chart_input['date']}T{chart_input['time']}").replace(
        tzinfo=ZoneInfo(chart_input["place"]["tz"])
    )
    return dt_local.astimezone(timezone.utc)


def progressed_positions(chart_input: Dict[str, Any], target_year: int) -> Dict[str, Dict[str, float]]:
    """Compute secondary progressed positions for ``target_year``."""

    dt0 = _to_dt(chart_input)
    years = target_year - dt0.year
    dt_prog = dt0 + timedelta(days=years)
    jd = ephem.to_jd_utc(dt_prog.date().isoformat(), "12:00:00", "UTC")
    sidereal = chart_input["system"] == "vedic"
    ayan = (
        (chart_input.get("options") or {}).get("ayanamsha", "lahiri") if sidereal else None
    )
    pos = ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayan)
    return {k: {"lon": v["lon"], "speed_lon": v["speed_lon"]} for k, v in pos.items()}
