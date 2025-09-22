"""Static ritual notes for extended Panchang payload."""


def notes_for_day() -> list[dict]:
    return [
        {
            "key": "madhyahna_sandhya",
            "text": "Madhyahna Sandhya roughly spans solar noon; used for specific rituals.",
        },
        {
            "key": "sayana_sandhya",
            "text": "Sayana Sandhya occurs near sunset; timings vary by latitude and season.",
        },
        {
            "key": "usage",
            "text": "Panchang day spans from local sunrise to next sunrise; times are local to your city.",
        },
    ]
