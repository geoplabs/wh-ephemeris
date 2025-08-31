import os
os.environ.setdefault("EPHEMERIS_BACKEND", "moseph")
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_western_has_angles_and_aspects():
    payload = {"system":"western","date":"1990-08-18","time":"14:32:00","time_known":True,
               "place":{"lat":17.385,"lon":78.4867,"tz":"Asia/Kolkata"}}
    r = client.post("/v1/charts/compute", json=payload)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["meta"]["zodiac"] == "tropical"
    assert j["angles"] is not None and "ascendant" in j["angles"]
    # at least 3 major aspects should be detected
    assert len(j["aspects"]) >= 3
    # chiron included
    names = [b["name"] for b in j["bodies"]]
    assert "Chiron" in names
