def houses(jd: float, lat: float, lon: float, system: str):
    base = jd % 360.0
    asc = (base + lat) % 360.0
    mc = (base + lon) % 360.0
    return {"asc": asc, "mc": mc}
