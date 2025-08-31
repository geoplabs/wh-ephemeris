from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_compute_chart_stub():
    payload = {
        "system":"western",
        "date":"1990-08-18",
        "time":"14:32:00",
        "time_known": True,
        "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata", "query": "Hyderabad, IN"}
    }
    res = client.post("/v1/charts/compute", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["chart_id"].startswith("cht_")
    assert data["meta"]["zodiac"] == "tropical"
    names = [b["name"] for b in data["bodies"]]
    assert "Sun" in names and "Chiron" in names
