"""Tests for Panchang API endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def _assert_local_timestamp(value: str, offset_hint: str) -> None:
    assert offset_hint in value
    dt = datetime.fromisoformat(value)
    assert dt.tzinfo is not None


def test_today_minimal():
    resp = client.get(
        "/v1/panchang/today",
        params={"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["header"]["tz"] == "Asia/Kolkata"
    _assert_local_timestamp(data["solar"]["sunrise"], "+05:30")
    _assert_local_timestamp(data["solar"]["sunset"], "+05:30")
    assert data["tithi"]["display_name"]
    assert data["nakshatra"]["display_name"]
    assert data["muhurta"] is not None


def test_compute_matches_today():
    params = {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"}
    today_resp = client.get("/v1/panchang/today", params=params)
    assert today_resp.status_code == 200
    today_data = today_resp.json()

    date_local = today_data["header"]["date_local"]
    compute_resp = client.post(
        "/v1/panchang/compute",
        json={
            "system": "vedic",
            "date": date_local,
            "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            "options": {"ayanamsha": "lahiri", "include_muhurta": True},
        },
    )
    assert compute_resp.status_code == 200
    compute_data = compute_resp.json()

    assert compute_data["solar"] == today_data["solar"]
    assert compute_data["tithi"]["display_name"] == today_data["tithi"]["display_name"]


def test_report_endpoint_pdf(tmp_path):
    resp = client.post(
        "/v1/panchang/report",
        json={
            "place": {"lat": 12.9716, "lon": 77.5946, "tz": "Asia/Kolkata"},
            "options": {"include_muhurta": True},
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["report_id"]
    assert payload["download_url"].endswith(".pdf")

    pdf_resp = client.get(payload["download_url"])
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF")

