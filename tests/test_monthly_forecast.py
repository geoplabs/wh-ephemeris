from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def _ci():
    return {
        "system": "western",
        "date": "1990-08-18",
        "time": "14:32:00",
        "time_known": True,
        "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    }


def test_monthly_forecast_api():
    r = client.post(
        "/v1/forecasts/monthly",
        json={"chart_input": _ci(), "options": {"year": 1990, "month": 9}},
    )
    assert r.status_code == 200
    j = r.json()
    assert "events" in j and len(j["events"]) >= 3
