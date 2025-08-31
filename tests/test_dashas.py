from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def _chart_input():
    return {"system":"vedic","date":"1990-08-18","time":"14:32:00","time_known":True,
            "place":{"lat":17.385,"lon":78.4867,"tz":"Asia/Kolkata"},
            "options":{"ayanamsha":"lahiri"}}

def test_vimshottari_maha_and_antar():
    r = client.post("/v1/dashas/compute", json={"chart_input":_chart_input(),"options":{"levels":2}})
    assert r.status_code == 200, r.text
    j = r.json()
    maha = [p for p in j["periods"] if p["level"]==1]
    antar= [p for p in j["periods"] if p["level"]==2]
    assert len(maha) >= 9
    assert len(antar) >= 9  # many more actually
    # dates increase
    starts = [p["start"] for p in maha[:5]]
    assert starts == sorted(starts)
    # lords are present strings
    assert isinstance(maha[0]["lord"], str) and len(maha[0]["lord"])>0
