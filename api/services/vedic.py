NAKSHATRAS = [
  "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha",
  "Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha",
  "Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha","Shatabhisha",
  "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

def nakshatra_from_lon_sidereal(lon_sid: float) -> dict:
    # Each nakshatra = 13°20′ = 13.3333333333°
    idx = int(lon_sid // 13.3333333333333) % 27
    pada = int(((lon_sid % 13.3333333333333) // 3.3333333333333)) + 1
    return {"name": NAKSHATRAS[idx], "pada": pada}
