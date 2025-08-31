SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]


def sign_name_from_lon(lon: float) -> str:
    return SIGNS[int(lon // 30) % 12]
