from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def ci():
    return {
        "system": "vedic",
        "date": "1990-08-18",
        "time": "14:32:00",
        "time_known": True,
        "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    }


def test_remedies_api():
    r = client.post(
        "/v1/remedies/compute",
        json={"chart_input": ci(), "options": {"allow_gemstones": True}},
    )
    assert r.status_code == 200
    j = r.json()
    assert "remedies" in j and isinstance(j["remedies"], list)
