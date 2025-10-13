from pathlib import Path

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


def test_yearly_forecast_pdf_uploads_to_s3(monkeypatch, tmp_path):
    from api.services import forecast_reports as fr

    monkeypatch.setenv("REPORTS_USE_S3", "true")
    monkeypatch.setenv("S3_BUCKET", "wh-test-bucket")
    monkeypatch.setenv("REPORTS_BASE_URL", "https://api.whathoroscope.com")
    monkeypatch.setenv("REPORTS_STORAGE_DIR", str(tmp_path))

    # Clear cached client between env toggles
    if hasattr(fr._get_s3_client, "cache_clear"):
        fr._get_s3_client.cache_clear()

    uploads = {}

    def fake_upload(path: Path, key: str) -> bool:
        uploads["path"] = path
        uploads["key"] = key
        return True

    def fake_render(context, out_path: str, template_name: str = "") -> str:
        Path(out_path).write_bytes(b"%PDF-1.4\n%fake")
        return out_path

    monkeypatch.setattr(fr, "_upload_to_s3", fake_upload)
    monkeypatch.setattr(fr, "render_western_natal_pdf", fake_render)
    monkeypatch.setattr(
        fr,
        "build_yearly_pdf_payload",
        lambda chart_input, options, payload: {"prepared_for": "Tester", "generated_at": "1 Jan", "sections": []},
    )

    chart_input = {"options": {"user_id": "user-789"}, "place": {"tz": "UTC"}}
    options = {"year": 2026, "user_id": "user-789"}
    payload = {"months": {}, "top_events": []}

    rid, url = fr.generate_yearly_pdf(chart_input, options, payload)

    assert uploads["key"].startswith("reports/")
    assert rid in uploads["key"]
    assert url == f"https://api.whathoroscope.com/{uploads['key']}"
    assert uploads["path"].exists()

    if hasattr(fr._get_s3_client, "cache_clear"):
        fr._get_s3_client.cache_clear()
