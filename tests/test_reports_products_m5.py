import time
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


def wait_pdf(rid):
    for _ in range(50):
        j = client.get(f"/v1/reports/{rid}").json()
        if j["status"] == "done":
            pdf = client.get(j["download_url"])
            assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
            return
        elif j["status"] == "error":
            assert False, f"job error: {j}"
        time.sleep(0.1)
    assert False, "timeout"


def test_advanced_natal_pdf_job():
    r = client.post("/v1/reports", json={"product": "advanced_natal_pdf", "chart_input": ci()})
    assert r.status_code == 202
    wait_pdf(r.json()["report_id"])


def test_transit_forecast_pdf_job():
    r = client.post(
        "/v1/reports",
        json={
            "product": "transit_forecast_pdf",
            "chart_input": ci(),
            "window": {"from": "2025-01-01", "to": "2025-02-28"},
        },
    )
    assert r.status_code == 202
    wait_pdf(r.json()["report_id"])
