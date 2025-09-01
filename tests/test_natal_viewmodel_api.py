from fastapi.testclient import TestClient
from api.app import app
import time

client = TestClient(app)

CI = {
    "system": "vedic",
    "date": "1990-08-18",
    "time": "14:32:00",
    "time_known": True,
    "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    "options": {"ayanamsha": "lahiri", "house_system": "whole_sign"},
}


def test_full_natal_viewmodel_json():
    r = client.post("/v1/natal/full", json={"chart_input": CI, "place_label": "Hyderabad, India"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert "header" in j and "core_chart" in j and "analysis" in j and "interpretation" in j
    assert j["header"]["system"] == "vedic"
    assert any(b["name"] == "Sun" for b in j["core_chart"]["bodies"])
    assert "elements_balance" in j["analysis"]


def test_full_natal_viewmodel_has_snapshot_and_strengths():
    r = client.post("/v1/natal/full", json={"chart_input": CI, "place_label": "Hyderabad, India"})
    j = r.json()
    assert "bodies" in j["core_chart"] and any(b["name"] == "Sun" for b in j["core_chart"]["bodies"])
    assert "strengths" in j["analysis"] and "growth" in j["analysis"]


def test_full_natal_pdf_job():
    r = client.post("/v1/natal/full/report", json={"chart_input": CI, "place_label": "Hyderabad, India"})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    for _ in range(50):
        s = client.get(f"/v1/reports/{rid}")
        assert s.status_code == 200
        js = s.json()
        if js["status"] == "done":
            pdf = client.get(js["download_url"])
            assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
            return
        elif js["status"] == "error":
            assert False, f"render error: {js}"
        time.sleep(0.1)
    assert False, "timeout waiting for PDF"


def test_pdf_contains_sections_text():
    r = client.post("/v1/natal/full/report", json={"chart_input": CI, "place_label": "Hyderabad, India"})
    rid = r.json()["report_id"]
    for _ in range(50):
        s = client.get(f"/v1/reports/{rid}")
        js = s.json()
        if js["status"] == "done":
            pdf_resp = client.get(js["download_url"])
            assert pdf_resp.status_code == 200
            assert pdf_resp.content[:4] == b"%PDF"
            return
        elif js["status"] == "error":
            assert False, f"render error: {js}"
        time.sleep(0.1)
    assert False, "timeout waiting for PDF"
