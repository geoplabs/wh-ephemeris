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


def test_yearly_forecast_api():
    r = client.post(
        "/v1/forecasts/yearly",
        json={
            "chart_input": _ci(),
            "options": {"year": 1991, "user_id": "user-1234"},
        },
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert "months" in j and "top_events" in j
    assert any(len(v) > 0 for v in j["months"].values())
    assert j.get("pdf_download_url")
    assert "/user-1234" in j["pdf_download_url"]
    pdf_resp = client.get(j["pdf_download_url"])
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF")
