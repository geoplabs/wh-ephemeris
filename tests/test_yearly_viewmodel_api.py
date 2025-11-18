from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

CI = {
    "system": "vedic",
    "date": "1990-08-18",
    "time": "14:32:00",
    "time_known": True,
    "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    "options": {"ayanamsha": "lahiri", "house_system": "whole_sign"},
}


def test_yearly_full_json():
    r = client.post(
        "/v1/yearly/full",
        json={
            "chart_input": CI,
            "options": {
                "year": 2025,
                "step_days": 1,
                "transit_bodies": [
                    "Sun",
                    "Mercury",
                    "Venus",
                    "Mars",
                    "Jupiter",
                    "Saturn",
                ],
                "aspects": {
                    "types": [
                        "conjunction",
                        "opposition",
                        "square",
                        "trine",
                        "sextile",
                    ],
                    "orb_deg": 3.0,
                },
            },
            "place_label": "Hyderabad, India",
            "include_interpretation": True,
            "include_dasha": True,
        },
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["header"]["year"] == 2025
    assert "months" in j and len(j["months"]) >= 1
    assert "overview" in j and "key_themes" in j["overview"]
    assert "key_dates" in j and isinstance(j["key_dates"], list)
    assert j["meta"]["interpretation"]["raw_events_forwarded"] is True


def test_yearly_full_pdf_job():
    r = client.post(
        "/v1/yearly/full/report",
        json={
            "chart_input": CI,
            "options": {
                "year": 2025,
                "step_days": 1,
                "transit_bodies": [
                    "Sun",
                    "Mercury",
                    "Venus",
                    "Mars",
                    "Jupiter",
                    "Saturn",
                ],
                "aspects": {
                    "types": [
                        "conjunction",
                        "opposition",
                        "square",
                        "trine",
                        "sextile",
                    ],
                    "orb_deg": 3.0,
                },
            },
            "place_label": "Hyderabad, India",
            "include_interpretation": True,
            "include_dasha": True,
            "branding": {"primary_hex": "#7C3AED"},
        },
    )
    assert r.status_code == 200
    rid = r.json()["report_id"]

    import time

    for _ in range(50):
        s = client.get(f"/v1/reports/{rid}")
        js = s.json()
        if js["status"] == "done":
            pdf = client.get(js["download_url"])
            assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
            return
        elif js["status"] == "error":
            assert False, f"render error: {js}"
        time.sleep(0.1)
    assert False, "timeout waiting for yearly PDF"
