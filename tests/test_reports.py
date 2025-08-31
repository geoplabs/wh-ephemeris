import time
import os
os.environ.setdefault("EPHEMERIS_BACKEND", "moseph")
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

sample_payload = {
    "system": "western",
    "date": "1990-08-18",
    "time": "14:32:00",
    "time_known": True,
    "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata", "query": "Hyderabad, IN"},
}

def test_report_lifecycle():
    res = client.post("/v1/reports", json=sample_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    rid = data["id"]
    assert data["status"] == "queued"

    # Poll until done
    for _ in range(30):
        res = client.get(f"/v1/reports/{rid}")
        assert res.status_code == 200
        info = res.json()
        if info["status"] == "done":
            break
        time.sleep(0.2)
    else:
        raise AssertionError("report not done")

    assert "download_url" in info
    url = info["download_url"]
    res = client.get(url)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
