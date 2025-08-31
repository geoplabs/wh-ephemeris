from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def ci_a():
    return {
        "system": "western",
        "date": "1990-08-18",
        "time": "14:32:00",
        "time_known": True,
        "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    }


def ci_b():
    return {
        "system": "western",
        "date": "1991-03-07",
        "time": "09:15:00",
        "time_known": True,
        "place": {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
    }


def test_compat_interpret():
    payload = {"person_a": ci_a(), "person_b": ci_b(), "options": {"tone": "casual"}}
    r = client.post("/v1/interpret/compatibility", json=payload)
    assert r.status_code == 200
    j = r.json()
    assert "score" in j and 0 <= j["score"] <= 100
