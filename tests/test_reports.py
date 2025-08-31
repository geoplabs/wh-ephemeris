import time
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)

base_payload = {
    "product": "western_natal_pdf",
    "chart_input": {
        "system": "western",
        "date": "1990-08-18",
        "time": "14:32:00",
        "time_known": True,
        "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    },
    "branding": {"logo_url": None, "primary_hex": "#4A3AFF"},
}


def _enqueue(payload, token: str = "t"):
    res = client.post("/v1/reports", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 202, res.text
    return res.json()


def _poll(rid):
    for _ in range(100):
        res = client.get(f"/v1/reports/{rid}")
        assert res.status_code == 200, res.text
        data = res.json()
        if data["status"] == "done":
            return data
        time.sleep(0.1)
    raise AssertionError("report not done")


def test_enqueue_and_status_and_pdf_header():
    data = _enqueue(base_payload, token="a")
    rid = data["report_id"]
    info = _poll(rid)
    url = info["download_url"]
    res = client.get(url)
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")


def test_rate_limit():
    for _ in range(10):
        _enqueue(base_payload, token="rate")
    res = client.post("/v1/reports", json=base_payload, headers={"Authorization": "Bearer rate"})
    assert res.status_code == 429


def test_idempotency():
    payload = dict(base_payload)
    payload["idempotency_key"] = "same"
    first = _enqueue(payload, token="idemp")
    second = _enqueue(payload, token="idemp2")  # different token but same key+payload
    assert first["report_id"] == second["report_id"]


def test_unknown_time_note():
    payload = {
        "product": "western_natal_pdf",
        "chart_input": {
            "system": "western",
            "date": "1990-08-18",
            "time": "14:32:00",
            "time_known": False,
            "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
        },
    }
    data = _enqueue(payload, token="unknown")
    info = _poll(data["report_id"])
    res = client.get(info["download_url"])
    assert b"Birth time unknown" in res.content
