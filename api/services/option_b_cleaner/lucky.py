from .mappings import COLOR_BY_SIGN, DIR_BY_PLANET, DEFAULT_TIME_WINDOW


def lucky_from_dominant(dominant_planet: str, dominant_sign: str, time_window: str | None = None):
    color = COLOR_BY_SIGN.get(dominant_sign, "Gold")
    direction = DIR_BY_PLANET.get(dominant_planet, "East")
    window = time_window or DEFAULT_TIME_WINDOW
    affirmation = {
        "Sun": "I act with clarity and purpose.",
        "Venus": "I attract harmony and support.",
        "Mars": "I move with courage and focus.",
        "Jupiter": "I welcome growth and opportunity.",
        "Saturn": "I honor structure and steady progress.",
        "Moon": "I listen to my feelings with care.",
        "Pluto": "My inner power is steady and calm.",
    }.get(dominant_planet, "I choose what strengthens me.")
    return {
        "color": color,
        "time_window": window,
        "direction": direction,
        "affirmation": affirmation,
    }
