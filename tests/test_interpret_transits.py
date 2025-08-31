from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def ci():
    return {
        "system": "western",
        "date": "1990-08-18",
        "time": "14:32:00",
        "time_known": True,
        "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    }


def test_transits_interpret():
    payload = {
        "chart_input": ci(),
        "window": {"from": "2025-01-01", "to": "2025-02-28"},
        "options": {"tone": "professional"},
    }
    r = client.post("/v1/interpret/transits", json=payload)
    assert r.status_code == 200
    j = r.json()
    assert "2025-01" in j["month_summaries"]
    assert isinstance(j["key_dates"], list)
