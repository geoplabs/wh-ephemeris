from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_today_hindi_deva():
    response = client.get(
        "/v1/panchang/today",
        params={
            "lat": 17.385,
            "lon": 78.4867,
            "tz": "Asia/Kolkata",
            "lang": "hi",
            "script": "deva",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["header"]["locale"]["lang"] == "hi"
    assert payload["tithi"]["display_name"]
    assert "aliases" in payload["tithi"]
    assert "en" in payload["tithi"]["aliases"]
    assert "deva" in payload["tithi"]["aliases"]


def test_today_english_iast():
    response = client.get(
        "/v1/panchang/today",
        params={
            "lat": 17.385,
            "lon": 78.4867,
            "tz": "Asia/Kolkata",
            "lang": "en",
            "script": "iast",
        },
    )
    payload = response.json()
    iast_alias = payload["nakshatra"]["aliases"]["iast"]
    assert "ā" in iast_alias or "ī" in iast_alias
