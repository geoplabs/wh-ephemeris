"""Tests for Panchang API endpoints."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_today_basic_shape() -> None:
    resp = client.get(
        "/v1/panchang/today",
        params={
            "lat": 19.076,
            "lon": 72.8777,
            "tz": "Asia/Kolkata",
            "ayanamsha": "lahiri",
            "include_muhurta": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["header"]["tz"] == "Asia/Kolkata"
    assert "sunrise" in data["solar"]
    assert "display_name" in data["tithi"]
    assert "aliases" in data["tithi"]
    assert "windows" in data and "auspicious" in data["windows"]


def test_compute_explicit_date_equals_today_for_same_date() -> None:
    today_ist = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    params = {
        "lat": 28.6139,
        "lon": 77.2090,
        "tz": "Asia/Kolkata",
    }
    today_resp = client.get("/v1/panchang/today", params=params)
    assert today_resp.status_code == 200
    today_data = today_resp.json()

    compute_resp = client.post(
        "/v1/panchang/compute",
        json={
            "system": "vedic",
            "date": today_ist,
            "place": {
                "lat": 28.6139,
                "lon": 77.2090,
                "tz": "Asia/Kolkata",
                "query": "New Delhi",
            },
            "options": {
                "ayanamsha": "lahiri",
                "include_muhurta": True,
                "include_hora": False,
            },
        },
    )
    assert compute_resp.status_code == 200
    compute_data = compute_resp.json()
    assert compute_data["header"]["date_local"] == today_data["header"]["date_local"]
    assert compute_data["header"]["tz"] == today_data["header"]["tz"]
    assert "display_name" in compute_data["nakshatra"]


def test_i18n_hindi_deva_labels() -> None:
    resp = client.get(
        "/v1/panchang/today",
        params={
            "lat": 17.385,
            "lon": 78.4867,
            "tz": "Asia/Kolkata",
            "lang": "hi",
            "script": "deva",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["header"]["locale"]["lang"] == "hi"
    assert "deva" in data["tithi"]["aliases"]


def test_pdf_smoke_if_enabled() -> None:
    resp = client.post(
        "/v1/panchang/report",
        json={
            "system": "vedic",
            "place": {
                "lat": 19.076,
                "lon": 72.8777,
                "tz": "Asia/Kolkata",
                "query": "Mumbai",
            },
            "options": {
                "ayanamsha": "lahiri",
                "include_muhurta": True,
                "lang": "en",
                "script": "latin",
            },
            "branding": {
                "primary_hex": "#7C3AED",
                "logo_url": "https://example.com/logo.png",
            },
        },
    )
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        payload = resp.json()
        rid = payload["report_id"]
        assert rid
        for _ in range(5):
            status_resp = client.get(f"/v1/reports/{rid}")
            if status_resp.status_code != 200:
                continue
            status_json = status_resp.json()
            if status_json.get("status") != "done":
                continue
            pdf_resp = client.get(status_json["download_url"])
            assert pdf_resp.status_code == 200
            assert pdf_resp.content.startswith(b"%PDF")
            break
