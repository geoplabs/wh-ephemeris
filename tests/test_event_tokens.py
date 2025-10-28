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


def test_event_phrase_uses_phase_from_note_when_flag_missing():
    event = {
        "transit_body": "Sun",
        "natal_body": "Pluto",
        "aspect": "conjunction",
        "orb": 0.39,
        "note": "Applying aspect, exact at 0.39°.",
        "transit_sign": "Scorpio",
        "natal_sign": "Scorpio",
    }

    phrase = event_phrase(event)

    assert (
        phrase
        == "Sun aligns with your Pluto in Scorpio—an applying exact conjunction at 0.39° orb"
    )


def test_event_phrase_uses_value_after_label_in_note():
    event = {
        "transit_body": "Venus",
        "natal_body": "Mars",
        "aspect": "square",
        "orb": 2.5,
        "note": "Applying / Separating: Separating at 2.5°.",
        "transit_sign": "Leo",
        "natal_sign": "Scorpio",
    }

    phrase = event_phrase(event)

    assert (
        phrase
        == "Venus presses on your Mars from Leo to Scorpio—an separating pressing square at 2.50° orb"
    )


def test_event_phrase_prefers_first_non_label_phase_reference():
    event = {
        "transit_body": "Mars",
        "natal_body": "Moon",
        "aspect": "trine",
        "orb": 1.1,
        "note": "Separating, previously applying earlier in the week.",
        "transit_sign": "Sagittarius",
        "natal_sign": "Aries",
    }

    phrase = event_phrase(event)

    assert (
        phrase
        == "Mars flows with your Moon from Sagittarius to Aries—an separating flowing trine at 1.10° orb"
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
