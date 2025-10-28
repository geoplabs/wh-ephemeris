from api.services.option_b_cleaner.event_tokens import event_phrase


def test_event_phrase_includes_orb_and_phase():
    event = {
        "transit_body": "Sun",
        "natal_body": "Pluto",
        "aspect": "conjunction",
        "orb": 0.39,
        "applying": True,
        "transit_sign": "Scorpio",
        "natal_sign": "Scorpio",
    }

    phrase = event_phrase(event)

    assert (
        phrase
        == "Sun aligns with your Pluto in Scorpio—an applying exact conjunction at 0.39° orb"
    )


def test_event_phrase_notes_cross_sign_alignment():
    event = {
        "transit_body": "Mercury",
        "natal_body": "Saturn",
        "aspect": "conjunction",
        "orb": 1.73,
        "applying": True,
        "transit_sign": "Scorpio",
        "natal_sign": "Sagittarius",
    }

    phrase = event_phrase(event)

    assert (
        phrase
        == "Mercury aligns with your Saturn from Scorpio to Sagittarius—an applying exact conjunction at 1.73° orb"
    )
