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


def test_natal_interpret_sections():
    r = client.post(
        "/v1/interpret/natal", json={"chart_input": ci(), "options": {"tone": "mystical"}}
    )
    assert r.status_code == 200
    j = r.json()
    assert "love" in j["sections"]
    assert isinstance(j["sections"]["career"], str)
