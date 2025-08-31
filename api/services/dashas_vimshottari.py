from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
from . import ephem
from .vedic import nakshatra_from_lon_sidereal

# Vimshottari order and full years per Maha
DASHA_ORDER = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
YEARS =      [   7,     20,    6,    10,     7,     18,       16,      19,       17]

SIDEREAL_YEAR_DAYS = 365.25636  # close enough for CI; adjust later if desired

def _lord_for_nakshatra_idx(idx: int) -> str:
    return DASHA_ORDER[idx % 9]

def _years_for_lord(lord: str) -> float:
    return YEARS[DASHA_ORDER.index(lord)]

def _to_jd_and_moon_sidereal(chart_input: Dict[str,Any], ayanamsha: str) -> Tuple[float, float]:
    jd = ephem.to_jd_utc(chart_input["date"], chart_input["time"], chart_input["place"]["tz"])
    pos = ephem.positions_ecliptic(jd, sidereal=True, ayanamsha=ayanamsha)
    return jd, pos["Moon"]["lon"]

def _to_dt(date_str: str, time_str: str, tz: str) -> datetime:
    # compute UTC datetime for birth moment
    from zoneinfo import ZoneInfo
    dt_local = datetime.fromisoformat(f"{date_str}T{time_str}").replace(tzinfo=ZoneInfo(tz))
    return dt_local.astimezone(timezone.utc)

def compute_vimshottari(chart_input: Dict[str,Any], levels: int = 2, ayanamsha: str = "lahiri") -> List[Dict[str,Any]]:
    """
    Returns list of dasha periods with ISO start/end dates.
    Algorithm:
      - Determine Moon's sidereal lon at birth -> nakshatra index 0..26
      - Birth Mahadasha lord = order[idx % 9]
      - Balance remaining of current Maha = (1 - fraction traversed in current nakshatra) * Maha years
      - Build timeline forward for e.g., 120 years or until 9 cycles
      - For Antar: within each Maha, sub-order = same DASHA_ORDER sequence
    """
    # Birth UTC
    dt0_utc = _to_dt(chart_input["date"], chart_input["time"], chart_input["place"]["tz"])
    _, moon_lon_sid = _to_jd_and_moon_sidereal(chart_input, ayanamsha)
    # nakshatra index & fraction within
    NAK_SIZE = 13.3333333333333
    idx = int(moon_lon_sid // NAK_SIZE) % 27
    frac = (moon_lon_sid % NAK_SIZE) / NAK_SIZE  # traversed
    maha_lord = _lord_for_nakshatra_idx(idx)

    # years & balance
    maha_years = _years_for_lord(maha_lord)
    remaining_years = (1.0 - frac) * maha_years

    periods = []
    # Build Mahadashas for ~120 years
    # First Maha is the birth one: remaining fragment, then full ones in sequence
    start = dt0_utc
    def add_period(level: int, lord: str, start_dt: datetime, years: float, parent: str|None=None):
        end_dt = start_dt + timedelta(days=years*SIDEREAL_YEAR_DAYS)
        periods.append({
            "level": level, "lord": lord,
            "start": start_dt.date().isoformat(),
            "end": (end_dt.date()).isoformat(),
            "parent": parent
        })
        return end_dt

    # 1) current (partial) Maha
    end = add_period(1, maha_lord, start, remaining_years)
    # 2) subsequent full Mahas (8 remaining then cycles)
    lord_idx = DASHA_ORDER.index(maha_lord)
    # Build enough (e.g., 9 full cycles ~120 years)
    for _ in range(9*2):  # ~2 cycles is plenty
        lord_idx = (lord_idx + 1) % 9
        l = DASHA_ORDER[lord_idx]
        years = _years_for_lord(l)
        end = add_period(1, l, end, years)

    if levels >= 2:
        # Expand each Maha into Antar sequence
        exp = []
        for p in periods:
            if p["level"] != 1: 
                continue
            m_start = datetime.fromisoformat(p["start"] + "T00:00:00+00:00")
            m_end   = datetime.fromisoformat(p["end"]   + "T00:00:00+00:00")
            m_days  = (m_end - m_start).days + 0.0
            # Antar durations scale by YEARS / sum(YEARS)=120 years
            total_yrs = 120.0
            cur = m_start
            for sub_lord, sub_years in zip(DASHA_ORDER, YEARS):
                dur_days = m_days * (sub_years / total_yrs)
                sub_end = cur + timedelta(days=dur_days)
                exp.append({
                    "level": 2, "lord": sub_lord, "parent": p["lord"],
                    "start": cur.date().isoformat(), "end": sub_end.date().isoformat()
                })
                cur = sub_end
        periods.extend(exp)

    return periods
