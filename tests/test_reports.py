import time
import os
os.environ.setdefault("EPHEMERIS_BACKEND", "moseph")
from fastapi.testclient import TestClient

from api.app import app


def _make_chart_input():
    return {
        "system": "western",
        "date": "1990-08-18",
        "time": "14:32:00",
        "time_known": True,
        "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    }


def test_enqueue_and_get_pdf():
    with TestClient(app) as client:
        app.state.rate = {}
        r = client.post(
            "/v1/reports",
            json={"product": "western_natal_pdf", "chart_input": _make_chart_input()},
        )
        assert r.status_code == 202
        rid = r.json()["report_id"]

        # Poll for completion
        url = None
        for _ in range(40):  # up to ~4 seconds
            g = client.get(f"/v1/reports/{rid}")
            assert g.status_code == 200
            j = g.json()
            if j["status"] == "done":
                url = j["download_url"]
                break
            elif j["status"] == "error":
                assert False, f"render failed: {j}"
            time.sleep(0.1)
        assert url and url.endswith(f"{rid}.pdf")

        # Fetch bytes and check PDF header
        pdf = client.get(url)
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"


def test_rate_limit():
    with TestClient(app) as client:
        app.state.rate = {}
        # hit it 12 times quickly; expect at least one 429
        codes = []
        for _ in range(12):
            r = client.post(
                "/v1/reports", json={"product": "western_natal_pdf", "chart_input": _make_chart_input()}
            )
            codes.append(r.status_code)
        assert 429 in codes


def test_idempotency_key():
    with TestClient(app) as client:
        app.state.rate = {}
        payload = {
            "product": "western_natal_pdf",
            "chart_input": _make_chart_input(),
            "idempotency_key": "abc123",
        }
        a = client.post("/v1/reports", json=payload).json()["report_id"]
        b = client.post("/v1/reports", json=payload).json()["report_id"]
        assert a == b

