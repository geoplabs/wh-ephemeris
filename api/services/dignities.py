RULERS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}
EXALT = {
    "Sun": "Aries",
    "Moon": "Taurus",
    "Mercury": "Virgo",
    "Venus": "Pisces",
    "Mars": "Capricorn",
    "Jupiter": "Cancer",
    "Saturn": "Libra",
}
DETRIMENT = {v: k for k, v in RULERS.items()}
FALL = {v: k for k, v in EXALT.items()}


def dignity_for(planet: str, sign: str) -> str:
    if sign == EXALT.get(planet):
        return "exaltation"
    if FALL.get(planet) == sign:
        return "fall"
    if RULERS.get(sign) == planet:
        return "domicile"
    return "neutral"
