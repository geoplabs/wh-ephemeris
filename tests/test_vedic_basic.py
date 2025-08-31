import os
os.environ.setdefault("EPHEMERIS_BACKEND", "moseph")
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_vedic_moon_has_nakshatra_and_kp_works():
    base = {"system":"vedic","date":"1990-08-18","time":"14:32:00","time_known":True,
            "place":{"lat":17.385,"lon":78.4867,"tz":"Asia/Kolkata"}}

    # Lahiri
    r1 = client.post("/v1/charts/compute", json={**base, "options":{"ayanamsha":"lahiri"}})
    j1 = r1.json()
    moon = [b for b in j1["bodies"] if b["name"]=="Moon"][0]
    assert moon.get("nakshatra") and "name" in moon["nakshatra"]

    # KP (krishnamurti)
    r2 = client.post("/v1/charts/compute", json={**base, "options":{"ayanamsha":"krishnamurti"}})
    j2 = r2.json()
    assert j2["meta"]["ayanamsha"] == "krishnamurti"
