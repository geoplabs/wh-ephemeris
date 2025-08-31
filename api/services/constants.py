SIGN_NAMES = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

def sign_index_from_lon(lon: float) -> int:
    return int(lon // 30) % 12

def sign_name_from_lon(lon: float) -> str:
    return SIGN_NAMES[sign_index_from_lon(lon)]

def fmt_deg(lon: float) -> str:
    # 0..360 to "sign 12°34′"
    sidx = sign_index_from_lon(lon)
    within = lon % 30.0
    deg = int(within)
    minutes_float = (within - deg) * 60
    mins = int(minutes_float)
    secs = int((minutes_float - mins) * 60)
    return f"{SIGN_NAMES[sidx]} {deg:02d}°{mins:02d}′{secs:02d}″"
