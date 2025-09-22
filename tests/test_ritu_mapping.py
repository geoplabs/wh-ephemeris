from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_ritu_is_sharad_on_2025_09_19_ist():
    response = client.post(
        "/v1/panchang/compute",
        json={
            "system": "vedic",
            "date": "2025-09-19",
            "place": {
                "lat": 28.6139,
                "lon": 77.2090,
                "tz": "Asia/Kolkata",
                "query": "New Delhi",
            },
            "options": {"ayanamsha": "lahiri"},
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ritu_extended"]["drik_ritu"] == "Sharad"
    assert payload["ritu_extended"]["vedic_ritu"] == "Sharad"
