from fastapi import FastAPI
from fastapi.testclient import TestClient

import sys
import types

if "swisseph" not in sys.modules:
    swe_stub = types.ModuleType("swisseph")

    class _SwissEphError(Exception):
        pass

    swe_stub.Error = _SwissEphError
    swe_stub.FLG_MOSEPH = 0
    swe_stub.FLG_SWIEPH = 0
    swe_stub.FLG_SIDEREAL = 0
    swe_stub.FLG_SPEED = 0
    swe_stub.BIT_DISC_CENTER = 0
    swe_stub.CALC_RISE = 1
    swe_stub.CALC_SET = 2
    swe_stub.SUN = 0
    swe_stub.MOON = 1
    swe_stub.MERCURY = 2
    swe_stub.VENUS = 3
    swe_stub.MARS = 4
    swe_stub.JUPITER = 5
    swe_stub.SATURN = 6
    swe_stub.URANUS = 7
    swe_stub.NEPTUNE = 8
    swe_stub.PLUTO = 9
    swe_stub.TRUE_NODE = 10
    swe_stub.CHIRON = 11
    swe_stub.SIDM_LAHIRI = 0
    swe_stub.SIDM_KRISHNAMURTI = 1
    swe_stub.SIDM_RAMAN = 2
    swe_stub.GREG_CAL = 0

    def _stub_rise_trans(*args, **kwargs):
        raise _SwissEphError()

    def _stub_calc_ut(*args, **kwargs):
        return [0.0] * 6, 0

    def _stub_set_ephe_path(*args, **kwargs):
        return None

    def _stub_julday(*args, **kwargs):
        return 2451545.0

    def _stub_set_sid_mode(*args, **kwargs):
        return None

    def _stub_houses(*args, **kwargs):
        return [0.0] * 13, [0.0] * 10

    swe_stub.rise_trans = _stub_rise_trans
    swe_stub.calc_ut = _stub_calc_ut
    swe_stub.set_ephe_path = _stub_set_ephe_path
    swe_stub.julday = _stub_julday
    swe_stub.set_sid_mode = _stub_set_sid_mode
    swe_stub.houses = _stub_houses

    sys.modules["swisseph"] = swe_stub


from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import panchang as panchang_router


test_app = FastAPI()
test_app.include_router(panchang_router.router)

client = TestClient(test_app)


def _is_ordered(periods):
    return all(periods[i]["end_ts"] <= periods[i + 1]["start_ts"] for i in range(len(periods) - 1))


def test_changes_lists_present_and_ordered():
    response = client.get(
        "/v1/panchang/today",
        params={
            "lat": 28.6139,
            "lon": 77.2090,
            "tz": "Asia/Kolkata",
            "ayanamsha": "lahiri",
        },
    )
    data = response.json()
    changes = data["changes"]

    assert isinstance(changes["tithi_periods"], list)
    assert len(changes["tithi_periods"]) >= 1
    assert _is_ordered(changes["tithi_periods"])
    assert _is_ordered(changes["nakshatra_periods"])
    assert _is_ordered(changes["yoga_periods"])
    assert _is_ordered(changes["karana_periods"])


def test_current_matches_changes_covering_now():
    import datetime as dt
    from zoneinfo import ZoneInfo

    ist = ZoneInfo("Asia/Kolkata")
    now = dt.datetime.now(ist).isoformat()

    response = client.get(
        "/v1/panchang/today",
        params={
            "lat": 19.076,
            "lon": 72.8777,
            "tz": "Asia/Kolkata",
        },
    )
    data = response.json()
    periods = data["changes"]["tithi_periods"]

    def covers(target: str, period: dict) -> bool:
        return period["start_ts"] <= target <= period["end_ts"]

    assert any(covers(now, period) for period in periods)


def test_weekly_summary_exposes_changes_block():
    response = client.get(
        "/v1/panchang/week",
        params={
            "lat": 28.6139,
            "lon": 77.2090,
            "tz": "Asia/Kolkata",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["days"], "weekly payload should include days"
    first_day = payload["days"][0]
    assert "changes" in first_day
    assert first_day["changes"]["tithi_periods"]


def test_monthly_summary_exposes_changes_block():
    response = client.get(
        "/v1/panchang/month",
        params={
            "year": 2024,
            "month": 1,
            "lat": 12.9716,
            "lon": 77.5946,
            "tz": "Asia/Kolkata",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["days"], "monthly payload should include days"
    first_day = payload["days"][0]
    assert "changes" in first_day
    assert first_day["changes"]["tithi_periods"]
