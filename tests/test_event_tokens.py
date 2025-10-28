from api.services.option_b_cleaner.event_tokens import event_phrase


def test_event_phrase_includes_orb_and_phase():
    event = {
        "transit_body": "Sun",
        "natal_body": "Pluto",
        "aspect": "conjunction",
        "orb": 0.39,
        "applying": True,
    }

    phrase = event_phrase(event)

    assert (
        phrase
        == "Sun aligns with your Pluto—an applying harmonizing conjunction at 0.39° orb"
    )
