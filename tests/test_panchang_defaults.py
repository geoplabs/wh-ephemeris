from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_missing_place_uses_defaults():
    response = client.post(
        "/v1/panchang/compute",
        json={"system": "vedic", "options": {"ayanamsha": "lahiri"}},
    )
    assert response.status_code == 200
    payload = response.json()
    meta = payload["header"]["meta"]
    assert meta["place_defaults_used"] is True
    assert meta["default_reason"] in {"missing_place", "missing_latlon"}
    assert payload["header"]["tz"]


def test_missing_tz_is_inferred():
    response = client.get("/v1/panchang/today?lat=28.6139&lon=77.2090")
    assert response.status_code == 200
    payload = response.json()
    meta = payload["header"]["meta"]
    assert meta["tz_inferred"] in (True, False)
    assert payload["header"]["tz"]


def test_only_tz_uses_default_coords():
    response = client.get("/v1/panchang/today?tz=Asia/Kolkata")
    assert response.status_code == 200
    payload = response.json()
    meta = payload["header"]["meta"]
    assert meta["place_defaults_used"] is True
    assert payload["header"]["place_label"]
